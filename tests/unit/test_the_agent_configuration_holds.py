"""The configuration that steers the agent, tested like the code it steers.

The AI-native SDLC playbook's Test stage says the eval suite runs "on
any change to `CLAUDE.md`, skills or hooks, since that configuration
steers the agent and deserves the regression testing that code gets."
This repository had four skills and no test that any of them worked.

Two halves, and only one of them is here:

- **Deterministic.** A hook either blocks a payload or it does not, a
  command either exists or it does not, a path either resolves or it
  does not. That is this file, and it needs no model.
- **Model-in-the-loop.** Twenty to fifty real tasks replayed through
  `claude -p`, checked for tests passing and policy followed. That
  needs an API key and a budget, and is not built. Said plainly here
  rather than implied by the file's name.

The hook clauses are the ones that matter, because a hook that cannot
block is `UX-109`'s defect in a newer place: a gate written as though
it holds.

holds: rules.md#never-let-an-instrument-read-a-proxy-for-the-thing-it-names
"""
import contextlib
import io
import json
import os
import pathlib
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
HOOKS = REPO / ".claude/hooks"
SETTINGS = REPO / ".claude/settings.json"
CLAUDE_MD = REPO / "CLAUDE.md"
REVIEW_MD = REPO / "REVIEW.md"
AGENTS = REPO / ".claude/agents"
SKILLS = REPO / ".claude/skills"
WORKFLOW = REPO / ".github/workflows/ci.yml"

#: Built rather than written, because `keep-the-guards-able-to-fail.sh`
#: blocks an edit that carries the literal - including this one. The
#: hook cannot tell a decorator from a string that looks like one, and
#: that bluntness is recorded in its own header.
SKIP = "@pytest.mark." + "skip"
XFAIL = "@pytest.mark." + "xfail"
SKIPIF = "@pytest.mark." + "skipif"


_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def fire(name, payload):
    """`(exit code, stderr)` for one hook against one PreToolUse payload."""
    done = subprocess.run([str(HOOKS / name)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=30)
    return done.returncode, done.stderr


def _selector_hook():
    """`UX-522`'s hook, loaded fresh so a clause can replace its edges."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "selector_before_commit", HOOKS / "selector_before_commit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@contextlib.contextmanager
def _payload(body):
    """`sys.stdin` carrying one PreToolUse payload."""
    held = sys.stdin
    sys.stdin = io.StringIO(json.dumps(body))
    try:
        yield
    finally:
        sys.stdin = held


@contextlib.contextmanager
def _env(**names):
    held = {k: os.environ.get(k) for k in names}
    os.environ.update(names)
    try:
        yield
    finally:
        for k, v in held.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


class TestTheSelectorRunsBeforeTheCommit:
    """`UX-522`: the selector, at the moment it cannot be skipped.

    Round 75 measured the habit rather than arguing about it - the
    close, the Outcome and the row move all landed *after*
    `test-touching`'s last run, so it never saw the tree the commit was
    about. These clauses hold the matching and the escape hatch; that
    the decision itself is right is `dev_touching`'s business.
    """

    #: What the hook must recognise as a commit. The heredoc case is
    #: the one `UX-424` cost a round over: this repository's commit
    #: messages quote commands, so a text scan fires on the message.
    @pytest.mark.parametrize("command", (
        "git commit -m x",
        "git commit -q -F -",
        "make lint && git commit -m x",
        'git commit -F - <<EOF\nfix: git commit -m nope\nEOF',
    ))
    def test_it_sees_a_commit(self, command):
        assert _selector_hook().is_git_commit(command), command

    @pytest.mark.parametrize("command", (
        "git status --short",
        "git add tools/dev_touching.py",
        "echo 'git commit -m x'",
        "git log --oneline -1",
        "python3 -c \"print('git commit')\"",
    ))
    def test_it_leaves_everything_else_alone(self, command):
        assert not _selector_hook().is_git_commit(command), command

    def test_settings_declares_it_on_bash(self):
        """A hook nothing declares is a file, not a control."""
        held = json.loads(SETTINGS.read_text(encoding="utf-8"))
        bash = [m for m in held["hooks"]["PreToolUse"]
                if m.get("matcher") == "Bash"]
        commands = [h["command"] for m in bash for h in m["hooks"]]
        assert any("selector-before-commit.sh" in c for c in commands), commands

    def test_the_escape_hatch_is_named_in_the_message(self):
        """The case the hook cannot be right about: a commit whose
        *content* is the fix to a red guard. A block with no way past
        it is a block somebody disables permanently."""
        source = (HOOKS / "selector_before_commit.py").read_text(
            encoding="utf-8")
        assert "BGA_SKIP_SELECTOR" in source
        assert "{skip}" in source.split("MESSAGE = ")[1].split('"""')[1]

    def test_the_escape_hatch_works(self):
        """Driven through `main`, with the selector replaced by one that
        always says red. Firing the real hook proves nothing: on a clean
        index there is nothing staged to select, so it returns 0 whether
        the hatch works or not - which is how the mutation that deleted
        the hatch stayed green."""
        module, ran = self._hook_that_always_reds()
        with _payload({"tool_input": {"command": "git commit -m x"}}):
            with _env(BGA_SKIP_SELECTOR="1"):
                assert module.main() == 0
        assert ran == [], "the selector ran despite the escape hatch"

    def test_it_does_not_run_the_selector_for_anything_else(self):
        """The other half of the matching, at `main` rather than at
        `is_git_commit`: a hook that consults the matcher and then
        ignores it costs every Bash command a test run."""
        module, ran = self._hook_that_always_reds()
        with _payload({"tool_input": {"command": "git status --short"}}):
            assert module.main() == 0
        assert ran == [], "the selector ran on a command that is not a commit"

    def test_it_blocks_a_commit_when_the_selector_is_red(self):
        """And that the gate is a gate. `2` is the PreToolUse refusal."""
        module, ran = self._hook_that_always_reds()
        with _payload({"tool_input": {"command": "git commit -m x"}}):
            assert module.main() == 2
        assert ran == [["tests/unit/test_the_register_is_terse.py"]]

    def test_it_judges_the_worktree_it_is_run_in(self, tmp_path):
        """`parents[2]` of this hook is the **shared** checkout, and a
        worktree borrows `.claude/` from it - so a hook reading its own
        path judges a tree the committer is not in. Round 80's track D
        measured that (8 changed files reported into a worktree with 2)
        and reached for the escape hatch, which is the wrong end."""
        module = _selector_hook()
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        held = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert module.repo_root().resolve() == tmp_path.resolve()
        finally:
            os.chdir(held)

    def test_it_falls_back_to_its_own_tree_outside_a_checkout(self, tmp_path):
        """The other input class. `git rev-parse` fails outside a
        repository, and a hook that then raises blocks every commit."""
        module = _selector_hook()
        held = os.getcwd()
        os.chdir(tmp_path)
        try:
            assert module.repo_root() == REPO
        finally:
            os.chdir(held)

    @staticmethod
    def _hook_that_always_reds():
        """The hook module with its two edges replaced: a fixed
        selection, and a run that is always red. What is left under
        test is the decision, which is the part with the mutations."""
        module = _selector_hook()
        ran = []
        module.selection = lambda: (
            ["tests/unit/test_the_register_is_terse.py"], {})
        module.selector_is_green = lambda files: (ran.append(files),
                                                  (False, "planted"))[1]
        return module, ran


class TestTheHooksBlockWhatTheyClaim:
    """A skill is advisory; a hook is the deterministic layer behind it.

    Each clause is a payload the hook sees in production, so a change
    to the matching that stops catching a case reddens here rather than
    in somebody's tree three weeks later.
    """

    @pytest.mark.parametrize("command", (
        "git add -A",
        "git add .",
        "git add --all",
        "make test && git add -A",
        "cd /tmp; git add -A",
        # UX-424. The first three are what a quote-stripping fix would
        # have lost: strip the quotes and `git add "-A"` reads as a
        # bare `git add`, which passes. Tokenising keeps them, because
        # `shlex` removes the quoting and leaves the word.
        'git add "-A"',
        "git add '-A'",
        "git add -vA",
        # `shlex` treats a newline as whitespace, so without the
        # substitution in `_as_one_line` this puts `git` in argument
        # position and passes.
        "make test\ngit add -A",
        # No parse, so the old regex decides - and it must still block.
        "echo 'unterminated && git add -A",
    ))
    def test_a_bulk_add_is_blocked(self, command):
        code, said = fire("no-bulk-add.sh", {"tool_input": {"command": command}})
        assert code == 2, (command, code, said)
        assert "4a.1" in said, said

    @pytest.mark.parametrize("command", (
        # Every one of these blocked before UX-424, and each cost a
        # retry in round 67. A commit message quoting the rule is the
        # commonest: this repository's messages describe the rules they
        # enforce, so the control was firing on its own documentation.
        'git commit -m "never use git add -A here"',
        "cat > /tmp/m.txt <<'EOF'\nThe rule is old; git add -A is banned.\nEOF",
        "cat > /tmp/m.txt <<'EOF'\n| `git add -A` | forbidden |\nEOF",
        "probe 'make test && git add -A'",
        'grep -rn "git add -A" docs/',
        'echo "git add -A" | wc -l',
    ))
    def test_writing_about_the_rule_is_not_blocked(self, command):
        """`UX-424`: the fourth sighting of an instrument reading a
        proxy rather than the thing, and the one that obstructed its
        own fix - the hook blocked two of the probes written to measure
        it, and three commits in the round that introduced it.

        A control whose failure mode is "you may not write about the
        rule I enforce" gets switched off, which is how a control stops
        existing (`UX-403` makes the same argument for the same shape).
        """
        code, said = fire("no-bulk-add.sh", {"tool_input": {"command": command}})
        assert code == 0, (command, code, said)

    @pytest.mark.parametrize("command", (
        "git add bga/analysis.py",
        "git add ./bga/analysis.py",
        "git add tests/unit/a.py tests/unit/b.py",
        "make test",
        "git status --short",
    ))
    def test_a_named_path_is_not(self, command):
        """The half that makes it usable. `git add ./x.py` is a path,
        not a bulk add, and a hook that stopped it would be turned off
        within the day - which is how a control stops existing."""
        code, said = fire("no-bulk-add.sh", {"tool_input": {"command": command}})
        assert code == 0, (command, code, said)

    @pytest.mark.parametrize("marker", (SKIP, XFAIL))
    def test_an_unconditional_skip_in_tests_is_blocked(self, marker):
        code, said = fire("keep-the-guards-able-to-fail.sh", {"tool_input": {
            "file_path": "tests/unit/test_x.py",
            "new_string": marker + "\ndef test_x():\n    pass\n"}})
        assert code == 2, (marker, code, said)
        assert "cannot fail" in said, said

    @pytest.mark.parametrize("allowed", (
        SKIPIF + "(find_chrome() is None, reason=NO_BROWSER)",
        'pytest.skip("this host exposes no /proc/meminfo")',
        "def test_x():\n    pass\n",
    ))
    def test_a_condition_that_names_itself_is_not(self, allowed):
        """`skipif` and a runtime `pytest.skip` name why they skipped.
        Both are how this suite gates on a missing browser or a missing
        bst, and blocking them would break the suite it protects."""
        code, said = fire("keep-the-guards-able-to-fail.sh", {"tool_input": {
            "file_path": "tests/unit/test_x.py", "new_string": allowed}})
        assert code == 0, (allowed, code, said)

    def test_outside_tests_it_says_nothing(self):
        code, _said = fire("keep-the-guards-able-to-fail.sh", {"tool_input": {
            "file_path": "bga/analysis.py", "new_string": SKIP}})
        assert code == 0, code

    def test_it_reads_a_whole_file_write_too(self):
        """`Write` carries `content`, `Edit` carries `new_string`. Reading
        one and not the other leaves the whole-file path unguarded, which
        is the shape of `UX-363`'s regex stopping at the first match."""
        code, _said = fire("keep-the-guards-able-to-fail.sh", {"tool_input": {
            "file_path": "tests/unit/test_x.py", "content": SKIP}})
        assert code == 2, code

    def test_ruff_reports_on_the_file_just_edited(self, tmp_path):
        bad = tmp_path / "bad.py"
        bad.write_text("import os\n", encoding="utf-8")
        code, said = fire("lint-edited-python.sh",
                          {"tool_input": {"file_path": str(bad)}})
        assert code == 2, (code, said)
        assert "F401" in said or "unused" in said.lower(), said

    @pytest.mark.parametrize("name,body", (("clean.py", "x = 1\n"),
                                           ("notes.md", "# not python\n")))
    def test_it_is_quiet_otherwise(self, tmp_path, name, body):
        path = tmp_path / name
        path.write_text(body, encoding="utf-8")
        code, said = fire("lint-edited-python.sh",
                          {"tool_input": {"file_path": str(path)}})
        assert code == 0, (name, code, said)


class TestEveryDeclaredHookExists:
    """`settings.json` names scripts by path. A name that resolves to
    nothing is a control the repository believes it has."""

    @staticmethod
    def _declared():
        held = json.loads(SETTINGS.read_text(encoding="utf-8"))
        for event in held.get("hooks", {}).values():
            for matcher in event:
                for hook in matcher.get("hooks", []):
                    yield hook["command"]

    def test_settings_declares_hooks_at_all(self):
        assert list(self._declared()), "settings.json declares no hooks"

    def test_each_command_resolves_and_is_executable(self):
        for command in self._declared():
            path = REPO / command.replace("${CLAUDE_PROJECT_DIR}/", "")
            assert path.is_file(), f"{command} names no file"
            assert path.stat().st_mode & 0o111, f"{path.name} is not executable"

    def test_every_script_on_disk_is_declared(self):
        """The other direction: a hook nobody wired up runs never, and
        reads in review as a control that is in force."""
        declared = {pathlib.Path(c).name for c in self._declared()}
        found = {p.name for p in HOOKS.glob("*.sh")}
        assert found == declared, (
            f"scripts on disk {sorted(found)}, declared {sorted(declared)}")


class TestClaudeMdIsTrueAndShort:
    """It is read at the start of every session, so a stale line is paid
    for on every one of them."""

    @staticmethod
    def _text():
        return CLAUDE_MD.read_text(encoding="utf-8")

    def test_it_stays_about_a_page(self):
        lines = self._text().splitlines()
        assert len(lines) <= 80, (
            f"CLAUDE.md is {len(lines)} lines; it is loaded in full at the "
            f"start of every session, so length is a per-session cost")

    def test_every_make_target_it_names_exists(self):
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        real = set(re.findall(r"^([a-z][\w-]*):", makefile, re.M))
        named = set(re.findall(r"`make ([a-z][\w-]*)", self._text()))
        assert named, "CLAUDE.md names no make target"
        assert named <= real, f"CLAUDE.md names absent target(s): {named - real}"

    def test_every_path_it_names_exists(self):
        named = set(re.findall(
            r"(?<![\w./-])((?:bga|tools|tests|docs)/[\w./-]+)", self._text()))
        missing = sorted(p for p in named
                         if not (REPO / p.rstrip("/")).exists())
        assert missing == [], f"CLAUDE.md names path(s) that do not exist: {missing}"

    def test_no_line_carries_a_count_that_a_close_makes_wrong(self):
        """`UX-471`. The tree map said **421 task files** against 482 on
        disk - 61 out, and drifting further on every close.

        Every other figure in this file is a command's runtime or a
        rule, and neither moves when a row closes. This one moved on
        every commit, and the review that found it could not name a
        decision it informs. So the number is gone rather than guarded:
        a count nobody acts on, kept true by a test somebody has to
        edit each round, is upkeep bought for nothing.

        This clause is the other shape - it asserts the **absence** and
        so never needs editing. It reads the counted nouns rather than
        every digit, because `CLAUDE.md` legitimately carries `~4m45s`,
        `-n auto` and section numbers, and a clause that banned digits
        outright would be banning the sentences this file is for.

        It found a second one on its first run, which the review that
        filed `UX-471` had passed over: *"~30 sightings in ~26 items"*
        about the proxy defect. A running tally of how often something
        has been sighted decays exactly like a file count, and round 73
        alone added four. Gone the same way.

        What it deliberately does **not** catch is a figure frozen to a
        closed item - *"Five found in `UX-420` alone"* is a fact about
        `UX-420` and cannot go stale, which is why that sentence spells
        its number and this one reads digits.
        """
        countable = r"(?:task file|scenario|item|row|test file|guard|skill)s?"
        found = re.findall(rf"\b(\d[\d,]*)\s+{countable}\b", self._text())
        assert found == [], (
            f"CLAUDE.md counts {found} of something the backlog changes on "
            f"every close - the count decays on its own, and `UX-471` "
            f"removed the last one rather than guard it")

    def test_it_points_at_the_card_rather_than_restating_it(self):
        """`UX-240`'s rule for skills, and it holds here for the same
        reason: two copies of one rule is how the copies disagree.

        `UX-505` made the card the entry point, so this asserts the
        card. The guide is still named — for the argument behind a rule
        — but a session that reads only what `CLAUDE.md` sends it to
        must land on the rules, not on the incidents that produced
        them.
        """
        text = self._text()
        assert "docs/contributing/rules.md" in text, (
            "CLAUDE.md does not send a session to the rules card")
        assert "docs/contributing/fixing-guide.md" in text
        assert len(text.splitlines()) < len(
            (REPO / "docs/contributing/fixing-guide.md").read_text(
                encoding="utf-8").splitlines())


class TestTheReviewPolicyIsReadable:
    """`REVIEW.md` is what a reviewer - human or agent - is held to. A
    policy that names a pass it does not define, or an item that does
    not exist, is the "claim a document's own body does not do" finding
    turned on the file that lists it."""

    @staticmethod
    def _text():
        return REVIEW_MD.read_text(encoding="utf-8")

    @pytest.mark.parametrize("pass_name", ("Bugs", "Security", "Compliance",
                                           "Evidence"))
    def test_each_named_pass_has_a_section(self, pass_name):
        assert f"**{pass_name}.**" in self._text(), (
            f"REVIEW.md's passes list names {pass_name} without defining it")

    def test_it_says_how_many_passes_there_are_and_has_that_many(self):
        text = self._text()
        stated = re.search(r"Run (\w+) passes", text)
        assert stated, "REVIEW.md does not say how many passes to run"
        words = {"three": 3, "four": 4, "five": 5}
        defined = len(re.findall(r"^\*\*[A-Z][a-z]+\.\*\*", text, re.M))
        assert words[stated.group(1)] == defined, (
            f"REVIEW.md says {stated.group(1)} passes and defines {defined}")

    def test_it_draws_the_important_line_and_caps_the_nits(self):
        text = self._text()
        assert "Important" in text and "nit" in text.lower()
        assert re.search(r"[Aa]t most \w+ nits", text), (
            "REVIEW.md does not cap nit volume, so a review nobody "
            "finishes reading is a review that did not happen")

    def test_every_item_it_cites_exists(self):
        cited = set(re.findall(r"`(UX-\d+)`", self._text()))
        assert cited, "REVIEW.md cites no item, so its rules have no provenance"
        scenarios = REPO / "docs/backlog/scenarios"
        missing = sorted(
            uid for uid in cited
            if not list(scenarios.glob(f"UX-0*{uid.split('-')[1]}-*.md")))
        assert missing == [], f"REVIEW.md cites absent item(s): {missing}"

    def test_it_keeps_the_agent_off_its_own_approval(self):
        """Separation of duties is the reason this file is committed
        rather than prompted."""
        assert "has no route to approve" in self._text()


class TestTheSubagentsAreWellFormed:
    """A subagent is a scoped helper with its own context window. Its
    frontmatter is what decides whether it is offered at all, so a
    missing field is a helper nobody is ever handed."""

    @staticmethod
    def _files():
        return sorted(AGENTS.glob("*.md"))

    def test_there_are_some(self):
        assert self._files(), ".claude/agents/ is empty"

    @pytest.mark.parametrize("field", ("name", "description", "tools"))
    def test_each_declares_the_field(self, field):
        for path in self._files():
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
            assert head, f"{path.name} has no frontmatter"
            assert re.search(rf"^{field}:", head.group(1), re.M), (
                f"{path.name} declares no {field}")

    def test_the_name_matches_the_filename(self):
        """Two names for one helper is the drift this repository has
        fixed more often than any other."""
        for path in self._files():
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8")).group(1)
            declared = re.search(r"^name:\s*(\S+)", head, re.M).group(1)
            assert declared == path.stem, (path.name, declared)

    #: `UX-504`: the one agent that may edit, and the four files no
    #: track writes. Named here rather than "everything except the
    #: implementer", so adding a third editing agent is a decision
    #: somebody makes in this list.
    MAY_EDIT = {"implementer"}

    #: The agents whose whole job is to read and report, named. Without
    #: this the clause below reads "whoever is not on the editing list",
    #: and widening that list would exempt them silently - which is what
    #: `UX-504`'s fifth mutation did while every clause stayed green.
    REPORTERS = {"researcher", "verifier"}
    SHARED = ("docs/backlog/scenarios/README.md",
              "docs/backlog/scenarios/closed.md",
              "tests/tiers.py",
              "tests/ci_reference.json")

    def test_a_reporting_agent_cannot_edit_the_tree(self):
        """A verifier that could fix what it found would be judging its
        own work, which is the one thing it exists not to do; a
        researcher that could edit is no longer reading."""
        for path in self._files():
            if path.stem in self.MAY_EDIT:
                continue
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8")).group(1)
            tools = re.search(r"^tools:\s*(.+)$", head, re.M).group(1)
            for forbidden in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                assert forbidden not in tools, (
                    f"{path.name} may use {forbidden}; a reporting agent "
                    f"reports only")

    def test_a_reporter_is_never_put_on_the_editing_list(self):
        """`UX-504`. The split is a *role*, not an exemption: a verifier
        that could fix what it found would judge its own work, and
        that must not become true by editing one set in this file. Each
        reporter's body says so too, so the classification cannot be
        dodged by rewording either end alone."""
        assert self.MAY_EDIT.isdisjoint(self.REPORTERS), (
            f"{sorted(self.MAY_EDIT & self.REPORTERS)} may edit, and they "
            f"are the agents that exist to report")
        said = ("report only", "fix nothing", "do not edit")
        for name in sorted(self.REPORTERS):
            body = (AGENTS / f"{name}.md").read_text(encoding="utf-8").lower()
            assert any(one in body for one in said), (
                f"{name}.md no longer says it does not edit, so nothing but "
                f"this file's own list keeps it from doing so. The three "
                f"phrasings above are the ones the bodies carry; a fourth "
                f"is a decision, not a pattern to lengthen")

    def test_the_implementer_may_edit(self):
        """`UX-504`. Without this the split reads as an exemption rather
        than a role: an implementer whose tools were trimmed back to
        read-only would satisfy every other clause here and silently
        stop being able to run a track."""
        head = _FRONTMATTER.match(
            (AGENTS / "implementer.md").read_text(encoding="utf-8")).group(1)
        tools = re.search(r"^tools:\s*(.+)$", head, re.M).group(1)
        for needed in ("Edit", "Write"):
            assert needed in tools, (
                f"implementer.md cannot {needed}, so it cannot run a track")

    def test_the_implementer_takes_its_base_rather_than_stopping(self):
        """`UX-560`: the worktree is created from `origin/main`, not the
        session's HEAD, so a track's base is wrong whenever the branch
        is ahead - which is every round. `UX-510` made the brief name
        the base; the brief is not what decides it.

        Round 81's two tracks both opened 34 commits behind and both
        recovered by resetting, so the instruction is to take the base,
        not to stop at it. Taking it needs no fetch because a linked
        worktree shares the main checkout's object database, and the
        file must say so - a track that does not know that will fetch,
        or worse, decide the commit is unreachable and improvise.

        `UX-614` moved the *command* out of this clause: asserting the
        literal `git reset --hard` passed unchanged when the fenced
        instruction became `git merge --ff-only`, so the string was no
        longer reading what it named. What is left here is the pair the
        wording cannot drop - take it, and why that always works -
        and `TestATrackTakesTheBaseItWasNamed` runs the command itself.
        """
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        assert "then take the base" in body, (
            "implementer.md does not tell a track to take its named "
            "base, so a wrong base is reported and then worked around")
        assert "object database" in body or "object store" in body, (
            "implementer.md does not say why the reset always works, so "
            "a track may treat its base as unreachable (UX-560)")

    def test_the_implementer_says_where_it_runs(self):
        """Its editing is bounded by *where* it runs, not by what it
        promises. A body that does not say so is one an orchestrator
        might launch in the tree itself."""
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        assert "worktree" in body, (
            "implementer.md does not say it runs in a worktree, which is "
            "the whole bound on its editing (UX-504)")

    def test_the_implementer_names_the_files_no_track_touches(self):
        """`UX-501` measured the collision: two branches each closing one
        item conflicted on the topic table and silently auto-merged the
        counts sentence to a number neither meant. The four are named in
        the body because an agent reads its body, not this file."""
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        missing = [name for name in self.SHARED if name not in body]
        assert missing == [], (
            f"implementer.md does not tell the track to leave {missing} "
            f"alone - the files every track collides on (UX-501, UX-503)")

    def test_the_implementer_is_told_to_check_the_base_it_got(self):
        """`UX-510`: all three of round 75's worktrees started nine
        commits behind the orchestrator, and two tracks were told to
        read files that did not exist in their copy. The brief cannot
        choose the base, so the track checks it - with the one command
        that answers, named in the body because an agent reads its body.
        """
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        assert "git log --oneline -1" in body, (
            "implementer.md does not tell the track how to read the "
            "commit its copy starts from (UX-510)")
        assert "the commit your brief names" in body, (
            "implementer.md says how to read the base but not what to "
            "compare it against, so a track behind the orchestrator has "
            "nothing to notice")

    def test_the_implementer_is_told_to_report_rather_than_work_around(self):
        """The half that decides what a track does with the answer. A
        track that recreates a file the brief cited costs a round; one
        that says "my base is X, the brief says Y" costs a message.

        `UX-560` changed the *remedy* - the track now resets to its base
        rather than stopping at it - so this pins the property that
        survived rather than the sentence that did not: the mismatch is
        reported, and a missing file is never recreated.
        """
        body = " ".join(
            (AGENTS / "implementer.md").read_text(encoding="utf-8").split())
        assert "say so in your first sentence" in body, (
            "implementer.md tells the track to check its base and not to "
            "report what it finds (UX-510)")
        assert "Never recreate a file the brief cites" in body, (
            "implementer.md does not forbid recreating a file its copy "
            "lacks, which is the working-around UX-510 priced")

    def test_the_merge_cost_is_a_measured_number_in_both_places(self):
        """`UX-510`'s third bullet. "Parallel is cheaper" is the claim a
        round makes when it splits, and the only measurement on file is
        round 75's - three picks, one conflicted, over nine commits. It
        lives in the brief the track reads and in the skill the
        orchestrator reads, because they are different readers."""
        for path in (AGENTS / "implementer.md",
                     REPO / ".claude/skills/decompose/SKILL.md"):
            body = " ".join(path.read_text(encoding="utf-8").split())
            assert "three cherry-picks" in body, (
                f"{path.name} does not say what merging a track cost the "
                f"one round that measured it (UX-510)")
            # Beside the count, not merely in the same file: three picks
            # is a number only against the distance it was over, and
            # both files say "nine commits" a paragraph earlier for a
            # different reason - a clause reading the whole body, or a
            # wide window, passes on that and checks nothing. Measured
            # offsets on the two bodies: -801/+144 and -299/-16/+139.
            at = body.index("three cherry-picks")
            assert "nine commits" in body[max(0, at - 40):at + 200], (
                f"{path.name} gives the pick count without the distance "
                f"it was over, which is the half that makes it a number")

    def test_the_verifier_says_it_does_not_fix(self):
        body = (AGENTS / "verifier.md").read_text(encoding="utf-8")
        assert "Fix nothing" in body or "fix nothing" in body
        assert "falsify" in body.lower() or "mutation" in body.lower(), (
            "a verifier for this repository that never asks whether a new "
            "guard can fail is checking the wrong thing")

    def test_the_researcher_is_told_to_name_what_it_could_not_find(self):
        """Silence reading as "there is none" is how a false premise
        reaches a task file."""
        body = (AGENTS / "researcher.md").read_text(encoding="utf-8")
        assert "could not establish" in body or "did not find" in body


class TestATrackTakesTheBaseItWasNamed:
    """`UX-614`: the worktree is branched from the **default branch**,
    not the round's, and three of round 84's seven tracks hit it.

    Re-measured on round 85's own worktree, one line:

    ```text
    $ git reflog show worktree-agent-a4b6a45b499adfdc3
    5343bd6 …@{0}: branch: Created from origin/main
    ```

    The harness picks the branch; the brief cannot. So the remedy is
    the thing that has to hold, and these clauses **run** it rather
    than reading it: the command is lifted out of `implementer.md` and
    executed against the two shapes a copy can be in.

    `git reset --hard` was the documented remedy until this item.
    Behind - the only direction four measured rounds have produced -
    the two are the same. Diverged they are not, and that is the
    argument: `--ff-only` stops, the reset discards.
    """

    PLACEHOLDER = re.compile(r"<[^>]+>")

    @staticmethod
    def _recovery():
        """The command `implementer.md` tells a track to run when its
        copy is not at its base, read out of the file rather than
        restated here - a clause that carried its own copy would pass
        over a body that documents something else."""
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        section = body.split("## Where your copy starts", 1)[1]
        section = section.split("\n## ", 1)[0]
        lines = [line.split("#")[0].strip()
                 for block in re.findall(r"```bash\n(.*?)```", section, re.S)
                 for line in block.splitlines() if line.strip()]
        found = [line for line in lines
                 if line.startswith("git") and not line.startswith("git log")]
        assert len(found) == 1, (
            f"'Where your copy starts' fences {len(found)} recovery "
            f"command(s), not one: {found}. A track reading two does not "
            f"know which is the instruction")
        return found[0]

    @classmethod
    def _argv(cls, sha):
        command = cls._recovery()
        assert cls.PLACEHOLDER.search(command), (
            f"{command!r} names no base for the track to substitute")
        import shlex
        return shlex.split(cls.PLACEHOLDER.sub(sha, command))

    @staticmethod
    def _git(where, *argv, check=True):
        return subprocess.run(["git", *argv], cwd=where, check=check,
                              capture_output=True, text=True, timeout=60)

    @classmethod
    def _round_and_a_copy_behind_it(cls, tmp_path):
        """The harness's shape: a worktree branched from the default
        branch while the round's branch is three commits ahead, and a
        file the brief cites existing only on the round's."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "base.md").write_text("base\n", encoding="utf-8")
        for argv in (["init", "-q", "-b", "main"],
                     ["config", "user.email", "a@b"],
                     ["config", "user.name", "a"],
                     ["add", "base.md"], ["commit", "-qm", "base"]):
            cls._git(repo, *argv)
        cls._git(repo, "checkout", "-qb", "round")
        for n in range(3):
            (repo / f"docs-{n}.md").write_text("x\n", encoding="utf-8")
            cls._git(repo, "add", f"docs-{n}.md")
            cls._git(repo, "commit", "-qm", f"round {n}")
        tip = cls._git(repo, "rev-parse", "HEAD").stdout.strip()
        cls._git(repo, "checkout", "-q", "main")
        copy = tmp_path / "copy"
        cls._git(repo, "worktree", "add", "-q", "-b", "track", str(copy),
                 "main")
        return repo, copy, tip

    def test_the_documented_recovery_reaches_the_round_s_tip(self, tmp_path):
        """`UX-614`'s acceptance test: a track launched while the
        round's branch is ahead of the default, ending on the round's
        tip - with the file its brief cites now present."""
        _repo, copy, tip = self._round_and_a_copy_behind_it(tmp_path)
        assert not (copy / "docs-2.md").exists(), (
            "the sandbox did not reproduce the shape: the copy already "
            "has the round's work")
        done = subprocess.run(self._argv(tip), cwd=copy, capture_output=True,
                              text=True, timeout=60)
        assert done.returncode == 0, (
            f"the command implementer.md documents does not recover a "
            f"copy three commits behind: {done.stderr}")
        assert self._git(copy, "rev-parse", "HEAD").stdout.strip() == tip, (
            "the copy ran the documented recovery and is not at the base")
        assert (copy / "docs-2.md").exists(), (
            "the recovery moved the branch without the working tree, so "
            "the files the brief cites are still missing")

    def test_the_recovery_refuses_to_discard_the_copy_s_own_work(
            self, tmp_path):
        """Why `--ff-only` and not `git reset --hard`. Behind, the two
        are the same command; diverged, the reset silently throws away
        a commit and the track reports work it no longer has. The
        instruction has to be the one that fails loudly."""
        _repo, copy, tip = self._round_and_a_copy_behind_it(tmp_path)
        (copy / "mine.md").write_text("a track's own work\n", encoding="utf-8")
        self._git(copy, "add", "mine.md")
        self._git(copy, "commit", "-qm", "the track's commit")
        mine = self._git(copy, "rev-parse", "HEAD").stdout.strip()

        done = subprocess.run(self._argv(tip), cwd=copy, capture_output=True,
                              text=True, timeout=60)
        assert done.returncode != 0, (
            "the documented recovery took the base over a diverged copy "
            "and said nothing - the track's own commit is gone")
        assert self._git(copy, "rev-parse", "HEAD").stdout.strip() == mine
        assert (copy / "mine.md").exists()

    def test_the_orchestrator_names_the_recovery_the_track_runs(self):
        """One copy of the instruction, in the two files that carry it:
        `decompose` is what the orchestrator writes the brief from and
        `implementer.md` is what the track reads. `UX-510` put the sha
        in the brief; this puts the *remedy* there, because a brief
        that asks a track to report its base gets a report and then a
        round of working around.

        Measured offset between the two on the skill as written: -247
        characters, one paragraph - so the window is the paragraph, not
        the file. A clause reading the whole body passes on a skill
        that names the command somewhere else entirely.
        """
        verb = " ".join(self._recovery().split()[:3])
        skill = " ".join((SKILLS / "decompose/SKILL.md").read_text(
            encoding="utf-8").split())
        assert verb in skill, (
            f"the decompose skill does not tell the orchestrator to put "
            f"`{verb}` in the brief, so the track's remedy and the brief's "
            f"instruction are two different sentences (UX-614)")
        at = skill.index(verb)
        assert "git rev-parse HEAD" in skill[max(0, at - 400):at + 400], (
            "the skill names the recovery without saying the sha is "
            "derived at launch; a sha remembered from the round document "
            "is the stale base this item is about")


class TestATrackCanReadEveryRefItsCheckoutHas:
    """`UX-623` as filed said a track can read its own branch and
    `origin/*` and nothing else, so a round whose branch is unpushed
    leaves the base uncheckable. Measured, that is false: a linked
    worktree's private git dir has no `refs/` at all, so the whole ref
    store is the shared checkout's and an unpushed branch resolves.

    ```text
    $ ls .git/worktrees/<a worktree>/
    CLAUDE_BASE HEAD ORIG_HEAD commondir gitdir index locked logs
    ```

    These clauses **run** it, on a checkout with no remote configured -
    the strongest form of "unpushed" - and run the base check
    `implementer.md` names against the branch name alone. A clause that
    only read the file would pass over a body claiming the opposite.
    """

    PLACEHOLDER = re.compile(r"<[^>]+>")
    SECTION = "## Which refs your copy can read"

    @classmethod
    def _section(cls):
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        assert cls.SECTION in body, (
            f"implementer.md has no {cls.SECTION!r} section, so a track "
            f"is never told which refs it can resolve (UX-623)")
        return body.split(cls.SECTION, 1)[1].split("\n## ", 1)[0]

    @classmethod
    def _base_check(cls):
        """The command that section tells a track to run against the
        base its brief names, read out of the file - restating it here
        would pass over a body documenting something else."""
        lines = [line.split("#")[0].strip()
                 for block in re.findall(r"```bash\n(.*?)```",
                                         cls._section(), re.S)
                 for line in block.splitlines() if line.strip()]
        assert len(lines) == 1, (
            f"{cls.SECTION!r} fences {len(lines)} commands, not one: "
            f"{lines}. A track reading two does not know which answers")
        return lines[0]

    @staticmethod
    def _git(where, *argv, check=True):
        return subprocess.run(["git", *argv], cwd=where, check=check,
                              capture_output=True, text=True, timeout=60)

    @classmethod
    def _checkout_with_an_unpushed_branch(cls, tmp_path):
        """A checkout with **no remote at all** and a round branch three
        commits ahead of the default, plus a worktree on the default."""
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "base.md").write_text("base\n", encoding="utf-8")
        for argv in (["init", "-q", "-b", "main"],
                     ["config", "user.email", "a@b"],
                     ["config", "user.name", "a"],
                     ["add", "base.md"], ["commit", "-qm", "base"]):
            cls._git(repo, *argv)
        cls._git(repo, "checkout", "-qb", "round")
        for n in range(3):
            (repo / f"round-{n}.md").write_text("x\n", encoding="utf-8")
            cls._git(repo, "add", f"round-{n}.md")
            cls._git(repo, "commit", "-qm", f"round {n}")
        tip = cls._git(repo, "rev-parse", "HEAD").stdout.strip()
        cls._git(repo, "checkout", "-q", "main")
        copy = tmp_path / "copy"
        cls._git(repo, "worktree", "add", "-q", "-b", "track", str(copy),
                 "main")
        assert cls._git(repo, "remote").stdout.strip() == "", (
            "the sandbox configured a remote, so 'unpushed' is not what "
            "is being measured")
        return repo, copy, tip

    def test_a_worktree_resolves_an_unpushed_branch_of_its_checkout(
            self, tmp_path):
        """`UX-623`'s corrected acceptance test. The branch exists only
        in the checkout the copy was made from and has never been
        pushed anywhere; the copy resolves it by name."""
        _repo, copy, tip = self._checkout_with_an_unpushed_branch(tmp_path)
        assert self._git(copy, "rev-parse", "--verify", "round"
                         ).stdout.strip() == tip, (
            "a linked worktree cannot resolve an unpushed branch of the "
            "checkout it was copied from - UX-623 as filed")
        unpushed = self._git(copy, "rev-parse", "--verify",
                             "origin/round", check=False)
        assert unpushed.returncode != 0, (
            "`origin/round` resolved, so the branch was pushed and the "
            "clause above measured the easy case")

    def test_a_branch_ref_lives_in_the_shared_dir_not_the_private_one(
            self, tmp_path):
        """The mechanism, so the clause above reads as a property.

        Asked of the branch's own ref path rather than of whether a
        private `refs/` directory exists: git 2.55 creates one for the
        per-worktree refs (`refs/bisect`, `refs/worktree`) where 2.43
        does not, and a clause reading that directory measures the git
        version instead of the ref store (`UX-623`, caught on CI).
        """
        _repo, copy, _tip = self._checkout_with_an_unpushed_branch(tmp_path)
        private = pathlib.Path(
            self._git(copy, "rev-parse", "--absolute-git-dir").stdout.strip())
        common = pathlib.Path(
            self._git(copy, "rev-parse", "--git-common-dir").stdout.strip())
        assert private != common.resolve(), (
            f"{copy} is not a linked worktree - its git dir is the "
            f"shared one, so nothing here is being measured")
        where = pathlib.Path(self._git(
            copy, "rev-parse", "--git-path",
            "refs/heads/round").stdout.strip()).resolve()
        assert private not in where.parents and where != private, (
            f"the branch's ref path is {where}, inside the worktree's own "
            f"git dir {private} - the ref store is not shared and UX-623 "
            f"as filed was right")

    def test_the_documented_check_answers_from_the_branch_name_alone(
            self, tmp_path):
        """The base check `implementer.md` names, run with a branch name
        substituted for its placeholder: a copy behind the round is
        told so without a commit id and without a fetch."""
        _repo, copy, _tip = self._checkout_with_an_unpushed_branch(tmp_path)
        command = self._base_check()
        assert self.PLACEHOLDER.search(command), (
            f"{command!r} names no base for the track to substitute")
        import shlex
        argv = shlex.split(self.PLACEHOLDER.sub("round", command))
        done = subprocess.run(argv, cwd=copy, capture_output=True,
                              text=True, timeout=60)
        assert done.returncode == 0, (
            f"the check implementer.md documents does not answer for a "
            f"copy behind an unpushed round branch: {done.stderr or argv}")

    def test_the_documented_check_says_no_when_the_copy_has_diverged(
            self, tmp_path):
        """The half that makes it a check rather than a formality. A
        copy carrying its own commit is not behind the base, and taking
        the base would cost that commit - the same distinction
        `--ff-only` draws, asked before anything is moved."""
        _repo, copy, _tip = self._checkout_with_an_unpushed_branch(tmp_path)
        (copy / "mine.md").write_text("a track's own work\n", encoding="utf-8")
        self._git(copy, "add", "mine.md")
        self._git(copy, "commit", "-qm", "the track's commit")
        import shlex
        argv = shlex.split(self.PLACEHOLDER.sub("round", self._base_check()))
        done = subprocess.run(argv, cwd=copy, capture_output=True,
                              text=True, timeout=60)
        assert done.returncode != 0, (
            "the documented check calls a diverged copy behind its base, "
            "so a track runs --ff-only expecting it to work")

    def test_the_section_names_the_reading_a_copy_does_not_get(self):
        """Scoped to the section, because `implementer.md` argues about
        the shared object database two sections earlier and a clause
        reading the whole body would match that instead - the shape
        `falsify` calls matching your own explanation."""
        section = " ".join(self._section().split())
        assert "per-worktree" in section, (
            "the section says which refs resolve without saying what "
            "does not, so a track reads it as 'everything resolves'")
        assert "git -C" in section, (
            "the section does not name the one reading a track is "
            "refused, which is the half UX-623 was filed for")

    def test_the_orchestrator_is_told_the_branch_resolves(self):
        """`decompose` is what the brief is written from. Without this
        the orchestrator pushes, or copies an id, for a reason that was
        measured false - and copying an id is `UX-626`."""
        skill = " ".join((SKILLS / "decompose/SKILL.md").read_text(
            encoding="utf-8").split())
        assert "whether or not it is pushed" in skill, (
            "the decompose skill does not tell the orchestrator that an "
            "unpushed branch resolves in a track's copy (UX-623)")
        at = skill.index("whether or not it is pushed")
        assert "refs/heads" in skill[max(0, at - 400):at + 200], (
            "the skill states the fact without the mechanism that makes "
            "it one, so the next round re-derives it or doubts it")


class TestABriefsBaseResolvesBeforeItIsSent:
    """`UX-626`: round 85's brief named base `2a7d1b8`, no object of
    that name here; the merge it described is `2724972`. Re-measured:

    ```text
    $ git cat-file -t 2a7d1b8   fatal: Not a valid object name 2a7d1b8
    $ git cat-file -t 2724972   commit
    ```

    `decompose` already told the orchestrator to derive the sha rather
    than remember one, and that is the instruction that was in front of
    it. Nothing in this repository runs when a track is launched - no
    hook fires on the Agent tool - so the only check that can exist is
    a command in the skill the brief is written from, and the only
    thing worth guarding about a command is that it **discriminates**.

    So these clauses run it, over the three classes an id falls in:
    absent, a valid object of the wrong type, and a ref that resolves.
    """

    PLACEHOLDER = re.compile(r"<[^>]+>")
    #: The id round 85's brief carried. Absent here and absent from any
    #: sandbox, which is the property the clause below needs.
    ABSENT = "2a7d1b8"

    @staticmethod
    def _section():
        skill = (SKILLS / "decompose/SKILL.md").read_text(encoding="utf-8")
        assert "## 3. Tracks" in skill, (
            "the decompose skill has no Tracks section, so the launch "
            "contract has moved and this class reads nothing")
        return skill.split("## 3. Tracks", 1)[1].split("\n## ", 1)[0]

    @classmethod
    def _resolve_check(cls):
        """The pre-launch check, taken as *the* fenced command in the
        launch section carrying a placeholder for the base. Selected by
        shape rather than by its own text: a clause that grepped for
        `rev-parse` would find whatever command it was told to expect.
        """
        lines = [line.split("#")[0].strip()
                 for block in re.findall(r"```bash\n(.*?)```",
                                         cls._section(), re.S)
                 for line in block.splitlines() if line.strip()]
        carry = [line for line in lines if cls.PLACEHOLDER.search(line)]
        assert len(carry) == 1, (
            f"the launch section fences {len(carry)} command(s) taking a "
            f"base, not one: {carry}. UX-626 is a brief whose base was "
            f"never resolved; two candidates is no check at all")
        return carry[0]

    @staticmethod
    def _git(where, *argv, check=True):
        return subprocess.run(["git", *argv], cwd=where, check=check,
                              capture_output=True, text=True, timeout=60)

    @classmethod
    def _a_repository(cls, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        (repo / "base.md").write_text("base\n", encoding="utf-8")
        for argv in (["init", "-q", "-b", "main"],
                     ["config", "user.email", "a@b"],
                     ["config", "user.name", "a"],
                     ["add", "base.md"], ["commit", "-qm", "base"]):
            cls._git(repo, *argv)
        return repo

    def _run(self, repo, base):
        import shlex
        argv = shlex.split(self.PLACEHOLDER.sub(base, self._resolve_check()))
        return subprocess.run(argv, cwd=repo, capture_output=True,
                              text=True, timeout=60)

    def test_it_refuses_the_id_that_was_never_an_object(self, tmp_path):
        """`UX-626`'s acceptance test: the brief's base, refused before
        a track is launched rather than by the track afterwards."""
        repo = self._a_repository(tmp_path)
        done = self._run(repo, self.ABSENT)
        assert done.returncode != 0, (
            f"the documented pre-launch check accepts {self.ABSENT!r}, "
            f"the id round 85's brief carried and no object here - so a "
            f"brief still goes out with a base nobody resolved")

    def test_it_refuses_an_object_that_is_not_a_base(self, tmp_path):
        """The boundary between the classes, and why the command is not
        `cat-file -t`: a tree id is a valid object, answers with exit 0,
        and is not something a track can start from."""
        repo = self._a_repository(tmp_path)
        tree = self._git(repo, "rev-parse", "HEAD^{tree}").stdout.strip()
        assert self._git(repo, "cat-file", "-t", tree).stdout.strip() \
            == "tree", "the sandbox did not produce a tree id"
        done = self._run(repo, tree)
        assert done.returncode != 0, (
            "the documented check calls a tree a valid base, so it "
            "passes an id that resolves to no commit at all")

    def test_it_accepts_a_ref_the_orchestrator_would_write(self, tmp_path):
        """The class that must pass, or the check is a command that
        always fails and the orchestrator learns to skip it. A branch
        name, because `UX-623` is why the brief may name one."""
        repo = self._a_repository(tmp_path)
        self._git(repo, "branch", "round")
        done = self._run(repo, "round")
        assert done.returncode == 0, (
            f"the documented check refuses a branch that exists: "
            f"{done.stderr.strip()!r}")

    def test_the_skill_says_when_the_check_runs(self):
        """Scoped to the launch section. The command alone is not the
        fix - `UX-614` put "derive the sha" on this page and round 85
        still typed one from memory, so what the section has to carry
        is the moment: before the brief is sent, not after a track
        reports."""
        section = " ".join(self._section().split())
        assert "before the brief goes out" in section, (
            "the launch section fences a resolve command without saying "
            "it runs before the brief is sent, which is the whole of "
            "UX-626 - the id was wrong when it was written")
        assert "written from memory rather than read" in section, (
            "the section drops why the id was wrong; a round reading "
            "'derive the sha' as advice repeats it (UX-626)")


class TestTheDocumentedRevertKeepsTheTracksOwnWork:
    """`UX-625`. The skill has said how to revert since `UX-359`; what
    it had not done was work. `cp <file> /tmp/<file>.bak` names a
    directory that does not exist for any file below the repository
    root, which is every file here:

    ```text
    $ cp .github/workflows/ci.yml /tmp/.github/workflows/ci.yml.bak
    cp: cannot create regular file '…': No such file or directory
    ```

    A step 1 that errors is why a track improvises step 4, and the
    improvisation is `git checkout --`, which discards the track's own
    uncommitted edit in the same file. So these clauses **run** the
    documented recipe on a nested path with work already in it - a
    clause that read the skill for the word "snapshot" would pass over
    a recipe that cannot be executed at all.
    """

    FILE = "<file>"
    SCRATCHPAD = "<the scratchpad path you were given>"
    #: Nested, because the root case is the only one that used to work.
    NESTED = "tests/unit/test_a_guard.py"

    @classmethod
    def _fence(cls):
        body = (SKILLS / "falsify/SKILL.md").read_text(encoding="utf-8")
        assert "## The loop, per guard" in body, (
            "the falsify skill has no loop section, so nothing here "
            "reads the recipe a track is told to run")
        section = body.split("## The loop, per guard", 1)[1]
        blocks = re.findall(r"```bash\n(.*?)```",
                            section.split("\n## ", 1)[0], re.S)
        assert len(blocks) == 1, (
            f"the loop section fences {len(blocks)} bash blocks, not "
            f"one - a track reading two does not know which is the loop")
        return [line.split("#")[0].rstrip()
                for line in blocks[0].splitlines()]

    @classmethod
    def _phases(cls):
        """`(what makes the snapshot, what puts it back)`, split at the
        first step that is not shell - steps 2 and 3 are the mutation
        and the run, and belong to the track rather than to this."""
        lines = cls._fence()
        first = next((i for i, line in enumerate(lines)
                      if line.startswith("python3")), None)
        assert first is not None, (
            "the loop fences no python step, so it is not the loop")
        snapshot = [line for line in lines[:first] if line.strip()]
        revert = [line for line in lines[first:]
                  if line.strip().startswith("cp ")]
        assert snapshot and len(revert) == 1, (
            f"the loop has {len(snapshot)} step(s) before the mutation "
            f"and {len(revert)} copy back after it; UX-625 needs one of "
            f"each or the recipe does not round-trip")
        # The revert runs in a later shell, so it needs the assignments
        # the snapshot phase made.
        return snapshot, [line for line in snapshot if re.match(r"\w+=", line)
                          ] + revert

    @classmethod
    def _script(cls, phase, scratchpad):
        for placeholder in (cls.FILE, cls.SCRATCHPAD):
            assert any(placeholder in line for line in cls._fence()), (
                f"the loop names no {placeholder} for a track to fill "
                f"in, so this clause cannot run what it documents")
        return "\n".join(
            line.replace(cls.SCRATCHPAD, str(scratchpad))
                .replace(cls.FILE, cls.NESTED)
            for line in phase)

    def _worktree(self, tmp_path):
        work = tmp_path / "agent-abcd"
        (work / "tests" / "unit").mkdir(parents=True)
        return work

    def _sh(self, script, cwd):
        return subprocess.run(["sh", "-e", "-c", script], cwd=cwd,
                              capture_output=True, text=True, timeout=60)

    def test_the_snapshot_step_runs_for_a_file_below_the_root(
            self, tmp_path):
        """The step that was broken. Every file in this repository is
        nested, so a recipe that only works at the root works never."""
        work = self._worktree(tmp_path)
        (work / self.NESTED).write_text("original\n", encoding="utf-8")
        scratchpad = tmp_path / "scratchpad"
        scratchpad.mkdir()
        done = self._sh(self._script(self._phases()[0], scratchpad), work)
        assert done.returncode == 0, (
            f"the falsify loop's snapshot step fails for a nested file, "
            f"which is every file here: {done.stderr.strip()!r}")

    def test_the_recipe_returns_the_work_and_not_the_committed_text(
            self, tmp_path):
        """`UX-625`'s acceptance test: a mutation applied to a file the
        track has already edited, reverted, and the track's own edit
        still there. The distinction `git checkout --` cannot draw -
        it would restore "original", which is neither."""
        work = self._worktree(tmp_path)
        target = work / self.NESTED
        target.write_text("original\n", encoding="utf-8")
        scratchpad = tmp_path / "scratchpad"
        scratchpad.mkdir()

        target.write_text("original\nthe track's own edit\n",
                          encoding="utf-8")
        snapshot, revert = self._phases()
        made = self._sh(self._script(snapshot, scratchpad), work)
        assert made.returncode == 0, made.stderr
        target.write_text("original\nthe track's own edit\nMUTATION\n",
                          encoding="utf-8")
        back = self._sh(self._script(revert, scratchpad), work)
        assert back.returncode == 0, back.stderr

        left = target.read_text(encoding="utf-8")
        assert "the track's own edit" in left, (
            "the documented revert discarded the track's uncommitted "
            "work along with the mutation - UX-625 itself")
        assert "MUTATION" not in left, (
            "the documented revert left the mutation in place, so the "
            "next run is green for the wrong reason")

    def test_two_tracks_snapshotting_one_file_do_not_collide(
            self, tmp_path):
        """`UX-615` in the same place: the scratchpad is keyed by the
        project, so two tracks mutating one file share a snapshot name
        unless the recipe separates them. A collision here restores the
        *other* track's copy, which is worse than no snapshot."""
        scratchpad = tmp_path / "scratchpad"
        scratchpad.mkdir()
        script = self._script(self._phases()[0], scratchpad)
        seen = []
        for name in ("agent-aaaa", "agent-bbbb"):
            work = tmp_path / name
            (work / "tests" / "unit").mkdir(parents=True)
            (work / self.NESTED).write_text(f"{name}\n", encoding="utf-8")
            done = self._sh(script, work)
            assert done.returncode == 0, done.stderr
            seen.append(name)
        kept = sorted(p.read_text(encoding="utf-8").strip()
                      for p in scratchpad.rglob("test_a_guard.py"))
        assert kept == seen, (
            f"two tracks snapshotted one file and the scratchpad holds "
            f"{kept} - the second overwrote the first, so its revert "
            f"restores the other track's text (UX-615)")

    def test_the_heading_counts_the_failure_modes_under_it(self):
        """Derived rather than restated. The safe revert was the third
        paragraph under a heading that said two, which is where a
        reader who counts stops reading."""
        body = (SKILLS / "falsify/SKILL.md").read_text(encoding="utf-8")
        heading = re.search(r"^## (\w+) failure modes.*$", body, re.M)
        assert heading, "the falsify skill no longer heads its failure modes"
        section = body.split(heading.group(0), 1)[1].split("\n## ", 1)[0]
        written = {"One": 1, "Two": 2, "Three": 3, "Four": 4}
        assert heading.group(1) in written, (
            f"the heading counts in {heading.group(1)!r}, which this "
            f"clause cannot read")
        found = len(re.findall(r"^\*\*The .*?\.\*\*", section, re.M))
        assert written[heading.group(1)] == found, (
            f"the heading says {heading.group(1)} failure modes and "
            f"{found} follow it; the one that gets dropped is the last, "
            f"and the last is the safe revert (UX-625)")

    def test_the_track_is_told_which_revert_at_the_step_it_reverts(self):
        """`implementer.md` step 5 is what a track reads at mutation
        time; the skill is a click away. Scoped to the loop section,
        because the file argues about `--ff-only` discarding work three
        sections earlier and a whole-body read would match that."""
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        loop = " ".join(body.split("## The loop", 1)[1]
                        .split("\n## ", 1)[0].split())
        assert "git checkout --" in loop, (
            "implementer.md's loop says to revert without naming the "
            "revert that discards the track's own work (UX-625)")
        assert "step 1" in loop, (
            "the loop names the trap without naming what to use "
            "instead, which leaves the track where UX-625 found it")


class TestEachTrackHasItsOwnScratchpad:
    """`UX-615`: the worktrees are isolated and the scratchpad is not.

    Measured on this repository's own, round 85:

    ```text
    session directories under the project key        1
    entries in the one scratchpad                 1592   (19 days)
    files matching `mutate*`                        33
    ```

    The path is keyed by the **project**, so every track of a round
    lands in it at once. Round 84's track had its `mutate.py` - one of
    those 33 - overwritten by another track mid-session, after its
    matrix had run; the surviving names that avoided it carry an item
    id or an agent id, improvised each time.

    The convention is the one name no two tracks share, and these
    clauses **run** the recipe out of `implementer.md` rather than
    reading it, twice, from two worktrees.
    """

    PLACEHOLDER = re.compile(r"<[^>]+>")

    @staticmethod
    def _recipe():
        """The line `implementer.md` tells a track to run before it
        writes a scratch file."""
        body = (AGENTS / "implementer.md").read_text(encoding="utf-8")
        section = body.split("## Where your scratch files go", 1)[1]
        section = section.split("\n## ", 1)[0]
        lines = [line.strip()
                 for block in re.findall(r"```bash\n(.*?)```", section, re.S)
                 for line in block.splitlines() if line.strip()]
        assert len(lines) == 1, (
            f"'Where your scratch files go' fences {len(lines)} commands, "
            f"not one: {lines}")
        return lines[0]

    def _made(self, shared, worktree):
        """The directories the recipe leaves under `shared`, run from
        `worktree` with the scratchpad path substituted for the
        placeholder the brief fills in."""
        worktree.mkdir(parents=True, exist_ok=True)
        command = self._recipe()
        assert self.PLACEHOLDER.search(command), (
            f"{command!r} names no scratchpad for the brief to fill in")
        done = subprocess.run(
            ["sh", "-c", self.PLACEHOLDER.sub(str(shared), command)],
            cwd=worktree, capture_output=True, text=True, timeout=60)
        assert done.returncode == 0, done.stderr
        return sorted(p for p in shared.iterdir() if p.is_dir())

    def test_two_tracks_writing_one_filename_do_not_see_each_other(
            self, tmp_path):
        """`UX-615`'s acceptance test, on the documented recipe: two
        tracks, one filename, and neither reads the other's."""
        shared = tmp_path / "scratchpad"
        shared.mkdir()
        first = self._made(shared, tmp_path / "wt" / "agent-aaaa")
        second = self._made(shared, tmp_path / "wt" / "agent-bbbb")
        assert len(second) == 2, (
            f"two worktrees ran the recipe and it made {len(second)} "
            f"director(y/ies): {[p.name for p in second]}. They share a "
            f"scratchpad, which is what UX-615 is")
        mine, theirs = first[0], next(p for p in second if p != first[0])
        (mine / "mutate.py").write_text("mine\n", encoding="utf-8")
        (theirs / "mutate.py").write_text("theirs\n", encoding="utf-8")
        assert (mine / "mutate.py").read_text(encoding="utf-8") == "mine\n", (
            "the second track's write landed on the first track's file - "
            "round 84's overwrite, reproduced")

    def test_the_directory_is_named_for_the_worktree(self, tmp_path):
        """Not merely *a* unique directory: the name has to be one the
        track can compute without being told, or the brief has to
        allocate it and two tracks launched at once collide again."""
        shared = tmp_path / "scratchpad"
        shared.mkdir()
        made = self._made(shared, tmp_path / "wt" / "agent-cccc")
        assert [p.name for p in made] == ["agent-cccc"], (
            f"the recipe made {[p.name for p in made]}, not a directory "
            f"named for the worktree it was run in")

    def test_the_orchestrator_names_the_same_convention(self):
        """One copy, in the two files that carry it - `decompose` is
        what the brief is written from, `implementer.md` is what the
        track reads. A brief that says nothing leaves the track to
        improvise a suffix, which is what the 33 `mutate*` files in the
        shared directory are."""
        skill = " ".join((SKILLS / "decompose/SKILL.md").read_text(
            encoding="utf-8").split())
        assert 'basename "$PWD"' in skill, (
            "the decompose skill does not tell the orchestrator to name "
            "the track's own scratchpad in the brief (UX-615)")
        assert 'basename "$PWD"' in self._recipe(), (
            "implementer.md's recipe and the skill's are two conventions")


class TestEverySkillWouldLoad:
    """`test_the_skills_point_at_the_guides.py` holds a skill to its
    guide. This holds it to the thing that decides whether it is offered
    at all: a description with no trigger in it is a skill Claude has to
    guess its way to."""

    @staticmethod
    def _skills():
        return sorted(SKILLS.glob("*/SKILL.md"))

    def test_each_declares_a_name_and_a_description(self):
        for path in self._skills():
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
            assert head, f"{path.parent.name} has no frontmatter"
            for field in ("name", "description"):
                assert re.search(rf"^{field}:", head.group(1), re.M), (
                    f"{path.parent.name} declares no {field}")

    def test_each_description_says_when_to_use_it(self):
        """The frontmatter's job is triggering. A description that only
        says what the skill *is* leaves the deciding to chance."""
        for path in self._skills():
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8")).group(1)
            description = re.search(r"^description:\s*(.+?)(?=^\w+:|\Z)",
                                    head, re.M | re.S).group(1)
            assert re.search(r"\buse (when|after|before)\b", description,
                             re.I), (
                f"{path.parent.name}'s description never says when to use "
                f"it: {description.strip()[:120]!r}")


class TestTheConfigurationHasItsOwnGate:
    """The playbook: the suite runs "on any change to `CLAUDE.md`,
    skills or hooks, since that configuration steers the agent and
    deserves the regression testing that code gets." A gate that only
    fires as part of the whole suite is fine until somebody edits a
    hook in a docs-only branch."""

    @staticmethod
    def _text():
        return WORKFLOW.read_text(encoding="utf-8")

    def test_ci_has_a_job_for_it(self):
        assert "agent-config" in self._text(), (
            "ci.yml runs no job named for the agent configuration")

    def test_it_watches_every_file_that_steers_the_agent(self):
        text = self._text()
        block = text.split("agent-config", 1)[1]
        for path in (".claude/**", "CLAUDE.md", "REVIEW.md"):
            assert path in block, (
                f"the agent-config job does not watch {path}, so a change "
                f"to it reaches main without this suite running")

    def test_it_runs_this_file(self):
        assert "test_the_agent_configuration_holds.py" in self._text()


class TestTheProxyRuleIsWhereItGetsRead:
    """`UX-425`. A round-68 sweep found ~30 sightings across ~26 items
    of one defect - an instrument reading a proxy rather than the thing
    it names - and found the repository naming it in four places, none
    of which was a rule document:

        $ grep -rniE "proxy|noise floor|absolute magnitude" \\
              docs/contributing/ .claude/skills/
        $ echo $?
        0

    Zero hits across the fixing guide, the style guide and all four
    skills. The most frequently repeated defect in the record was the
    one thing the rules did not mention. These clauses hold the three
    places it now lives, and that they stay three rather than one.
    """

    GUIDE = REPO / "docs/contributing/fixing-guide.md"
    MEASURE = SKILLS / "measure/SKILL.md"

    def test_the_hard_rules_name_the_class(self):
        """§5 is where a contributor looks for what not to do."""
        text = self.GUIDE.read_text(encoding="utf-8")
        rules = text.split("## 5. Hard rules")[1].split("\n## ")[0]
        assert "proxy" in rules.lower(), (
            "fixing guide section 5 does not name the defect this "
            "repository repeats most - see UX-425")

    def test_the_measure_skill_asks_the_three_questions(self):
        """The rule is stated in the guide and *asked* here, because
        the mistake is made while writing the measurement and is
        invisible when reading it back."""
        text = self.MEASURE.read_text(encoding="utf-8").lower()
        for phrase in ("what quantity does this actually read",
                       "is that the quantity the name claims",
                       "can it tell the answers apart"):
            assert phrase in text, f"the measure skill stops asking: {phrase}"

    @pytest.mark.parametrize("shape,item", (
        ("a text scan that cannot tell code from data", "UX-403"),
        ("a ratio at the noise floor", "UX-420"),
        ("a comparison across machines", "UX-418"),
        ("the wrong artifact or population", "UX-359"),
    ))
    def test_each_shape_names_an_item_that_exists(self, shape, item):
        """A rule with a worked example can be re-checked against the
        record; one without is an assertion. Both documents are allowed
        to cite different examples, so this checks the union."""
        both = (self.GUIDE.read_text(encoding="utf-8")
                + self.MEASURE.read_text(encoding="utf-8"))
        assert item in both, f"nothing cites {item} for {shape!r}"

    @pytest.mark.parametrize("where", ("GUIDE", "MEASURE"))
    def test_every_item_the_rule_cites_resolves(self, where):
        """Per document, not over their union.

        The first draft checked the union and could not discriminate:
        a mutation that broke the guide's citation left the same id in
        the skill and the clause passed. That is the `CLAUDE.md` defect
        of a guard whose setup another gate already excludes - the
        seventh sighting in this repository, and the second in this
        round. Found by the mutation, as both were.
        """
        text = getattr(self, where).read_text(encoding="utf-8")
        section = (text.split("## 5. Hard rules")[1].split("\n## ")[0]
                   if where == "GUIDE"
                   else text.split("## Before you trust the number")[1])
        cited = sorted(set(re.findall(r"UX-(\d+)", section)))
        assert cited, f"{where} cites no worked example, so the rule " \
                      f"cannot be re-checked against the record"
        missing = [f"UX-{number}" for number in cited
                   if not list((REPO / "docs/backlog/scenarios")
                               .glob(f"UX-{int(number):04d}-*.md"))]
        assert missing == [], (
            f"{where} cites {missing}, and no task file has those ids")

    def test_claude_md_points_at_the_rule_rather_than_restating_it(self):
        """The page is under an 80-line bound, and two summaries of a
        rule that lives nowhere else is how the rule stops being one."""
        text = CLAUDE_MD.read_text(encoding="utf-8")
        assert "proxy" in text, "the day-one page dropped the class entirely"
        assert "measure` skill" in text or "`measure`" in text, (
            "CLAUDE.md names the class but not where its rule is, so a "
            "session meets the summary and never the rule")


class TestTheCiFirstAdviceStaysTrue:
    """`UX-426`. The `verify` skill's section 7 tells a session to open
    the PR before the work, and the whole reason is one fact about
    `.github/workflows/ci.yml`: it runs on `pull_request` and pushes to
    `main`, so a branch with no PR gets no runs.

    That is two copies of one fact, which this repository has watched
    drift three separate times. If someone adds `push:` on all branches
    the advice becomes wrong *and* unnecessary, and nothing else would
    say so.
    """

    VERIFY = SKILLS / "verify/SKILL.md"

    @staticmethod
    def _triggers():
        """The branches each event in `on:` is filtered to."""
        text = WORKFLOW.read_text(encoding="utf-8")
        block = text.split("\non:\n", 1)[1].split("\n\n", 1)[0]
        found, event = {}, None
        for line in block.splitlines():
            if re.fullmatch(r"  (\w+):", line):
                event = line.strip().rstrip(":")
            elif event and "branches:" in line:
                found[event] = re.findall(r"[\w./-]+", line.split(":", 1)[1])
        return found

    def test_the_workflow_runs_only_where_the_skill_says(self):
        assert self._triggers() == {"push": ["main"], "pull_request": ["main"]}, (
            f"ci.yml's triggers are {self._triggers()}, and the verify "
            f"skill's section 7 tells sessions to open a PR early because "
            f"they are push-to-main plus pull_request. Fix whichever is "
            f"wrong - if CI now runs on every push, the advice is obsolete")

    def test_the_skill_states_the_fact_it_rests_on(self):
        text = self.VERIFY.read_text(encoding="utf-8")
        assert "pull_request" in text and "no PR collects no runs" in text, (
            "section 7 gives the advice without the fact that justifies it, "
            "so a later round cannot tell when it stops applying")

    def test_it_is_guidance_and_says_so(self):
        """The half that keeps this honest. One round is not a baseline,
        and a process claim asserted on one sample is `UX-420`'s mistake
        one level up - so section 7 must keep saying it is unmeasured,
        and the hard rules must keep not carrying it."""
        text = self.VERIFY.read_text(encoding="utf-8")
        assert "One round is not a baseline" in text, (
            "section 7 stopped admitting it is one session's experience")
        rules = (REPO / "docs/contributing/fixing-guide.md").read_text(
            encoding="utf-8").split("## 5. Hard rules")[1].split("\n## ")[0]
        assert "draft" not in rules.lower(), (
            "the PR-first loop was promoted into the hard rules; it has "
            "not been measured against the alternative even once")


class TestTheRulesCardIsTheEntryPoint:
    """`UX-505`: the rules on one page, the incidents behind it.

    The fixing guide opens with "if you have limited context budget:
    read only this file" and is the budget. Every rule is stated once
    and then argued with the incident that produced it, which is why
    the rules are trusted and also why a session paid the whole guide
    to learn them. `UX-584` derives the two sizes in the documents
    themselves; no figure is restated here.

    Split by register: the card carries the rules, the guide keeps every
    incident. So the card has two ways to rot — it can grow back into a
    second guide, and it can carry a rule the guide does not argue —
    and one clause each.
    """

    CARD = REPO / "docs/contributing/rules.md"
    GUIDE = REPO / "docs/contributing/fixing-guide.md"

    #: The card's budget. Not "smaller than the guide" - that would let
    #: it reach 300 lines and still pass, which is the state this item
    #: is about.
    CAP = 80

    def test_the_card_stays_a_card(self):
        lines = self.CARD.read_text(encoding="utf-8").splitlines()
        assert len(lines) <= self.CAP, (
            f"{self.CARD.name} is {len(lines)} lines, cap is {self.CAP} - "
            f"a card that grows back into a guide is a second guide, and "
            f"two copies of a rule is how the copies disagree")

    def test_it_is_a_fraction_of_what_it_replaces(self):
        """The measurement the filing asks for, as a property: what a
        session reads first is a small multiple smaller than the
        argument behind it. Ten is not a magic number - it is the order
        of magnitude that makes reading the card first worth doing."""
        card, guide = (len(p.read_bytes()) for p in (self.CARD, self.GUIDE))
        assert card * 5 < guide, (
            f"the card is {card} B against the guide's {guide} B; at that "
            f"ratio a session may as well read the guide")

    def test_every_section_of_the_card_names_the_guide_section(self):
        """The card cannot carry a rule the guide does not argue. Read
        per **section**, because the rule sentences are deliberately
        rewritten short - a clause matching sentences would be asserting
        the card is a copy, which is the thing it must not be."""
        import re
        text = self.CARD.read_text(encoding="utf-8")
        cited = set()
        for heading in re.findall(r"^## .*$", text, re.M):
            cited.update(re.findall(r"§(\d+[a-z]?)", heading))
        assert cited, "no section of the card names a guide section"
        headings = self.GUIDE.read_text(encoding="utf-8")
        for section in sorted(cited):
            assert re.search(rf"^## {re.escape(section)}\.", headings, re.M), (
                f"the card cites the guide's §{section} and the guide has "
                f"no such section - the card is carrying a rule nothing "
                f"argues")

    def test_the_guide_says_the_card_is_the_entry_point(self):
        """Otherwise a session that opens the guide first - which is
        what every document still linking to it does - never learns the
        card exists."""
        head = "\n".join(self.GUIDE.read_text(encoding="utf-8").splitlines()[:12])
        assert "rules.md" in head, (
            "the guide's opening does not send a reader to the card")

    #: `UX-585`: a named guard that carries no marker, and why. Not
    #: "everything unmarked" - that would make the clause below vacuous.
    #: Each entry is asserted *still* unmarked, so the list shrinks when
    #: the marker lands rather than hiding one that did.
    #: `UX-600` emptied it: the one deferral was the round's own
    #: parallelism, and its marker landed.
    UNMARKED = {}

    #: Named beside a guard, and not one: a tool is the mechanism the
    #: rule asks for, and the test file next to it is what holds it.
    NOT_A_GUARD_FILE = ("dev_close_task.py",)

    @staticmethod
    def _slug(rule):
        """The rule sentence as an anchor. Rewriting a rule changes its
        slug, which is the point - a marker names *that* sentence."""
        plain = re.sub(r"[`*'’]", "", rule)
        return re.sub(r"-+", "-",
                      re.sub(r"[^a-z0-9]+", "-", plain.lower())).strip("-")

    def _rule_rows(self):
        """`[(rule, guard cell)]` from the rule tables only. The §6a
        stream table has three columns and is not rules; the header row
        is dropped by its text, not by its position."""
        rows = []
        for line in self.CARD.read_text(encoding="utf-8").splitlines():
            if not (line.startswith("| ") and line.count("|") == 3
                    and "---" not in line):
                continue
            rule, guard = (one.strip() for one in line.split("|")[1:3])
            if (rule, guard) != ("rule", "guard"):
                rows.append((rule, guard))
        return rows

    @staticmethod
    def _named_files(cell):
        """Every guard **file** a cell names - a test module or a hook."""
        return re.findall(r"[\w./-]+\.(?:py|sh)", cell)

    def test_the_card_names_a_guard_for_the_rules_that_have_one(self):
        """A rule with no guard is a rule kept by attention alone, and
        the card is where that is visible. Not every rule can have one -
        "never widen scope" is judgement - so this asserts the column is
        populated rather than full.

        Reads the **rule** tables only. The first writing counted every
        row on the page, and the §6a stream table has a third column of
        prose that is never empty: emptying every real guard cell left
        it green, on eight rows that are not rules at all.
        """
        rows = self._rule_rows()
        assert len(rows) > 20, f"the card has {len(rows)} rule rows"
        guarded = [one for one in rows
                   if self._named_files(one[1]) or "`make " in one[1]]
        assert len(guarded) >= 8, (
            f"only {len(guarded)} of {len(rows)} rule rows name a guard; "
            f"the column is what makes an unguarded rule visible")

    def test_every_named_guard_carries_the_marker_for_its_row(self):
        """`UX-585`: the clause above asserts eight cells are populated,
        so a wrong guard name passes it. A marker is the guard's own
        claim to hold that rule, and this reads it."""
        wrong = []
        for rule, cell in self._rule_rows():
            want = "holds: rules.md#" + self._slug(rule)
            for name in self._named_files(cell):
                found = [one for one in (REPO / "tests/unit" / name,
                                         REPO / name) if one.exists()]
                if not found:
                    wrong.append(f"{rule!r} names {name}, which does not exist")
                elif pathlib.Path(name).name in self.NOT_A_GUARD_FILE:
                    continue
                elif want in found[0].read_text(encoding="utf-8"):
                    continue
                elif name not in self.UNMARKED:
                    wrong.append(f"{name} is the guard for {rule!r} and does "
                                 f"not say so: no `{want}` line")
        assert not wrong, "\n".join(wrong)

    def test_every_marker_in_the_tree_names_a_row_that_names_it(self):
        """The other direction. A rule rewritten without re-pointing its
        marker leaves a guard claiming a sentence that no longer reads
        that way, and the clause above cannot see it."""
        slugs = {self._slug(rule): cell for rule, cell in self._rule_rows()}
        # `--others` too: a marker in a guard added but not yet committed
        # is the case this clause is most likely to be run against.
        listed = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO, check=True, capture_output=True, text=True).stdout.split()
        carriers, wrong = [], []
        for rel in listed:
            if rel.startswith("docs/backlog/"):  # the Outcome quotes them
                continue
            path = REPO / rel
            if not path.is_file() or path.suffix not in (".py", ".sh", ".md"):
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            if "holds: rules.md#" not in text:
                continue
            carriers.append(rel)
            for slug in re.findall(r"holds: rules\.md#([a-z0-9-]+)", text):
                if slug not in slugs:
                    wrong.append(f"{rel} holds `{slug}`, and the card has no "
                                 f"rule with that slug")
                elif pathlib.Path(rel).name not in slugs[slug]:
                    wrong.append(f"{rel} holds `{slug}`, whose row names "
                                 f"{slugs[slug]!r} instead")
        assert len(carriers) >= 8, (
            f"only {len(carriers)} files in the tree carry a marker")
        assert not wrong, "\n".join(wrong)

    def test_a_deferred_marker_is_still_missing(self):
        """`UNMARKED` is a debt, not an exemption: an entry that has been
        marked must leave the list, or the list becomes the place a
        guard nobody checked goes to hide."""
        stale = []
        for name, why in self.UNMARKED.items():
            path = REPO / "tests/unit" / name
            assert path.exists(), f"{name} is deferred and does not exist"
            if "holds: rules.md#" in path.read_text(encoding="utf-8"):
                stale.append(f"{name} carries a marker now ({why})")
        assert not stale, "\n".join(stale)

    def test_every_make_target_the_column_names_exists(self):
        """A cell may name a target rather than a file - `make
        check-clean` is the whole guard for two rows."""
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        real = set(re.findall(r"^([a-z][\w-]*):", makefile, re.M))
        named = {one for _, cell in self._rule_rows()
                 for one in re.findall(r"`make ([a-z][\w-]*)", cell)}
        assert named, "the guard column names no make target"
        assert named <= real, f"the card names absent target(s): {named - real}"

    def test_the_marker_scan_reads_a_population(self):
        """Every clause above passes on a card whose rows name nothing."""
        named = [one for one in self._rule_rows() if self._named_files(one[1])]
        assert len(named) >= 8, (
            f"only {len(named)} rule rows name a guard file")
        assert self._slug("Never widen scope") == "never-widen-scope"
