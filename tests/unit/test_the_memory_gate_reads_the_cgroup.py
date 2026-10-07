"""UX-1282: the jobserver's memory gate reads the memory the build's
cgroup can use - the lower of `MemAvailable` and the tightest limit minus
usage over its own cgroup and every ancestor - over scripted
`/proc/meminfo`, `/proc/self/cgroup` and `/sys/fs/cgroup`. The advice's
half is `test_memory_joins_the_sweep.py`.
"""

import json
import os

from tools import bst_native_build_tracer as tracer
from tools.jobserver.memory import MemoryGate, read_build_memory, read_cgroup_limit_bytes
from tools.jobserver.pool import read_mem_available_bytes

GB = 1 << 30
PAGE = os.sysconf("SC_PAGE_SIZE")
SANDBOX = 100
HOST_AVAILABLE = 60 * GB


def _host(tmp_path, self_cgroup, files=None, available=HOST_AVAILABLE):
    """`(meminfo, cgroup_root, self_cgroup)` paths; `files` is `{relative path: text}` under the root."""
    meminfo = tmp_path / "meminfo"
    meminfo.write_text(f"MemTotal: {64 * GB // 1024} kB\nMemAvailable: {available // 1024} kB\n")
    membership = tmp_path / "self_cgroup"
    membership.write_text(self_cgroup)
    root = tmp_path / "cgroup"
    root.mkdir()
    for relative, text in (files or {}).items():
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        (root / relative).write_text(text)
    return str(meminfo), str(root), str(membership)


def _v2(tmp_path, leaf_max, parent_max, current=GB):
    return _host(
        tmp_path,
        "0::/kubepods/pod1/build\n",
        {
            "kubepods/pod1/memory.max": f"{parent_max}\n",
            "kubepods/pod1/memory.current": f"{current}\n",
            "kubepods/pod1/build/memory.max": f"{leaf_max}\n",
            "kubepods/pod1/build/memory.current": f"{current}\n",
        },
    )


def test_no_cgroup_reads_mem_available(tmp_path):
    paths = _host(tmp_path, "0::/\n")
    assert read_build_memory(*paths) == (HOST_AVAILABLE, "meminfo")
    assert read_cgroup_limit_bytes(*paths[1:]) is None


def test_a_v2_max_limit_reads_mem_available(tmp_path):
    paths = _v2(tmp_path, "max", "max")
    assert read_build_memory(*paths) == (HOST_AVAILABLE, "meminfo")


def test_a_v2_leaf_limit_below_the_host_binds(tmp_path):
    paths = _v2(tmp_path, 20 * GB, "max", current=5 * GB)
    assert read_build_memory(*paths) == (15 * GB, "cgroup")
    assert read_cgroup_limit_bytes(*paths[1:]) == 20 * GB


def test_a_tighter_v2_parent_binds_over_the_leaf(tmp_path):
    paths = _v2(tmp_path, "max", 8 * GB, current=3 * GB)
    assert read_build_memory(*paths) == (5 * GB, "cgroup")
    assert read_cgroup_limit_bytes(*paths[1:]) == 8 * GB


def test_reclaimable_page_cache_is_headroom(tmp_path):
    # usage 7.5 of 8 GB, 6 GB of it inactive_file: the working set is 1.5 GB, headroom 6.5 GB.
    meminfo, root, membership = _v2(tmp_path, 8 * GB, "max", current=15 * GB // 2)
    stat = os.path.join(root, "kubepods/pod1/build/memory.stat")
    with open(stat, "w", encoding="utf-8") as handle:
        handle.write(f"anon {GB}\nactive_file {GB // 2}\ninactive_file {6 * GB}\n")
    assert read_build_memory(meminfo, root, membership) == (13 * GB // 2, "cgroup")


def test_a_v1_limit_reads_limit_minus_usage(tmp_path):
    files = {
        "memory/docker/abc/memory.limit_in_bytes": f"{12 * GB}\n",
        "memory/docker/abc/memory.usage_in_bytes": f"{5 * GB}\n",
        "memory/docker/abc/memory.stat": f"cache {3 * GB}\ninactive_file {9 * GB}\ntotal_inactive_file {3 * GB}\n",
        "memory/docker/memory.limit_in_bytes": "9223372036854771712\n",
        "memory/docker/memory.usage_in_bytes": f"{4 * GB}\n",
    }
    paths = _host(tmp_path, "5:cpu,cpuacct:/docker/abc\n4:memory:/docker/abc\n0::/\n", files)
    assert read_build_memory(*paths) == (10 * GB, "cgroup")
    assert read_cgroup_limit_bytes(*paths[1:]) == 12 * GB


def _gate(tmp_path, mem_available):
    proc = tmp_path / "proc"
    for pid, ppid, rss in ((SANDBOX, 1, 2 * PAGE), (SANDBOX + 1, SANDBOX, GB // 2)):
        os.makedirs(proc / str(pid))
        (proc / str(pid) / "stat").write_text(f"{pid} (cc1) S {ppid} " + "0 " * 19 + f"{rss // PAGE} 0 0\n")
    decisions = tmp_path / "decisions.jsonl"
    decisions.write_text(json.dumps({"element": "giant.bst", "pid": SANDBOX}) + "\n")
    trace_log = tmp_path / "trace.log"
    trace_log.write_text(f"END pid=7 ppid=1 ts=1.0 element=giant.bst maxrss_kb={2 * GB // 1024} cmd=cc1\n")
    return MemoryGate(str(trace_log), str(decisions), mem_available, str(proc))


def test_the_gate_holds_under_a_cap_where_meminfo_alone_grants(tmp_path):
    # 2 GB per job x a handful of jobs fits 60 GB available, not 1 GB of cgroup headroom.
    meminfo, root, membership = _v2(tmp_path, "max", 4 * GB, current=3 * GB)
    assert _gate(tmp_path / "host", lambda: read_mem_available_bytes(meminfo)).withhold(0) is None
    reason = _gate(tmp_path / "capped", lambda: read_build_memory(meminfo, root, membership)[0]).withhold(0)
    assert (reason or "").startswith("rss "), reason


def test_the_pool_controller_and_the_broker_read_the_cgroup(tmp_path):
    meminfo, root, membership = _v2(tmp_path, "max", 4 * GB, current=3 * GB)
    scratch = tmp_path / "fifo"
    scratch.mkdir()
    _path, fd, _tokens = tracer.open_jobserver(4, str(scratch))
    paths = {"trace_log": "t", "decisions": "d", "meminfo": meminfo, "cgroup_root": root, "self_cgroup": membership}
    controller = tracer.PoolController(fd, 4, capacity=4, psi_paths=paths)
    assert controller.memory_gate.mem_available() == GB
    proxies_dir = str(tmp_path / "proxies")
    proxy_fds = tracer.create_jobserver_proxies(proxies_dir, {"a": "make"})
    ledger = tmp_path / "ledger.jsonl"
    broker_scratch = {"proxies_dir": proxies_dir, "peak_rss": {"a": GB}, "meminfo_path": meminfo}
    broker_scratch.update({"cgroup_root": root, "self_cgroup": membership})
    broker = tracer.Broker(fd, proxy_fds, {"a": 10}, ledger_path=str(ledger), scratch=broker_scratch)
    broker.note_running("a", max_jobs=3)
    broker.tick()
    rows = [json.loads(line) for line in ledger.read_text().splitlines() if '"memory_withheld"' in line]
    assert rows and rows[0]["mem_available"] == GB, rows
