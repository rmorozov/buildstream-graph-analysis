"""UX-1080: the BuildStream restarts `bga` makes around the build - the
doctor's `bst --version`, `bst artifact list-contents`, `bst show
--deps all`, hostinfo's `bst --version` - land in the same tail ledger
as `UX-1078`'s phases, as `calls` rows under the phase they ran inside.

A fake `bst` on PATH logs every invocation it received to a file; the
guard is that `tail.json`'s (or the ledger's) `calls` equal that log.
"""

import json
import os
import stat
import time

import pytest

from bga import progress


def _fake_bst(tmp_path, body):
    """A `bst` on PATH that appends its argv to `calls.jsonl` and runs
    `body` (shell) for its exit/stdout."""
    binaries = tmp_path / "path"
    binaries.mkdir()
    log = tmp_path / "calls.jsonl"
    stub = binaries / "bst"
    stub.write_text(
        "#!/bin/sh\n"
        f"python3 -c \"import json,sys; open({str(log)!r}, 'a').write("
        f"json.dumps(sys.argv[1:]) + chr(10))\" \"$@\"\n"
        f"{body}\n"
    )
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return binaries, log


def _logged(log):
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text().splitlines() if line]


@pytest.fixture(autouse=True)
def _isolated_ledger():
    progress.reset_ledger()
    yield
    progress.reset_ledger()


def test_check_bst_records_a_call(tmp_path, monkeypatch):
    from tools import bga_doctor

    binaries, log = _fake_bst(tmp_path, "echo '2.8.1'")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    with progress.timed("doctor"):
        check = bga_doctor.check_bst()

    assert check["status"] == bga_doctor.OK
    logged = _logged(log)
    assert logged == [["--version"]]
    [phase] = progress.ledger()["phases"]
    [call] = phase["calls"]
    assert call["verb"].endswith("bst --version")
    assert call["exit"] == 0
    assert isinstance(call["wall_us"], int) and call["wall_us"] >= 0


def test_hostinfo_times_bst_but_not_the_others(tmp_path, monkeypatch):
    from bga import hostinfo

    binaries, log = _fake_bst(tmp_path, "echo '2.8.1'")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    with progress.timed("hostinfo"):
        found = hostinfo._toolchain()

    assert found["bst"] == "2.8.1"
    logged = _logged(log)
    assert logged == [["--version"]]
    [phase] = progress.ledger()["phases"]
    verbs = [call["verb"] for call in phase["calls"]]
    assert len(verbs) == 1 and verbs[0].endswith("bst --version")


def test_list_contents_records_one_call_per_batch(tmp_path, monkeypatch):
    from tools.bst_native_build_tracer import read_artifact_contents

    binaries, log = _fake_bst(tmp_path, "echo 'app.bst:'; echo '/usr/include/app.h'")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    with progress.timed("Plane 2 report"):
        contents = read_artifact_contents(str(tmp_path), ["app.bst"])

    assert contents == {"app.bst": {"/usr/include/app.h"}}
    logged = _logged(log)
    assert logged == [["artifact", "list-contents", "app.bst"]]
    [phase] = progress.ledger()["phases"]
    [call] = phase["calls"]
    assert call["verb"] == "bst artifact list-contents app.bst"
    assert call["exit"] == 0


def test_run_bst_show_records_a_call_under_its_phase(tmp_path, monkeypatch):
    from tools.bst_show_to_graph import run_bst_show

    binaries, log = _fake_bst(tmp_path, "true")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    with progress.timed("run directory"):
        run_bst_show(str(tmp_path), ["app.bst"])

    logged = _logged(log)
    assert len(logged) == 1
    assert logged[0][:3] == ["show", "--deps", "all"] and logged[0][-1] == "app.bst"
    [phase] = progress.ledger()["phases"]
    [call] = phase["calls"]
    assert call["verb"].startswith("bst show --deps all --format ")
    assert call["verb"].endswith(" app.bst")
    assert call["exit"] == 0


def test_run_bst_show_timeout_kills_rather_than_hangs(tmp_path, monkeypatch):
    from tools.bst_show_to_graph import run_bst_show

    binaries, log = _fake_bst(tmp_path, "sleep 5")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    started = time.monotonic()
    with progress.timed("run directory"), pytest.raises(RuntimeError, match="timed out"):
        run_bst_show(str(tmp_path), ["app.bst"], timeout=0.2)
    elapsed = time.monotonic() - started
    assert elapsed < 4, f"the timeout did not bound the wait ({elapsed:.1f}s)"

    [phase] = progress.ledger()["phases"]
    [call] = phase["calls"]
    assert call["exit"] not in (0, None)  # killed, not a clean return


def test_a_call_with_no_phase_open_rides_the_next_one_that_closes(tmp_path, monkeypatch):
    """The general fallback: a `timed_call` made with nothing open (a
    caller that forgot a phase, or one this track missed) is buffered
    and claimed by the next `timed()` to close - never dropped. `bga
    snapshot`'s own doctor call no longer relies on this (below); it
    gets its own named phase."""
    from tools import bga_doctor

    binaries, log = _fake_bst(tmp_path, "echo '2.8.1'")
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    bga_doctor.check_bst()  # outside any `timed()` block
    assert progress.ledger()["phases"] == []
    with progress.timed("Plane 2 report"):
        pass
    [phase] = progress.ledger()["phases"]
    assert len(phase["calls"]) == 1


def test_the_doctor_call_sits_under_before_the_build(tmp_path, monkeypatch):
    """On a real `bga snapshot`, the doctor's `bst --version` is
    announced and recorded as its own phase - `before the build` - not
    credited to `Plane 2 report` (the first phase `take_snapshot` runs),
    which is what the drain-on-close fallback alone would do."""
    import stat as stat_module

    from tests.unit.test_the_tail_says_what_it_is_doing import tailed_project
    from tools.bga_snapshot import main

    root = tailed_project(tmp_path, monkeypatch)
    # `tailed_project`'s own stub `bst` only ever prints a version line;
    # this replaces it with one that also logs, so the call can be told
    # apart from the ones a real build/extraction would also make.
    log = tmp_path / "doctor_calls.jsonl"
    stub = tmp_path / "path" / "bst"  # tailed_project's stub, never a real bst
    assert stub.is_file()
    stub.write_text(
        "#!/bin/sh\n"
        f"python3 -c \"import json,sys; open({str(log)!r}, 'a').write("
        f"json.dumps(sys.argv[1:]) + chr(10))\" \"$@\"\n"
        "echo '2.8.1'\n"
    )
    stub.chmod(stub.stat().st_mode | stat_module.S_IEXEC)

    assert main(["--", "bst", "build", "all.bst"]) == 0

    from bga import run_store

    [snapshot] = run_store.list_snapshots(str(root))
    tail = run_store.read_tail(snapshot)
    phases = {row["name"]: row for row in tail["phases"]}
    assert "before the build" in phases
    before = [c["verb"] for c in phases["before the build"]["calls"]]
    assert any(v.endswith("bst --version") for v in before)
    for name, row in phases.items():
        if name == "before the build":
            continue
        assert not any(c["verb"].endswith("bst --version") for c in row["calls"]), (
            f"{name!r} carries the doctor's call too: {row['calls']}"
        )
