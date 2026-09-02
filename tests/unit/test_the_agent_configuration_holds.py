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
"""
import json
import pathlib
import re
import subprocess

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
        must land on the rules, not on 34 KB of the incidents that
        produced them.
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
    read only this file" and is 34,400 bytes — the file *is* the
    budget. Every rule is stated once and then argued with the incident
    that produced it, which is why the rules are trusted and also why a
    session paid 34 KB to learn twelve of them.

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

    def test_the_card_names_a_guard_for_the_rules_that_have_one(self):
        """A rule with no guard is a rule kept by attention alone, and
        the card is where that is visible. Not every rule can have one -
        "never widen scope" is judgement - so this asserts the column is
        populated rather than full.

        Reads the **rule** tables only, by their two columns. The first
        writing counted every row on the page, and the §6a stream table
        has a third column of prose that is never empty: emptying every
        real guard cell left it green, on eight rows that are not rules
        at all.
        """
        rows = [line for line in self.CARD.read_text(encoding="utf-8")
                .splitlines()
                if line.startswith("| ") and line.count("|") == 3
                and "---" not in line]
        assert len(rows) > 20, f"the card has {len(rows)} rule rows"
        guarded = [row for row in rows
                   if row.split("|")[2].strip() not in ("", "-", "—", "guard")]
        assert len(guarded) >= 8, (
            f"only {len(guarded)} of {len(rows)} rule rows name a guard; "
            f"the column is what makes an unguarded rule visible")
