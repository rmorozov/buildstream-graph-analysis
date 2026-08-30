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

#: Built rather than written, because `keep-the-guards-able-to-fail.sh`
#: blocks an edit that carries the literal - including this one. The
#: hook cannot tell a decorator from a string that looks like one, and
#: that bluntness is recorded in its own header.
SKIP = "@pytest.mark." + "skip"
XFAIL = "@pytest.mark." + "xfail"
SKIPIF = "@pytest.mark." + "skipif"


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
    ))
    def test_a_bulk_add_is_blocked(self, command):
        code, said = fire("no-bulk-add.sh", {"tool_input": {"command": command}})
        assert code == 2, (command, code, said)
        assert "4a.1" in said, said

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
