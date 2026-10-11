"""UX-1284: a link that peaks at 4x the compiles the gate settled on is
held the moment it is live - eight finished cc1 END lines at c, one lto1
at 4c under make/gcc/lto-wrapper in the sandbox, memory to spare: the
next `+` is withheld `rss unsettled`. Real FIFO, scripted `/proc` and
meminfo, as test_the_pool_withholds_for_measured_rss_with_no_plan.py.
"""

import json
import os

from tools import bst_native_build_tracer as tracer

MB = 1 << 20
GB = 1 << 30
PAGE = os.sysconf("SC_PAGE_SIZE")
COMPILE = 300 * MB
SANDBOX = 100


def _stat(root, pid, ppid, rss_bytes, comm):
    os.makedirs(root / str(pid), exist_ok=True)
    (root / str(pid) / "stat").write_text(f"{pid} ({comm}) S {ppid} " + "0 " * 19 + f"{rss_bytes // PAGE} 0 0\n")


def _end(pid, maxrss_bytes, binary):
    return (
        f"END pid={pid} ppid={SANDBOX + 1} ts={pid}.0 element=giant.bst inv=none utime=1.0 stime=0.1 "
        f"maxrss_kb={maxrss_bytes // 1024} cmd=/nix/store/x-gcc/libexec/gcc/{binary} -O0 unit.c\n"
    )


def _controller(tmp_path, link_rss):
    """A 16-slot pool at 4 whose giant finished eight compiles at
    `COMPILE` and now runs its link: lto1 at `link_rss`, 64 GB free."""
    proc = tmp_path / "proc"
    _stat(proc, 1, 0, 8 * PAGE, "init")
    _stat(proc, SANDBOX, 1, 2 * PAGE, "bwrap")
    chain = [(SANDBOX + 1, "make"), (SANDBOX + 2, "gcc"), (SANDBOX + 3, "lto-wrapper")]
    for pid, comm in chain:
        _stat(proc, pid, pid - 1, 4 * MB, comm)
    _stat(proc, SANDBOX + 4, SANDBOX + 3, link_rss, "lto1")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(json.dumps({"element": "giant.bst", "pid": SANDBOX, "decision": "joined"}) + "\n")
    trace_log = tmp_path / "trace.log"
    trace_log.write_text("".join(_end(200 + n, COMPILE - n * MB, "cc1") for n in range(8)))
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: 67108864 kB\nMemAvailable: {64 * GB // 1024} kB\n")
    scratch = tmp_path / "fifo"
    scratch.mkdir()
    _path, fd, _tokens = tracer.open_jobserver(16, str(scratch), seed=4)
    os.read(fd, 4)
    ledger = str(tmp_path / "ledger.jsonl")
    paths = {"seed": 4, "trace_log": str(trace_log), "decisions": str(decisions)}
    paths.update({"meminfo": str(meminfo), "proc_root": str(proc), "memory": str(tmp_path / "no-psi")})
    return tracer.PoolController(fd, 16, capacity=16, ledger_path=ledger, psi_paths=paths), ledger


def _two_low_ticks(controller):
    controller.tick(busy_cores=2.0, psi_some10=0.0)
    return controller.tick(busy_cores=2.0, psi_some10=0.0)


def test_a_link_at_four_compiles_is_held_unsettled(tmp_path):
    # 4c x (4 pool + 1 running + 1 + 1 reserve) = 8.4 GB fits 64 GB: only the unsettled hold stops it.
    controller, ledger = _controller(tmp_path, 4 * COMPILE)
    row = _two_low_ticks(controller)
    assert row["action"] == "hold", row
    assert row["reason"] == f"rss unsettled giant.bst live {4 * COMPILE}>finished {COMPILE}", row
    assert controller.pool == 4
    with open(ledger, encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle]
    assert rows[-1]["reason"].startswith("rss unsettled giant.bst"), rows[-1]


def test_the_same_link_at_one_compile_gets_its_token(tmp_path):
    # The control: the shape alone, not the tree or the meminfo, is what holds.
    controller, _ledger = _controller(tmp_path, COMPILE)
    row = _two_low_ticks(controller)
    assert row["action"] == "add", row
    assert controller.pool == 5
