"""UX-1134: with no plan, `PoolController` withholds its next `+` when the
running jobs' measured RSS per job, times one more plus one held free,
exceeds `MemAvailable` plus the RSS the build already holds - real FIFO, a
scripted `/proc` root and meminfo, real hook END lines.
"""

import json
import os

from tools import bst_native_build_tracer as tracer
from tools.jobserver import report_block

GB = 1 << 30
PAGE = os.sysconf("SC_PAGE_SIZE")
SANDBOX = 100


def _stat(root, pid, ppid, rss_bytes, comm="cc1"):
    os.makedirs(root / str(pid), exist_ok=True)
    (root / str(pid) / "stat").write_text(f"{pid} ({comm}) S {ppid} " + "0 " * 19 + f"{rss_bytes // PAGE} 0 0\n")


def _end(element, maxrss_bytes, pid=7):
    kb = maxrss_bytes // 1024
    return f"END pid={pid} ppid=1 ts=1.0 element={element} utime=0.1 stime=0.0 maxrss_kb={kb} cmd=cc1 -O2 x.c\n"


def _controller(tmp_path, *, live, finished, available, seed=4):
    """A 16-slot pool at `seed`, one running `giant.bst` sandbox whose one
    descendant holds `live` bytes, `finished` its END lines' peaks."""
    proc = tmp_path / "proc"
    _stat(proc, 1, 0, 8 * PAGE, "init")
    _stat(proc, SANDBOX, 1, 2 * PAGE, "bwrap")
    _stat(proc, SANDBOX + 1, SANDBOX, live)
    _stat(proc, 50, 1, 5 * GB, "unrelated")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(json.dumps({"element": "giant.bst", "pid": SANDBOX, "decision": "joined"}) + "\n")
    trace_log = tmp_path / "trace.log"
    trace_log.write_text("".join(_end("giant.bst", peak) for peak in finished))
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: 33554432 kB\nMemAvailable: {available // 1024} kB\n")
    scratch = tmp_path / "fifo"
    scratch.mkdir()
    _path, fd, _tokens = tracer.open_jobserver(16, str(scratch), seed=seed)
    ledger = str(tmp_path / "ledger.jsonl")
    paths = {"seed": seed, "trace_log": str(trace_log), "decisions": str(decisions)}
    paths.update({"meminfo": str(meminfo), "proc_root": str(proc), "memory": str(tmp_path / "no-psi")})
    return tracer.PoolController(fd, 16, capacity=16, ledger_path=ledger, psi_paths=paths), ledger


def _two_low_ticks(controller):
    controller.tick(busy_cores=2.0, psi_some10=0.0)
    return controller.tick(busy_cores=2.0, psi_some10=0.0)


def test_a_settled_giant_that_does_not_fit_gets_no_token(tmp_path):
    # 2 GB finished peak x (4 pool + 1 running + 1 + 1 reserve) = 14 GB > 8 GB avail + 0.5 GB live.
    controller, ledger = _controller(tmp_path, live=GB // 2, finished=[4 << 20, 2 * GB], available=8 * GB)
    row = _two_low_ticks(controller)
    assert row["action"] == "hold" and row["reason"].startswith("rss "), row
    assert controller.pool == 4
    block = report_block(
        {
            "jobserver": 16,
            "jobserver_seed": 4,
            "jobserver_auth": "fd",
            "jobserver_pool_mode": "dynamic",
            "capacity": 16,
            "jobserver_ledger_path": ledger,
            "jobserver_status_path": None,
            "plan_path": None,
            "broker_status_path": None,
            "element_kinds_present": True,
            "jobserver_decisions_path": None,
            "jobserver_wrappers": [],
        }
    )
    assert block["jobserver_pool"]["memory"]["rss_withheld"] == 1


def test_a_giant_that_fits_only_with_no_reserve_gets_no_token(tmp_path):
    # 2 GB x 6 = 12 GB <= 12 GB avail + 0.5 GB live, but x 7 with one held free = 14 GB does not.
    controller, _ledger = _controller(tmp_path, live=GB // 2, finished=[2 * GB], available=12 * GB)
    row = _two_low_ticks(controller)
    assert row["action"] == "hold" and row["reason"].startswith("rss "), row
    assert controller.pool == 4


def test_the_same_giant_gets_its_token_when_it_fits_with_its_reserve(tmp_path):
    # 14 GB <= 14 GB avail + 0.5 GB live.
    controller, _ledger = _controller(tmp_path, live=GB // 2, finished=[2 * GB], available=14 * GB)
    row = _two_low_ticks(controller)
    assert row["action"] == "add", row
    assert controller.pool == 5


def test_a_live_job_bigger_than_every_finished_one_holds(tmp_path):
    # Fits by any number (1 GB x 6 << 64 GB), but the 1 GB cc1's peak is still unknown.
    controller, _ledger = _controller(tmp_path, live=GB, finished=[4 << 20], available=64 * GB)
    row = _two_low_ticks(controller)
    assert row["action"] == "hold" and row["reason"].startswith("rss unsettled giant.bst"), row
    with open(tmp_path / "trace.log", "a", encoding="utf-8") as handle:
        handle.write(_end("giant.bst", 3 * GB // 2))
    assert controller.tick(busy_cores=2.0, psi_some10=0.0)["action"] == "add"
