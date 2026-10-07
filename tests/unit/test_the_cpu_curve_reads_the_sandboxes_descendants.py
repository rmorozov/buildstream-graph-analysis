"""UX-1314: each sandbox's CPU curve is its host descendants' utime+stime.

The trace log's pids are namespace-local: every `bwrap --unshare-pid`
sandbox starts at 2 (`spine.c:443`), and host `/proc/2` is `kthreadd`.
The root is the decision row's host `pid`; the scripted `/proc` below
has both sandboxes' trace pid at 2 and a kthreadd stub there.
"""

import json
import shutil

import pytest

from tools.bst_native_build_tracer import (
    _TICKS_PER_S,
    ElementCpuSampler,
    element_cpu_series,
    read_element_cpu_samples,
)

#: `{pid: (ppid, comm)}` - two sandboxes whose trace logs both say pid 2.
TREE = {
    1: (0, "init"),
    2: (0, "kthreadd"),
    4100: (1, "bwrap"),
    4101: (4100, "bwrap"),
    4102: (4101, "make"),
    4103: (4102, "cc1"),
    4200: (1, "bwrap"),
    4201: (4200, "bwrap"),
    4202: (4201, "cc1plus"),
    4300: (1, "unrelated"),
}
#: Cumulative utime+stime jiffies per tick.
TICKS = [
    {1: 5, 2: 0, 4100: 1, 4101: 1, 4102: 10, 4103: 100, 4200: 1, 4201: 1, 4202: 50, 4300: 7},
    {1: 5, 2: 0, 4100: 1, 4101: 1, 4102: 30, 4103: 500, 4200: 1, 4201: 1, 4202: 450, 4300: 900},
]
ROOTS = {"a.bst": 4100, "b.bst": 4200}
TREES = {"a.bst": (4100, 4101, 4102, 4103), "b.bst": (4200, 4201, 4202)}
INTERVAL = 2.0


def _script(proc, jiffies, children_files, gone=()):
    shutil.rmtree(proc, ignore_errors=True)
    for pid, (ppid, comm) in TREE.items():
        if pid in gone:
            continue
        task = proc / str(pid) / "task" / str(pid)
        task.mkdir(parents=True)
        utime, stime = jiffies[pid] - jiffies[pid] // 3, jiffies[pid] // 3
        fields = ["S", ppid, pid, pid, 0, -1, 0, 0, 0, 0, 0, utime, stime] + [0] * 10
        (proc / str(pid) / "stat").write_text(f"{pid} ({comm}) " + " ".join(map(str, fields)) + "\n")
        if children_files:
            kids = [str(kid) for kid, (parent, _) in TREE.items() if parent == pid and kid not in gone]
            (task / "children").write_text("".join(kid + " " for kid in kids))


def _sample(tmp_path, roots, ticks, children_files=True):
    proc, decisions, out = tmp_path / "proc", tmp_path / "decisions.jsonl", tmp_path / "samples.jsonl"
    decisions.write_text(
        "".join(json.dumps({"element": e, "pid": p, "decision": "joined"}) + "\n" for e, p in roots.items())
    )
    sampler = ElementCpuSampler(str(out), str(decisions), interval_s=INTERVAL, proc_root=str(proc))
    sampler._handle = open(out, "w", encoding="utf-8")
    for index, (jiffies, gone) in enumerate(ticks):
        _script(proc, jiffies, children_files, gone)
        sampler.tick(index * INTERVAL)
    sampler._handle.close()
    return element_cpu_series(read_element_cpu_samples(str(out))), sampler


@pytest.mark.parametrize("children_files", [True, False], ids=["task-children", "ppid-scan"])
def test_two_sandboxes_both_at_pid_2_get_their_own_descendants_series(tmp_path, children_files):
    series, _ = _sample(tmp_path, ROOTS, [(TICKS[0], ()), (TICKS[1], ())], children_files)

    assert sorted(series) == ["a.bst", "b.bst"]
    for element, tree in TREES.items():
        delta = sum(TICKS[1][pid] - TICKS[0][pid] for pid in tree)
        assert series[element] == [[int(INTERVAL * 1e6), round(delta / _TICKS_PER_S / INTERVAL, 3)]]
    assert series["a.bst"] != series["b.bst"]


def test_a_descendant_that_exits_ends_its_own_series_not_the_elements(tmp_path):
    """Per-pid rows: cc1's time leaving the tree is not a negative rate."""
    third = {**TICKS[1], 4102: 130}
    series, _ = _sample(tmp_path, {"a.bst": 4100}, [(TICKS[0], ()), (TICKS[1], ()), (third, {4103})])

    rates = [point[1] for point in series["a.bst"]]
    assert rates == [round(420 / _TICKS_PER_S / INTERVAL, 3), round(100 / _TICKS_PER_S / INTERVAL, 3)]


def test_a_sandbox_whose_root_exits_is_dropped_and_the_other_kept(tmp_path):
    third = {**TICKS[1], 4103: 700}
    series, sampler = _sample(tmp_path, ROOTS, [(TICKS[0], ()), (TICKS[1], ()), (third, {4200, 4201, 4202})])

    assert sampler._live == {4100: "a.bst"}
    assert len(series["b.bst"]) == 1
    assert len(series["a.bst"]) == 2
