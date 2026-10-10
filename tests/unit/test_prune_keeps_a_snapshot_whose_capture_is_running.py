"""UX-1309: `--prune` spares a snapshot whose capture is still running.

`take_snapshot` writes `capture.pid` while its capture runs and removes it
after; `_prune` keeps a snapshot whose marker names a live pid. The tracer
is stubbed, as in `test_snapshot.py`, because what is under test is the
marker and the prune filter, not the build.
"""

import os
import subprocess
import sys
from datetime import datetime, timezone

import pytest

from bga import run_store
from tools import bga_snapshot
from tools.bga_snapshot import CAPTURE_PID_NAME, _prune, take_snapshot


@pytest.fixture
def project(tmp_path):
    root = tmp_path / "proj"
    root.mkdir()
    (root / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    return str(root)


def _snapshot(project, day):
    return run_store.new_snapshot_dir(project, now=datetime(2026, 1, day, tzinfo=timezone.utc))


def _dead_pid():
    proc = subprocess.Popen([sys.executable, "-c", "pass"])
    proc.wait()
    return proc.pid


class TestPruneSparesALiveWriter:
    def test_a_live_marker_is_kept_and_husks_are_still_deleted(self, project):
        live = _snapshot(project, 1)
        dead = _snapshot(project, 2)
        bare = _snapshot(project, 3)
        with_run = _snapshot(project, 4)
        os.makedirs(os.path.join(with_run, "run"))
        with open(os.path.join(live, CAPTURE_PID_NAME), "w") as handle:
            handle.write(str(os.getpid()))
        with open(os.path.join(dead, CAPTURE_PID_NAME), "w") as handle:
            handle.write(str(_dead_pid()))

        _prune(project, keep=0, older_than=None, dry_run=False)

        survivors = set(run_store.list_snapshots(project))
        # `with_run` is the only run-bearing snapshot, so `@last` protects it
        # (`_protected`); the claim is about the two run-less ones.
        assert live in survivors, "a capture still writing must not be pruned"
        assert with_run in survivors
        assert dead not in survivors, "a dead writer's husk is still a husk"
        assert bare not in survivors, "a marker-less husk is still a husk"


class TestTheWriterMarksItsSnapshot:
    def test_the_marker_names_this_process_while_the_capture_runs(self, project, monkeypatch):
        import tools.bst_native_build_tracer as tracer

        seen = {}

        def fake_capture(argv):
            snapshot = os.path.dirname(argv[argv.index("--run-dir") + 1])
            with open(os.path.join(snapshot, CAPTURE_PID_NAME)) as handle:
                seen["pid"] = handle.read()
            seen["snapshot"] = snapshot
            return 0

        monkeypatch.setattr(tracer, "main", fake_capture)
        take_snapshot(project, ["bst", "build", "all.bst"], {"trace_opens": False, "trace_spine": "off"})

        assert seen["pid"] == str(os.getpid())
        assert not os.path.exists(os.path.join(seen["snapshot"], CAPTURE_PID_NAME))

    def test_the_marker_is_removed_even_when_the_capture_raises(self, project, monkeypatch):
        import tools.bst_native_build_tracer as tracer

        seen = {}

        def failing_capture(argv):
            seen["snapshot"] = os.path.dirname(argv[argv.index("--run-dir") + 1])
            raise RuntimeError("the build died")

        monkeypatch.setattr(tracer, "main", failing_capture)
        with pytest.raises(RuntimeError):
            take_snapshot(project, ["bst", "build", "all.bst"], {"trace_opens": False, "trace_spine": "off"})

        assert not os.path.exists(os.path.join(seen["snapshot"], CAPTURE_PID_NAME))


def test_capture_alive_reads_a_missing_or_garbled_marker_as_a_husk(project):
    snapshot = _snapshot(project, 9)
    assert bga_snapshot._capture_alive(snapshot) is False
    with open(os.path.join(snapshot, CAPTURE_PID_NAME), "w") as handle:
        handle.write("not a pid")
    assert bga_snapshot._capture_alive(snapshot) is False


def _weighted(project, day, size):
    snapshot = _snapshot(project, day)
    os.makedirs(os.path.join(snapshot, "run"))
    with open(os.path.join(snapshot, "payload"), "wb") as handle:
        handle.write(b"x" * size)
    return snapshot


def _store_with_a_live_oldest(project):
    live = _weighted(project, 1, 4000)
    older = _weighted(project, 2, 4000)
    _weighted(project, 3, 10)
    _weighted(project, 4, 10)
    with open(os.path.join(live, CAPTURE_PID_NAME), "w") as handle:
        handle.write(str(os.getpid()))
    return live, older


def test_max_store_counts_a_live_capture_and_deletes_the_unprotected_one_instead(project):
    live, older = _store_with_a_live_oldest(project)

    _prune(project, keep=None, older_than=None, dry_run=False, max_store=5000)

    survivors = set(run_store.list_snapshots(project))
    assert live in survivors, "a capture still writing must not be pruned"
    assert older not in survivors, "the live capture's bytes are not freed, so the next one must go"


def test_max_store_leftover_message_names_the_live_capture(project, capsys):
    _store_with_a_live_oldest(project)

    _prune(project, keep=None, older_than=None, dry_run=False, max_store=3000)

    out = capsys.readouterr().out
    assert "still being captured" in out, "what is left is not all @last/@prev"


class TestCaptureAliveBranches:
    def _marker(self, project, text):
        snapshot = _snapshot(project, 8)
        with open(os.path.join(snapshot, CAPTURE_PID_NAME), "w") as handle:
            handle.write(text)
        return snapshot

    def test_permission_denied_means_the_pid_exists(self, project, monkeypatch):
        snapshot = self._marker(project, "12345")

        def denied(pid, sig):
            raise PermissionError

        monkeypatch.setattr(os, "kill", denied)
        assert bga_snapshot._capture_alive(snapshot) is True

    def test_a_non_positive_pid_is_not_a_writer(self, project, monkeypatch):
        calls = []
        monkeypatch.setattr(os, "kill", lambda pid, sig: calls.append(pid))
        for text in ("0", "-1"):
            assert bga_snapshot._capture_alive(self._marker(project, text)) is False
        assert calls == [], "os.kill(0 or -1, 0) would signal a process group"

    def test_an_unreadable_marker_is_a_husk(self, project):
        snapshot = _snapshot(project, 7)
        os.makedirs(os.path.join(snapshot, CAPTURE_PID_NAME))  # open() raises IsADirectoryError
        assert bga_snapshot._capture_alive(snapshot) is False


def _live_without_run(project, day, size):
    snapshot = _snapshot(project, day)  # no run/: a capture before extraction
    with open(os.path.join(snapshot, "payload"), "wb") as handle:
        handle.write(b"x" * size)
    with open(os.path.join(snapshot, CAPTURE_PID_NAME), "w") as handle:
        handle.write(str(os.getpid()))
    return snapshot


def test_max_store_counts_a_live_capture_that_has_no_run_yet(project):
    live = _live_without_run(project, 1, 4000)
    older = _weighted(project, 2, 4000)
    _weighted(project, 3, 10)
    _weighted(project, 4, 10)

    _prune(project, keep=None, older_than=None, dry_run=False, max_store=5000)

    survivors = set(run_store.list_snapshots(project))
    assert live in survivors
    assert older not in survivors, "the live capture's bytes count, so the unprotected run must go"


def test_nothing_to_prune_names_a_live_capture_as_the_excess(project, capsys):
    _live_without_run(project, 1, 4000)

    _prune(project, keep=None, older_than=None, dry_run=False, max_store=1000)

    out = capsys.readouterr().out
    assert "Nothing to prune" in out
    assert "still being captured" in out


def test_an_overflowing_pid_is_a_husk_not_a_crash(project):
    snapshot = _snapshot(project, 6)
    with open(os.path.join(snapshot, CAPTURE_PID_NAME), "w") as handle:
        handle.write("99999999999999999999")
    assert bga_snapshot._capture_alive(snapshot) is False
    _prune(project, keep=0, older_than=None, dry_run=False)
    assert snapshot not in run_store.list_snapshots(project)


def test_removing_an_absent_marker_is_not_an_error(project):
    bga_snapshot._remove_capture_pid(_snapshot(project, 5))


def test_keep_zero_spares_a_live_capture_that_already_has_a_run(project):
    live = _weighted(project, 1, 10)
    _weighted(project, 2, 10)
    _weighted(project, 3, 10)
    with open(os.path.join(live, CAPTURE_PID_NAME), "w") as handle:
        handle.write(str(os.getpid()))

    _prune(project, keep=0, older_than=None, dry_run=False)

    assert live in run_store.list_snapshots(project)


def test_keep_counts_runs_only_so_a_live_run_less_capture_costs_no_run_its_slot(project):
    oldest = _weighted(project, 1, 10)
    older = _weighted(project, 2, 10)
    newer = _weighted(project, 3, 10)
    newest = _weighted(project, 4, 10)
    live = _live_without_run(project, 5, 10)

    _prune(project, keep=3, older_than=None, dry_run=False)

    survivors = set(run_store.list_snapshots(project))
    assert oldest not in survivors
    assert {older, newer, newest, live} <= survivors, "keep=3 deletes exactly one of four runs"


def test_nothing_to_prune_does_not_call_a_live_capture_referred_to(project, capsys):
    _weighted(project, 1, 10)
    _live_without_run(project, 2, 10)

    _prune(project, keep=1, older_than=None, dry_run=False)

    out = capsys.readouterr().out
    assert "Nothing to prune: 2 snapshots, 1 of them still referred to by @last/@prev." in out
