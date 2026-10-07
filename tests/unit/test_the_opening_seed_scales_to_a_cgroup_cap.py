"""UX-1339: under `auto` with no plan the opening seed scales by
`min(1, cgroup limit / MemTotal)`, and `PoolController.tick` reads one
unread token back when the width already out does not fit
(`MemoryGate.over`). Scripted cgroup trees, `/proc` and FIFOs throughout.
"""

import json
import os

from tools import bst_native_build_tracer as tracer
from tools.jobserver.memory import MemoryGate, opening_share
from tools.jobserver.pool import capped_width, opening_seed

GB = 1 << 30
PAGE = os.sysconf("SC_PAGE_SIZE")
SANDBOX = 100


def _host(tmp_path, limit, total=31 * GB, available=30 * GB, current=GB):
    """`(meminfo, cgroup_root, self_cgroup)`; `limit` `None` is no cgroup cap."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: {total // 1024} kB\nMemAvailable: {available // 1024} kB\n")
    membership = tmp_path / "self_cgroup"
    membership.write_text("0::/bga-cap\n")
    root = tmp_path / "cgroup"
    (root / "bga-cap").mkdir(parents=True)
    if limit is not None:
        (root / "bga-cap" / "memory.max").write_text(f"{limit}\n")
        (root / "bga-cap" / "memory.current").write_text(f"{current}\n")
    return str(meminfo), str(root), str(membership)


def _nested(tmp_path, parent, leaf):
    """`_host` with a limit on the parent and another on the leaf `bga-cap` beneath it."""
    paths = _host(tmp_path, None)
    root = tmp_path / "cgroup"
    for directory, limit in ((root, parent), (root / "bga-cap", leaf)):
        (directory / "memory.max").write_text(f"{limit}\n")
        (directory / "memory.current").write_text(f"{GB}\n")
    return paths


def test_the_tightest_cap_over_the_ancestors_sets_the_share(tmp_path):
    assert abs(opening_share(*_nested(tmp_path / "p", 20 * GB, "max")) - 20 / 31) < 1e-9
    assert abs(opening_share(*_nested(tmp_path / "q", 20 * GB, 28 * GB)) - 20 / 31) < 1e-9
    assert abs(opening_share(*_nested(tmp_path / "r", 28 * GB, 20 * GB)) - 20 / 31) < 1e-9


def test_a_20_of_31_gib_cap_opens_at_four_where_no_cap_opens_at_seven(tmp_path):
    capped = opening_share(*_host(tmp_path / "a", 20 * GB))
    assert abs(capped - 20 / 31) < 1e-9
    assert opening_seed(15, capped_width(8, capped), "auto", False) == 4  # floor(8 x 20/31) - 1
    uncapped = opening_share(*_host(tmp_path / "b", None))
    assert uncapped == 1.0 and opening_seed(15, capped_width(8, uncapped), "auto", False) == 7
    roomy = opening_share(*_host(tmp_path / "c", 64 * GB))
    assert roomy == 1.0 and opening_seed(15, capped_width(8, roomy), "auto", False) == 7


def test_typed_n_and_plan_ignore_the_share():
    width = capped_width(8, 20 / 31)
    assert opening_seed(15, width, "auto", False, typed=True) == 15
    assert opening_seed(15, width, "n", False) == 15
    assert opening_seed(15, width, "auto", True) == 15
    assert opening_seed(15, capped_width(None, 20 / 31), "auto", False) == 15
    assert opening_seed(2, width, "auto", False) == 2
    assert opening_seed(15, capped_width(1, 0.1), "auto", False) == 0


def _controller(tmp_path, readable):
    """A pool of 8 over a 20 GiB cap with a 2 GiB per-job peak, `readable` tokens left unread."""
    meminfo, root, membership = _host(tmp_path, 20 * GB)
    proc = tmp_path / "proc"
    for pid, ppid, rss in ((SANDBOX, 1, 2 * PAGE), (SANDBOX + 1, SANDBOX, GB // 2)):
        os.makedirs(proc / str(pid))
        (proc / str(pid) / "stat").write_text(f"{pid} (cc1) S {ppid} " + "0 " * 19 + f"{rss // PAGE} 0 0\n")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(json.dumps({"element": "giant.bst", "pid": SANDBOX}) + "\n")
    trace_log = tmp_path / "trace.log"
    trace_log.write_text(f"END pid=7 ppid=1 ts=1.0 element=giant.bst maxrss_kb={2 * GB // 1024} cmd=cc1\n")
    scratch = tmp_path / "fifo"
    scratch.mkdir()
    _path, fd, _tokens = tracer.open_jobserver(12, str(scratch), seed=8)
    paths = {"trace_log": str(trace_log), "decisions": str(decisions), "proc_root": str(proc), "seed": 8}
    paths.update({"meminfo": meminfo, "cgroup_root": root, "self_cgroup": membership})
    controller = tracer.PoolController(fd, 12, capacity=4, psi_paths=paths)
    for _ in range(8 - readable):
        os.read(fd, 1)
    return controller


def _tick(controller):
    return controller.tick(busy_cores=3, psi_some10=0.0, psi_mem10=0.0)


def test_an_over_width_tick_with_unread_tokens_reads_one_back(tmp_path):
    controller = _controller(tmp_path, readable=2)
    assert controller.memory_gate.over(8)
    row = _tick(controller)
    assert (row["action"], controller.pool, controller.memory_rss_withdraws) == ("withdraw", 7, 1)


def test_no_withdraw_when_it_fits_or_none_are_unread(tmp_path):
    fits = _controller(tmp_path / "fits", readable=2)
    fits.pool = 4
    assert not fits.memory_gate.over(4)
    assert _tick(fits)["action"] == "hold" and fits.pool == 4
    unread = _controller(tmp_path / "none", readable=0)
    assert unread.memory_gate.over(8)
    assert _tick(unread)["action"] == "hold" and unread.pool == 8


def test_over_counts_the_reserve_jobs_the_gate_keeps_free(tmp_path):
    # pool 7: 2 GiB x (7 + 1 live + 1 reserve) = 18 GiB fits 19.5; pool 8 -> 20 GiB does not.
    gate = _controller(tmp_path, readable=2).memory_gate
    assert isinstance(gate, MemoryGate)
    assert not gate.over(7) and gate.over(8)


def test_main_opens_at_four_and_names_the_cgroup(tmp_path, monkeypatch):
    from tests.unit.test_the_auto_seed_opens_at_bsts_own_max_jobs import _run_main

    seed, block = _run_main(tmp_path, monkeypatch, seed_typed=False, share=20 / 31)
    assert (seed, block["seed"], block["seed_bound"]) == (4, 4, "cgroup")


def test_an_add_tick_is_not_relabelled_a_withdraw(tmp_path):
    controller = _controller(tmp_path, readable=0)
    controller.pool = 4
    controller.memory_gate.withhold = lambda pool: None
    controller.memory_gate.over = lambda pool: True
    _tick_low = lambda: controller.tick(busy_cores=0, psi_some10=0.0, psi_mem10=0.0)
    _tick_low()
    row = _tick_low()
    assert (row["action"], controller.pool, controller.moves, controller.memory_rss_withdraws) == ("add", 5, 1, 0)
