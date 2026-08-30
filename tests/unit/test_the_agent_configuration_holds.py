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

    def test_it_points_at_the_guide_rather_than_restating_it(self):
        """`UX-240`'s rule for skills, and it holds here for the same
        reason: two copies of one rule is how the copies disagree."""
        text = self._text()
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

    def test_neither_can_edit_the_tree(self):
        """Both are read-and-report. A verifier that could fix what it
        found would be judging its own work, which is the one thing it
        exists not to do."""
        for path in self._files():
            head = _FRONTMATTER.match(path.read_text(encoding="utf-8")).group(1)
            tools = re.search(r"^tools:\s*(.+)$", head, re.M).group(1)
            for forbidden in ("Edit", "Write", "MultiEdit", "NotebookEdit"):
                assert forbidden not in tools, (
                    f"{path.name} may use {forbidden}; both agents report only")

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
