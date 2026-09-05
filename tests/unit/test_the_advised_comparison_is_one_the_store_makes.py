"""UX-577: the advised `bga compare` is a command, not a refusal.

`UX-78` refuses a full baseline against an incremental candidate with
`EXIT_MISMATCHED_RUNS`. `next_steps` advised `compare @prev @last`
whenever the run sat in a store, so a store holding one cold run and
one incremental run advised the one pair it will not make.
"""
import contextlib
import io
import json
import pathlib
import re
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.exceptions import EXIT_CODES, EXIT_OK
from tools import bga_snapshot

COLD = REPO / "tests/fixtures/same_build_twice_cold/run"
INCREMENTAL = REPO / "tests/fixtures/same_build_twice_incremental/run"

CLI_GUIDE = REPO / "docs/guides/cli.md"

# The seed store `UX-330` plants and the guide's block is taken from.
DEMO_PATH = "/tmp/bga-demo"

# `bga snapshot` runs the build again, which needs `bst` and a sandbox -
# the same exemption `test_the_printed_sentences_are_contracts.py`
# argues, and for the same reason. It is parsed instead of run.
UNRUNNABLE = {"snapshot"}


def _store(tmp_path, *runs):
    """A project holding one snapshot per fixture, oldest first."""
    project = tmp_path / "project"
    for index, fixture in enumerate(runs):
        snapshot = project / ".bga" / "runs" / f"2026090{index + 1}T000000Z"
        snapshot.mkdir(parents=True)
        shutil.copytree(fixture, snapshot / "run")
    (project / "project.conf").write_text("name: ux577\n", encoding="utf-8")
    return project


def _run(argv):
    """One `bga` invocation, in-process, returning its exit code."""
    from bga.cli import main

    with io.StringIO() as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
        try:
            return main(argv) or EXIT_OK
        except SystemExit as exit_code:
            return exit_code.code or EXIT_OK


def _steps(run_dir):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", str(run_dir), "--format", "json"])
    return {s["id"]: s for s in json.loads(buffer.getvalue())["next_steps"]}


def _last_run(project):
    stamps = sorted((project / ".bga" / "runs").iterdir())
    return stamps[-1] / "run"


class TestTheStoreDecidesWhetherThePairIsAdvised:

    def test_a_matched_pair_is_advised_and_runs(self, tmp_path, monkeypatch):
        project = _store(tmp_path, INCREMENTAL, INCREMENTAL)
        step = _steps(_last_run(project))["compare-with-the-run-before"]
        assert step["argv"] == ["bga", "compare", "@prev", "@last"]
        monkeypatch.chdir(project)
        assert _run(step["argv"][1:]) == EXIT_OK

    def test_a_mismatched_pair_is_the_refusal_this_guards(self, tmp_path,
                                                          monkeypatch):
        """The gap itself: `@prev @last` on a cold+incremental store."""
        project = _store(tmp_path, COLD, INCREMENTAL)
        monkeypatch.chdir(project)
        assert _run(["compare", "@prev", "@last"]) == \
            EXIT_CODES["mismatched runs"]

    def test_a_mismatched_pair_is_not_advised(self, tmp_path):
        project = _store(tmp_path, COLD, INCREMENTAL)
        offered = _steps(_last_run(project))
        assert "compare-with-the-run-before" not in offered, (
            f"`compare @prev @last` exits "
            f"{EXIT_CODES['mismatched runs']} on this store and is still "
            f"advised; got {sorted(offered)}")
        assert "compare-with-a-run-that-pairs" not in offered, (
            "no run in this store shares @last's mode, so there is no pair "
            "to name")

    def test_the_run_that_would_pair_is_named_and_runs(self, tmp_path,
                                                       monkeypatch):
        project = _store(tmp_path, INCREMENTAL, COLD, INCREMENTAL)
        step = _steps(_last_run(project))["compare-with-a-run-that-pairs"]
        assert step["argv"] == [
            "bga", "compare", "@20260901T000000Z", "@last"], step["argv"]
        assert "full" in step["reason"] and "incremental" in step["reason"]
        monkeypatch.chdir(project)
        assert _run(step["argv"][1:]) == EXIT_OK, (
            "the advised pair must be one the store makes")

    def test_an_unknown_mode_is_not_a_mismatch(self, tmp_path):
        """`_check_run_modes`' rule: `unknown` is not guessed into
        either bucket, so it must not silently withdraw the advice."""
        project = _store(tmp_path, COLD, INCREMENTAL)
        context = _last_run(project) / "run-context.json"
        payload = json.loads(context.read_text(encoding="utf-8"))
        payload.pop("queue_summary", None)
        context.write_text(json.dumps(payload), encoding="utf-8")
        assert "compare-with-the-run-before" in _steps(_last_run(project))


class TestTheGuideAdvisesWhatTheSeedStoreCanRun:
    """`UX-577`'s third clause. The subject is the fenced block under
    *What to run next*, and nothing else in the guide - the paragraphs
    around it argue for the block and quote commands as prose."""

    def _block(self):
        text = CLI_GUIDE.read_text(encoding="utf-8")
        section = text.split("### What to run next", 1)
        assert len(section) == 2, "the guide's next-step heading moved"
        fence = re.search(r"```text\n(.*?)```", section[1], re.S)
        assert fence, "no fenced block under the next-step heading"
        return fence.group(1)

    def test_every_advised_command_exits_zero(self, tmp_path, monkeypatch):
        store = tmp_path / "bga-demo"
        assert _run(["gen-synthetic", "--store", str(store)]) == EXIT_OK
        monkeypatch.chdir(store)
        commands = [line.split() for line in self._block().splitlines()
                    if line.strip().startswith("bga ")]
        assert commands, "the block advises no command"
        for argv in commands:
            argv = [word.replace(DEMO_PATH, str(store)) for word in argv[1:]]
            if argv[0] in UNRUNNABLE:
                bga_snapshot.create_parser().parse_args(argv[1:])
                continue
            assert _run(argv) == EXIT_OK, f"`bga {' '.join(argv)}` did not"

    def test_the_advised_commands_are_the_ones_the_tool_prints(
            self, tmp_path, monkeypatch):
        """So the block cannot drift into a set of commands that happen
        to exit 0 but are not the advice."""
        store = tmp_path / "bga-demo"
        assert _run(["gen-synthetic", "--store", str(store)]) == EXIT_OK
        monkeypatch.chdir(store)
        printed = {
            " ".join(step["argv"]).replace(str(store), DEMO_PATH)
            for step in _steps("@last").values()
        }
        quoted = {line.strip() for line in self._block().splitlines()
                  if line.strip().startswith("bga ")}
        assert quoted == printed, (
            f"the guide quotes {sorted(quoted - printed)} the tool does not "
            f"print, and omits {sorted(printed - quoted)}")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
