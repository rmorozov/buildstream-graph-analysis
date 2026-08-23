"""UX-197: the seams round 21 verified into round 20's landings.

Six of them, four in code this project shipped one round earlier. Each
was reproduced before it was fixed; what is guarded here is the fixed
behaviour, and each guard was falsified against the original defect.

The through-line worth naming: every one of these is a claim that was
*written down* and not *checked*. `UX-188` left a comment saying the
timeline must not print its scratch path, and printed it. `UX-183`'s
log said stdout was compared with progress on and off, and compared
off against off. `UX-185` declared a `suspended` field nothing ever
assigned. That is the class this file exists to close, one instance at
a time.
"""
import os
import re
import signal
import subprocess
import sys
import time

import pytest

REPO = os.getcwd()


class TestTheTimelinePrintsNoPathThatIsAlreadyGone:
    """Seam 2. Reproduced before the fix:

        Successfully generated trace! Open
        /tmp/bga-timeline-umfcn7q8/plane1.json in chrome://tracing ...

    naming a file inside the scratch directory `render()` deletes on its
    way out. `UX-188` moved that sentence from stdout to stderr and
    wrote a comment saying a timeline user must not see it - the stream
    changed and the sentence did not.
    """

    def test_every_path_it_prints_exists_afterwards(self, tmp_path, snapshot):
        out = tmp_path / "timeline.json"
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["timeline", str(snapshot), "-o", str(out)],)],
            capture_output=True, text=True, cwd=REPO)
        assert result.returncode == 0, result.stderr

        printed = set(re.findall(r"/[\w./-]+\.json", result.stdout + result.stderr))
        assert printed, "it printed no path at all, which is its own bug"
        missing = sorted(p for p in printed if not os.path.exists(p))
        assert not missing, (
            f"told the user to open {missing}, which does not exist - "
            f"the scratch directory is gone by the time they read it")

    def test_the_converter_still_says_it_when_called_directly(self, tmp_path):
        """The sentence is useful to `bga log-to-chrome`; only the
        composing caller suppresses it. Deleting the line outright would
        have passed the guard above and cost a real user their path."""
        log = tmp_path / "build.log"
        log.write_text(_WRAPPED)
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["log-to-chrome", str(log), str(tmp_path / "out.json")],)],
            capture_output=True, text=True, cwd=REPO)
        assert "Successfully generated" in result.stderr
        assert str(tmp_path / "out.json") in result.stderr

    def test_a_missing_input_is_not_a_silent_success(self, tmp_path):
        """Adjacent, and pre-existing: the two `FileNotFoundError` paths
        printed to stdout and `return`ed None, which `sys.exit(None)`
        renders as exit 0."""
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["log-to-chrome", "/nope/missing.log", str(tmp_path / "o.json")],)],
            capture_output=True, text=True, cwd=REPO)
        assert result.returncode != 0, "a missing input exited 0"
        assert result.stdout == "", "the error went to stdout"
        assert "Could not find input file" in result.stderr


class TestTheDeadSuspendedFieldIsGone:
    """Seam 3. `RunContext.suspended` was declared, never assigned and
    never read - one letter from the `suspension` property that does the
    work, so a consumer reaching for the obvious name got `None` for a
    run that really had slept."""

    def test_the_field_does_not_exist(self):
        from bga.ingest.models import RunContext

        assert "suspended" not in RunContext.__dataclass_fields__, (
            "a field nothing assigns is a trap, not an API")

    def test_the_accessor_that_works_still_does(self):
        from bga.ingest.models import RunContext

        run = RunContext(
            build_outcome={"suspended": {"suspended_seconds": 900.0}})
        assert run.suspension == {"suspended_seconds": 900.0}
        assert run.incomplete_reason == "suspended"

    def test_a_run_that_did_not_sleep_says_so(self):
        from bga.ingest.models import RunContext

        run = RunContext(build_outcome={})
        assert run.suspension is None
        assert run.incomplete_reason is None


class TestCtrlCDuringBstShowLeavesNoChild:
    """Seam 4. `UX-183` replaced `subprocess.run` with `Popen` plus a
    poll loop so it could draw a ticker, and lost `run`'s
    kill-the-child-on-exception contract. Reproduced: a 120s child, the
    parent taking a KeyboardInterrupt, and the child still alive
    afterwards - the `UX-157`/`UX-163` lifecycle rule, one phase over.
    """

    def test_the_child_dies_with_its_parent(self, tmp_path):
        marker = tmp_path / "child.pid"
        probe = tmp_path / "probe.py"
        probe.write_text(_ORPHAN_PROBE % {"marker": marker, "repo": REPO})

        subprocess.run([sys.executable, str(probe)], capture_output=True,
                       text=True, timeout=60, cwd=REPO)

        assert marker.exists(), "the probe never started a child to orphan"
        pid = int(marker.read_text().strip())
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if not _alive(pid):
                return
            time.sleep(0.1)
        os.kill(pid, signal.SIGKILL)          # do not leak it out of the suite
        pytest.fail(f"pid {pid} outlived the interrupted parent")


class TestTheCountsAreRight:
    """Seam 5. Both were hand-written figures the code had outgrown."""

    def test_round_20_counts_its_own_items(self):
        text = open("docs/audits/round-20.md", encoding="utf-8").read()
        assert "All ten items UX-183..UX-192" in text, (
            "UX-183..UX-192 is ten items; the section said twelve")

    def test_the_status_table_does_not_hardcode_the_alias_count(self):
        """The first version of this guard asserted the row named
        `len(TOOL_ALIASES)` exactly - and `UX-194` broke it one hour
        later by adding an eighteenth alias. A row that has to be edited
        every time a command is added is a row that will be stale again,
        which is the whole of seam 5.

        So the row says "every alias command", and this asserts it names
        no number at all. The *coverage* is checked where it belongs, in
        `test_help_is_short.py`, which reads `TOOL_ALIASES` itself.
        """
        import re

        # UX-232 moved closed rows to `closed.md`; UX-192 is one of
        # them. The guard follows the row rather than the filename -
        # a guard pinned to one file goes quiet the day the row moves.
        rows = []
        for name in ("docs/backlog/scenarios/README.md",
                     "docs/backlog/scenarios/closed.md"):
            rows += [line for line in
                     open(name, encoding="utf-8").read().splitlines()
                     if line.startswith("| UX-192 |")]
        assert len(rows) == 1, f"UX-192 has {len(rows)} rows across the backlog"
        row = rows[0]
        stale = re.search(r"(all )?\b(\d+|ten|eleven|twelve|seventeen|eighteen)\b"
                          r" alias commands", row)
        assert not stale, (
            f"the UX-192 row names a count ({stale.group(0)}) that the next "
            f"command added will make wrong")
        assert "alias command" in row


class TestTheSchemaGuardsCannotVanishQuietly:
    """Seam 6. `pytest.importorskip` at module scope turned 25 guards
    into one `skipped` line whenever `jsonschema` was absent - measured
    in a clean venv as `collected 0 items / 1 skipped`."""

    def test_no_test_module_collects_behind_an_importorskip(self):
        """UX-235 generalised this from one file to all of them.

        It named `tests/unit/test_output_schemas.py` and looked only
        there, so `test_publish_the_join.py` - added in round 25 with a
        module-scope `importorskip` on line 27 - walked straight past
        it and hid twenty-one guards behind one import for two rounds.
        A guard written for the instance rather than the class is how
        the class comes back.

        Module *scope* is the defect: an `importorskip` inside a test
        skips that test, which is the correct and intended use.
        """
        import pathlib

        offenders = []
        for path in sorted(pathlib.Path("tests").rglob("test_*.py")):
            for number, line in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1):
                if "importorskip" not in line or line.lstrip().startswith("#"):
                    continue
                if line == line.lstrip():          # no indentation: module scope
                    offenders.append(f"{path}:{number}")
        assert offenders == [], (
            f"a module-scope importorskip hides every guard in its file: "
            f"{offenders}. Use a module-level `skipif` marker on the tests "
            f"that need the import, so the rest of the file still runs.")

    def test_ci_declares_itself_a_dev_environment(self):
        import yaml

        workflow = yaml.safe_load(open(".github/workflows/ci.yml", encoding="utf-8"))
        assert workflow.get("env", {}).get("BGA_EXPECT_DEV") == "1", (
            "without this the schema guards skip silently in CI too")

    def test_the_canary_fails_rather_than_skips_when_dev_is_claimed(self):
        """Driven for real: run that one test with `BGA_EXPECT_DEV` set
        and `jsonschema` made unimportable."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/unit/test_output_schemas.py::test_the_dev_extras_are_actually_here",
             "-q", "-p", "no:cacheprovider", "-p", "_hide_jsonschema"],
            capture_output=True, text=True, cwd=REPO,
            env=dict(os.environ, BGA_EXPECT_DEV="1",
                     PYTHONPATH=os.path.join(REPO, "tests", "support")))
        assert "1 failed" in result.stdout, result.stdout[-1500:]
        assert "pip install -e" in result.stdout, (
            "the failure should name the fix")


def _alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""

_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""

# Run out-of-process: the interrupt has to arrive at a real poll loop
# around a real child, which is the whole thing under test.
_ORPHAN_PROBE = '''
import os, signal, subprocess, sys
sys.path.insert(0, %(repo)r)
from tools import bst_show_to_graph as m

real_popen = subprocess.Popen
def popen(cmd, **kw):
    return real_popen(
        ["/bin/sh", "-c", "echo $$ > %(marker)s; exec sleep 120"], **kw)
subprocess.Popen = popen

def on_alarm(signum, frame):
    raise KeyboardInterrupt("simulated Ctrl-C")
signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(2)

try:
    m.run_bst_show(".", ["all.bst"], bst_bin="bst")
except BaseException as error:
    print(type(error).__name__)
'''


@pytest.fixture
def snapshot(tmp_path):
    """A snapshot shaped like one `bga snapshot` writes, both planes."""
    import gzip
    import shutil

    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree("tests/fixtures/golden/mixed_task_kinds", snap / "run")
    os.remove(snap / "run" / "expected_output.json")
    with gzip.open(snap / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW)
    return snap


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
