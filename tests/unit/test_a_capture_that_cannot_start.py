"""UX-324: a capture that cannot start says so, and leaves nothing.

The README's own first command, on a machine without `bst`:

    $ bga snapshot -- bst build all.bst
    Traceback (most recent call last):
      ... 32 lines ...
    FileNotFoundError: [Errno 2] No such file or directory: 'bst'

and a snapshot directory left behind holding `build.log`,
`capture-context.txt` and a zero-byte `plane2.log`. `bga doctor` on the
same machine opens with `[FAIL] bst-present` and a one-line remedy, so
the tool knew the answer and nothing asked it.

Three things are held here, and the second is the one with teeth:

* the refusal is one sentence naming the remedy and `bga doctor`;
* **nothing is written** - the store is compared byte for byte across
  the refusal, which is the clause a bypassed check reddens;
* the debris that already exists on disk is described honestly. "The
  build produced no elements" is a claim about a build that *ran*, and
  it sends the reader to look at their project instead of their machine.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import run_store
from tools.bga_snapshot import build_ever_started, why_the_build_cannot_start

# The wrapper log's own shapes, copied from `bst_run_wrapped.run_wrapped`
# rather than invented: the first two lines are written before `Popen`,
# and everything after them means the process existed.
NEVER_STARTED = (
    "[wrapper][2026-08-27 08:16:19,570] INFO: Executing command: bst build all.bst\n"
    "[wrapper][2026-08-27 08:16:19,570] INFO: bga-clocks start wall=1 monotonic=2\n")
INTERRUPTED = NEVER_STARTED + (
    "[wrapper][2026-08-27 08:16:20,000] INFO: Stopping the build after "
    "KeyboardInterrupt\n")
RAN_AND_FAILED = NEVER_STARTED + (
    "[wrapper][2026-08-27 08:16:20,000] INFO: Error loading project\n"
    "[wrapper][2026-08-27 08:16:21,000] INFO: bga-clocks end wall=3 monotonic=4\n"
    "[wrapper][2026-08-27 08:16:21,000] INFO: Return code: 255\n")


def _tree(root: pathlib.Path):
    """Every path under `root` with its bytes - the whole store, hashed
    by content rather than by mtime, so "nothing was written" is a real
    comparison and not a directory listing."""
    if not root.exists():
        return {}
    out = {}
    for path in sorted(root.rglob("*")):
        rel = str(path.relative_to(root))
        out[rel] = path.read_bytes() if path.is_file() else None
    return out


@pytest.fixture
def project(tmp_path):
    (tmp_path / "elements").mkdir()
    (tmp_path / "project.conf").write_text("name: ux324\nelement-path: elements\n")
    (tmp_path / "elements" / "all.bst").write_text("kind: manual\n")
    return tmp_path


def _snapshot(project, *argv, without_bst=True):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO)
    if without_bst:
        # A PATH with no `bst` on it - the machine the friction was
        # found on. `/usr/bin:/bin` rather than an empty PATH, because
        # the capture needs a shell and an empty one is a different bug.
        env["PATH"] = "/usr/bin:/bin"
    return subprocess.run([sys.executable, "-m", "bga.cli", "snapshot", *argv],
                          capture_output=True, text=True, cwd=str(project),
                          env=env, timeout=300)


class TestTheRefusal:

    def test_it_refuses_before_anything_exists(self, project):
        done = _snapshot(project, "--", "bst", "build", "all.bst")
        assert done.returncode == 2, (done.stdout, done.stderr)
        assert "Traceback (most recent call last)" not in done.stderr, (
            "the raw FileNotFoundError is back:\n" + done.stderr)
        assert "bst is not on PATH" in done.stderr
        assert "bga doctor" in done.stderr, (
            "the refusal does not point at the command that diagnoses the "
            "machine, which is the whole reason it is a sentence and not a "
            "traceback")

    def test_it_writes_nothing_at_all(self, project):
        """The clause with teeth. `UX-157`'s rule, extended to the phase
        before the build: interrupting before the build starts leaves
        nothing behind - and neither does refusing to start it."""
        store = project / run_store.STORE_DIRNAME
        before = _tree(store)
        assert before == {}, "the fixture project already has a store"

        done = _snapshot(project, "--", "bst", "build", "all.bst")
        assert done.returncode == 2

        after = _tree(store)
        assert after == before, (
            f"the refusal left {sorted(set(after) - set(before))} behind. "
            "Every one of those is debris that then has to be described, "
            "resolved and pruned - which is the second half of UX-324.")

    def test_a_machine_that_can_build_is_not_refused(self, monkeypatch):
        """The negative: this must not become a check that always fires."""
        monkeypatch.setattr(shutil, "which",
                            lambda name: "/usr/bin/bst" if name == "bst" else None)
        monkeypatch.setattr(subprocess, "run", lambda *a, **k: subprocess.
                            CompletedProcess(a, 0, stdout="2.1.0\n", stderr=""))
        assert why_the_build_cannot_start(["bst", "build", "all.bst"]) is None

    def test_a_non_bst_command_is_checked_too(self):
        refusal = why_the_build_cannot_start(["definitely-not-a-real-binary"])
        assert refusal and "is not on PATH" in refusal


class TestNeverStartedIsNotProducedNothing:

    @pytest.mark.parametrize("log,started", [
        (NEVER_STARTED, False),
        (INTERRUPTED, True),
        (RAN_AND_FAILED, True),
    ])
    def test_the_wrapper_log_says_which(self, tmp_path, log, started):
        (tmp_path / "build.log").write_text(log)
        assert build_ever_started(str(tmp_path)) is started

    def test_a_snapshot_with_no_log_answers_unknown_rather_than_guessing(
            self, tmp_path):
        """`None`, not `False`. A directory with no wrapped log reads
        exactly like a build that never ran, and claiming the latter is
        the same overreach as the sentence this replaced."""
        assert build_ever_started(str(tmp_path)) is None

    def test_an_unknown_snapshot_keeps_the_older_sentence(self, project):
        (project / ".bga" / "runs" / "20260827T081619Z").mkdir(parents=True)
        done = _snapshot(project, "--list")
        assert "produced no elements" in done.stdout, done.stdout
        assert "never started" not in done.stdout

    def test_the_listing_says_never_started(self, project):
        snapshot = project / ".bga" / "runs" / "20260827T081619Z"
        snapshot.mkdir(parents=True)
        (snapshot / "build.log").write_text(NEVER_STARTED)
        done = _snapshot(project, "--list")
        assert done.returncode == 0, done.stderr
        assert "the build never started" in done.stdout, done.stdout
        assert "produced no elements" not in done.stdout, (
            "a build that never launched is still described as one that ran "
            "and produced nothing - the two are different problems")

    def test_a_build_that_ran_and_produced_nothing_still_says_so(self, project):
        """The other side, so the fix is a distinction and not a rename."""
        snapshot = project / ".bga" / "runs" / "20260827T081619Z"
        snapshot.mkdir(parents=True)
        (snapshot / "build.log").write_text(RAN_AND_FAILED)
        done = _snapshot(project, "--list")
        assert "produced no elements" in done.stdout, done.stdout


class TestTheStoreAgreesWithItself:

    def _store(self, project, *, debris=True, healthy=True):
        runs = project / ".bga" / "runs"
        if debris:
            (runs / "20260827T081619Z").mkdir(parents=True)
            (runs / "20260827T081619Z" / "build.log").write_text(NEVER_STARTED)
        if healthy:
            good = runs / "20260827T090000Z"
            good.mkdir(parents=True)
            shutil.copytree(REPO / "tests/fixtures/macro_micro/run", good / "run")
        return runs

    def test_a_prefix_naming_debris_is_not_told_it_does_not_exist(self, project):
        """`--list` shows the directory; resolution used to answer "no
        snapshot starts with that", which is two commands disagreeing
        about what is on disk."""
        self._store(project)
        with pytest.raises(run_store.StoreError) as error:
            run_store.resolve_snapshot("@20260827T0816", start=str(project))
        message = str(error.value)
        assert "20260827T081619Z" in message, (
            f"the refusal does not name the snapshot `--list` shows: {message}")
        assert "no snapshot in" not in message, (
            f"still denying a directory that exists: {message}")
        assert "20260827T090000Z" in message, (
            "the refusal does not say which snapshot *would* resolve")

    def test_with_no_healthy_run_the_refusal_names_the_debris(self, project):
        self._store(project, healthy=False)
        with pytest.raises(run_store.StoreError) as error:
            run_store.resolve_snapshot("@20260827", start=str(project))
        assert "20260827T081619Z" in str(error.value)

    def test_a_prefix_matching_nothing_still_says_so(self, project):
        """The negative: the new branch must not swallow a real typo."""
        self._store(project)
        with pytest.raises(run_store.StoreError) as error:
            run_store.resolve_snapshot("@19990101", start=str(project))
        assert "no snapshot in" in str(error.value)
