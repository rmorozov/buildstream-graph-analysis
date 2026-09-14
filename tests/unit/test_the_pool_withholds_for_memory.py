"""UX-850: memory is a second resource the pool reads. `Broker` withholds
a proxy's next token when the element's own planned peak RSS (from
`--plan`) times the tokens it would then hold exceeds `MemAvailable`;
`PoolController` withdraws a token when `/proc/pressure/memory`'s `some
avg10` is over `JOBSERVER_POOL_MEMORY_PSI_BOUND`, the same way the CPU
bound already does. Real FIFOs and real (fake, scripted) files
throughout - never a mock of either reader.
"""
import json
import os

from tools import bst_native_build_tracer as tracer

PEAK = 1024 * 1024  # 1 MiB - chosen so the byte/kB boundary lands exact


def _meminfo(tmp_path, kb, name="meminfo"):
    path = tmp_path / name
    path.write_text(f"MemTotal:       16000000 kB\nMemAvailable:   {kb} kB\n")
    return str(path)


def _broker(tmp_path, elements, plan, peak_rss=None, meminfo_path=None, ceiling=8):
    global_scratch = str(tmp_path / "global")
    os.makedirs(global_scratch, exist_ok=True)
    _path, global_fd, _tokens = tracer.open_jobserver(ceiling, global_scratch)
    proxies_dir = str(tmp_path / "proxies")
    proxy_fds = tracer.create_jobserver_proxies(proxies_dir, dict.fromkeys(elements, "make"))
    ledger = str(tmp_path / "ledger.jsonl")
    scratch = {"proxies_dir": proxies_dir}
    if peak_rss is not None:
        scratch["peak_rss"] = peak_rss
    if meminfo_path is not None:
        scratch["meminfo_path"] = meminfo_path
    broker = tracer.Broker(global_fd, proxy_fds, plan, ledger_path=ledger, scratch=scratch)
    return broker, global_fd, proxy_fds, ledger


def _readable(fd) -> int:
    held = 0
    while True:
        try:
            if not os.read(fd, 1):
                break
        except BlockingIOError:
            break
        held += 1
    if held:
        os.write(fd, b"+" * held)
    return held


def _rows(ledger):
    with open(ledger, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class TestTheBrokerWithholdsByPlannedPeak:
    def test_below_the_bound_withholds(self, tmp_path):
        # held_after = 1 (implicit) + 0 (granted) + 2 (room, -j3) = 3
        # threshold = PEAK * 3 = 3072 kB exactly; 3000 kB is short.
        meminfo = _meminfo(tmp_path, 3000)
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 10}, peak_rss={"a": PEAK}, meminfo_path=meminfo)
        broker.note_running("a", max_jobs=3)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 0, "3000 kB is short of the 3072 kB threshold"
        rows = [row for row in _rows(ledger) if row["event"] == "memory_withheld"]
        assert rows == [{"event": "memory_withheld", "element": "a", "tokens": 2,
                         "mem_available": 3000 * 1024, "peak_rss": PEAK,
                         "t": rows[0]["t"]}]
        assert broker.memory_withheld == 1

    def test_above_the_bound_grants(self, tmp_path):
        meminfo = _meminfo(tmp_path, 3200)  # 3,276,800 B >= PEAK * 3
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 10}, peak_rss={"a": PEAK}, meminfo_path=meminfo)
        broker.note_running("a", max_jobs=3)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 2, "3200 kB clears the 3072 kB threshold"
        assert not [row for row in _rows(ledger) if row["event"] == "memory_withheld"]

    def test_a_plan_without_peak_rss_withholds_nothing(self, tmp_path):
        meminfo = _meminfo(tmp_path, 1)  # a starved host - would withhold if read at all
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 10}, peak_rss={}, meminfo_path=meminfo)
        broker.note_running("a", max_jobs=3)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 2, "no peak_rss entry - the gate is a no-op"
        assert not [row for row in _rows(ledger) if row["event"] == "memory_withheld"]

    def test_a_peak_that_alone_exceeds_the_machine_grants_nothing(self, tmp_path):
        meminfo = _meminfo(tmp_path, 16_000_000)  # generous - still not enough
        huge_peak = 16_000_000 * 1024 * 1024  # far past any MemAvailable above
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 10}, peak_rss={"a": huge_peak}, meminfo_path=meminfo)
        broker.note_running("a", max_jobs=3)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 0, "runs on its implicit token only"
        rows = [row for row in _rows(ledger) if row["event"] == "memory_withheld"]
        assert len(rows) == 1, "one row for the one tick this test drives"

    def test_memory_returning_grants_a_previously_withheld_element(self, tmp_path):
        meminfo = tmp_path / "meminfo"
        meminfo.write_text("MemTotal:       16000000 kB\nMemAvailable:   3000 kB\n")
        broker, global_fd, proxy_fds, _ledger = _broker(
            tmp_path, ["a"], {"a": 10}, peak_rss={"a": PEAK}, meminfo_path=str(meminfo))
        broker.note_running("a", max_jobs=3)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 0, "withheld this tick"
        assert _readable(global_fd) == 7, "the seeded pool, untouched"
        meminfo.write_text("MemTotal:       16000000 kB\nMemAvailable:   3200 kB\n")
        broker.tick()
        assert _readable(proxy_fds["a"]) == 2, "reconsidered and granted on the next tick"


class TestThePoolReadsMemoryPSI:
    def _controller(self, tmp_path, psi_memory_path=None, ceiling=4, capacity=4):
        path, fd, tokens = tracer.open_jobserver(ceiling, str(tmp_path))
        assert tokens == ceiling - 1
        ledger = str(tmp_path / "ledger.jsonl")
        pc = tracer.PoolController(
            fd, ceiling, capacity=capacity, ledger_path=ledger,
            psi_paths={"cpu": str(tmp_path / "no-cpu-psi"),
                      "memory": psi_memory_path or str(tmp_path / "no-mem-psi")})
        return pc, path, fd, ledger

    def test_absent_does_nothing(self, tmp_path):
        pc, path, fd, _ledger = self._controller(tmp_path)
        assert not pc.psi_memory_present
        row = pc.tick(busy_cores=0.5)
        assert row["action"] == "hold"
        tracer.close_jobserver(path, fd)

    def test_present_under_the_bound_does_nothing(self, tmp_path):
        psi_mem = tmp_path / "pressure-memory"
        psi_mem.write_text("some avg10=4.00 avg60=2.00 avg300=1.00 total=1\n"
                           "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")
        pc, path, fd, _ledger = self._controller(tmp_path, psi_memory_path=str(psi_mem))
        assert pc.psi_memory_present
        row = pc.tick(busy_cores=0.5)
        assert row["action"] == "hold" and row["psi_mem10"] == 4.0
        tracer.close_jobserver(path, fd)

    def test_present_over_the_bound_withdraws(self, tmp_path):
        psi_mem = tmp_path / "pressure-memory"
        psi_mem.write_text("some avg10=22.50 avg60=10.00 avg300=5.00 total=1\n"
                           "full avg10=0.00 avg60=0.00 avg300=0.00 total=0\n")
        pc, path, fd, ledger = self._controller(tmp_path, psi_memory_path=str(psi_mem))
        row = pc.tick(busy_cores=0.5)  # cores alone would not trigger overload
        assert row["action"] == "withdraw"
        assert row["psi_mem10"] == 22.5
        assert row["reason"] == "memory psi 22.5>10.0"
        assert pc.memory_psi_withdraws == 1
        rows = _rows(ledger)
        assert rows[0]["reason"].startswith("memory psi")
        tracer.close_jobserver(path, fd)


def test_count_memory_psi_withdraws_reads_the_shared_ledger(tmp_path):
    """UX-850: the report's `psi_memory_withdraws` scalar comes from
    this reader against the same ledger `Broker` and `PoolController`
    both write to - it must not count a CPU-PSI or busy withdraw."""
    ledger = tmp_path / "ledger.jsonl"
    ledger.write_text("\n".join(json.dumps(row) for row in [
        {"action": "withdraw", "reason": "memory psi 15.0>10.0"},
        {"action": "withdraw", "reason": "psi 15.0>10.0"},
        {"action": "withdraw", "reason": "busy 5.0>capacity 4"},
        {"action": "hold", "reason": "memory psi 15.0>10.0"},
    ]) + "\n")
    assert tracer.count_memory_psi_withdraws(str(ledger)) == 1
