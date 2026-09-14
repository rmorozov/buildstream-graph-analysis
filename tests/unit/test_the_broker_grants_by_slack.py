"""UX-849: the Acceptance Test's own guard. `Broker` moves tokens out of
the global jobserver FIFO into per-element proxies, real FIFOs
throughout - never round-robin, always the running element with the
least slack first, capped at its own `-jK` minus one. An element `plan`
does not name gets the plan's own median slack; a tie is broken by
name. Without `--plan` nothing about the shim's argv changes at all.
"""
import json
import os
import signal
import subprocess
import sys
import time

from tools import bst_native_build_tracer as tracer
from tools.native_trace.bwrap_shim import build_shim_argv

# UX-854: a real child reading real bytes off a real proxy FIFO, then
# killed before it can release them - the same shape
# `test_a_leaked_token_is_refilled.py` uses for the global FIFO.
_HOLDER = """
import json, os, sys, time
fifo_path, k, ledger, tool, marker = sys.argv[1:6]
k = int(k)
fd = os.open(fifo_path, os.O_RDWR)
if k:
    os.read(fd, k)
row = {"event": "acquire", "tool": tool, "pid": os.getpid(), "tokens": k, "t": time.time()}
with open(ledger, "a", encoding="utf-8") as f:
    f.write(json.dumps(row) + chr(10))
open(marker, "w").close()
while True:
    time.sleep(1)
"""


def _spawn_holder(tmp_path, fifo_path, tokens, ledger, tool="ninja"):
    script = tmp_path / "holder.py"
    if not script.exists():
        script.write_text(_HOLDER)
    marker = tmp_path / f"marker-{tokens}-{tool}"
    proc = subprocess.Popen([sys.executable, str(script), fifo_path, str(tokens),
                             ledger, tool, str(marker)])
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.02)
    else:
        proc.kill()
        raise AssertionError("the fake holder never wrote its acquire row")
    return proc


def _write_acquire(ledger, tool, pid, tokens):
    row = {"event": "acquire", "tool": tool, "pid": pid, "tokens": tokens,
          "t": time.time()}
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _leaked_rows(ledger):
    with open(ledger, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle
               if line.strip() and json.loads(line)["event"] == "leaked"]


def _broker(tmp_path, elements, plan, ceiling=8):
    """A real global FIFO seeded with `ceiling - 1` tokens, and one real
    proxy FIFO per name in `elements`."""
    global_scratch = str(tmp_path / "global")
    os.makedirs(global_scratch, exist_ok=True)
    _path, global_fd, tokens = tracer.open_jobserver(ceiling, global_scratch)
    proxies_dir = str(tmp_path / "proxies")
    proxy_fds = tracer.create_jobserver_proxies(proxies_dir, dict.fromkeys(elements, "make"))
    ledger = str(tmp_path / "ledger.jsonl")
    broker = tracer.Broker(global_fd, proxy_fds, plan, ledger_path=ledger,
                           scratch={"proxies_dir": proxies_dir})
    return broker, global_fd, proxy_fds, ledger


def _readable(fd) -> int:
    """How many tokens a fd currently holds - read then push back, so
    inspecting state never consumes it."""
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
    import json
    with open(ledger, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


class TestPopulation:
    def test_zero_running_elements_returns_every_token_to_the_global_fifo(self, tmp_path):
        broker, global_fd, proxy_fds, _ledger = _broker(
            tmp_path, ["a", "b"], {"a": 100, "b": 200}, ceiling=4)
        broker.tick()
        assert _readable(global_fd) == 3, "nothing running - nothing to grant"
        assert _readable(proxy_fds["a"]) == 0
        assert _readable(proxy_fds["b"]) == 0

    def test_one_running_element_is_capped_at_its_own_jk_minus_one(self, tmp_path):
        broker, global_fd, proxy_fds, _ledger = _broker(
            tmp_path, ["a"], {"a": 100}, ceiling=8)
        broker.note_running("a", max_jobs=4)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 3, "capped at -j4 minus the implicit token"
        assert _readable(global_fd) == 4, "the rest stays in the global pool"
        assert broker.grants == 1

    def test_two_running_elements_grant_least_slack_first(self, tmp_path):
        # The least-slack element sorts *last* by name, so a grant order
        # that reads names alone (the verifier's mutation) goes red here.
        broker, global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a", "b"], {"a": 50, "b": 5}, ceiling=8)
        broker.note_running("a", max_jobs=8)
        broker.note_running("b", max_jobs=8)
        broker.tick()
        rows = _rows(ledger)
        grants = [row for row in rows if row["event"] == "grant"]
        assert grants[0]["element"] == "b", "least slack is filled to its own cap first"
        assert grants[0]["tokens"] == 7, "b's own cap (-j8 - 1) takes everything b can hold"
        assert _readable(proxy_fds["b"]) == 7
        assert _readable(proxy_fds["a"]) == 0, "nothing left after b's cap"
        assert _readable(global_fd) == 0


class TestThePlan:
    def test_an_element_absent_from_the_plan_gets_the_median_slack(self, tmp_path):
        broker, _global_fd, proxy_fds, _ledger = _broker(
            tmp_path, ["a", "b", "c", "unplanned"],
            {"a": 10, "b": 20, "c": 30}, ceiling=8)
        assert broker.median_slack == 20
        assert broker.slack_for("unplanned") == 20
        broker.note_running("unplanned", max_jobs=8)
        broker.note_running("a", max_jobs=8)  # slack 10 - should still go first
        broker.tick()
        assert _readable(proxy_fds["a"]) == 7
        assert _readable(proxy_fds["unplanned"]) == 0

    def test_a_tie_on_slack_is_broken_by_name_order(self, tmp_path):
        broker, _global_fd, _proxy_fds, ledger = _broker(
            tmp_path, ["zeta", "alpha"], {"zeta": 5, "alpha": 5}, ceiling=3)
        broker.note_running("zeta", max_jobs=8)
        broker.note_running("alpha", max_jobs=8)
        broker.tick()
        grants = [row for row in _rows(ledger) if row["event"] == "grant"]
        assert grants[0]["element"] == "alpha", "same slack - name order wins"


class TestDrain:
    def test_an_element_ending_drains_its_proxy_back_to_the_global_fifo(self, tmp_path):
        broker, global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 5}, ceiling=8)
        broker.note_running("a", max_jobs=4)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 3
        before = _readable(global_fd)
        broker.note_done("a")
        assert _readable(proxy_fds["a"]) == 0
        assert _readable(global_fd) == before + 3
        assert "a" not in broker.running
        drains = [row for row in _rows(ledger) if row["event"] == "drain"]
        assert drains[0] == {"event": "drain", "element": "a", "tokens": 3,
                             "t": drains[0]["t"]}
        assert broker.drains == 1


class TestLeaks:
    """UX-854: a proxy token a killed job never returned is audited too -
    at `note_done` (the proxy's own remainder, back to the global FIFO)
    and on `tick` (a dead wrapper holder of a still-running element,
    back to that element's proxy)."""

    def test_a_dead_note_done_holder_is_refilled_to_the_global_fifo(self, tmp_path):
        broker, global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 5}, ceiling=8)
        broker.note_running("a", max_jobs=4)
        broker.tick()
        assert _readable(proxy_fds["a"]) == 3, "granted 3 (cap -j4 minus one)"
        proxy_path = str(tmp_path / "proxies" / "a.fifo")
        holder = _spawn_holder(tmp_path, proxy_path, 2, ledger, tool="ninja")
        try:
            holder.send_signal(signal.SIGKILL)
            holder.wait(timeout=5)
            before = _readable(global_fd)
            broker.note_done("a")
            assert _readable(proxy_fds["a"]) == 0
            assert _readable(global_fd) == before + 3, "1 drained + 2 leaked = the full grant"
            leaked = _leaked_rows(ledger)
            assert len(leaked) == 1
            assert leaked[0]["element"] == "a"
            assert leaked[0]["tokens"] == 2
            assert leaked[0]["pid"] is None
            assert broker.leaks == 1
            assert broker.tokens_refilled == 2
        finally:
            if holder.poll() is None:
                holder.kill()
                holder.wait(timeout=5)

    def test_a_dead_tick_holder_mapped_to_a_running_element_is_refilled_to_its_proxy(self, tmp_path):
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 5}, ceiling=1)  # 0 seed tokens - nothing to distribute
        broker.note_running("a", max_jobs=4)
        dead_pid = 2**22 - 1
        _write_acquire(ledger, tool="ninja", pid=dead_pid, tokens=2)

        broker.tick({dead_pid: "a"})
        assert _readable(proxy_fds["a"]) == 2, "the dead holder's tokens go back to its proxy"
        leaked = _leaked_rows(ledger)
        assert len(leaked) == 1
        assert leaked[0] == {"event": "leaked", "element": "a", "pid": dead_pid,
                             "tokens": 2, "t": leaked[0]["t"]}
        assert broker.leaks == 1
        assert broker.tokens_refilled == 2

        broker.tick({dead_pid: "a"})
        assert _readable(proxy_fds["a"]) == 2, "not refilled a second time"
        assert len(_leaked_rows(ledger)) == 1, "a second tick writes nothing more"

    def test_a_live_holder_is_left_alone(self, tmp_path):
        broker, _global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 5}, ceiling=1)
        broker.note_running("a", max_jobs=4)
        _write_acquire(ledger, tool="ninja", pid=os.getpid(), tokens=2)
        broker.tick({os.getpid(): "a"})
        assert _readable(proxy_fds["a"]) == 0, "a live holder's tokens are never refilled"
        assert _leaked_rows(ledger) == []
        assert broker.leaks == 0

    def test_a_pid_with_no_element_is_refilled_to_the_global_fifo(self, tmp_path):
        """UX-854's verifier (point 1): the broker is now the *sole*
        auditor when it exists - an unmapped pid is not left to
        `PoolController.audit_leaks` (which does not run at all against
        this ledger), it is refilled by the broker itself, to the
        global FIFO rather than any one element's proxy."""
        broker, global_fd, proxy_fds, ledger = _broker(
            tmp_path, ["a"], {"a": 5}, ceiling=1)  # 0 seed tokens - nothing to distribute
        # "a" is never `note_running` - nothing is running to redistribute
        # the freed tokens to within this same `tick()`, so the refill
        # itself (not a later grant) is what lands in the global FIFO.
        dead_pid = 2**22 - 2
        _write_acquire(ledger, tool="ninja", pid=dead_pid, tokens=2)
        before = _readable(global_fd)
        broker.tick({})  # pid_to_element does not name it
        assert _readable(proxy_fds["a"]) == 0, "not this element's own proxy"
        assert _readable(global_fd) == before + 2, "unmapped - refilled to the global FIFO"
        leaked = _leaked_rows(ledger)
        assert len(leaked) == 1
        assert leaked[0] == {"event": "leaked", "tool": "ninja", "pid": dead_pid,
                             "tokens": 2, "element": None, "t": leaked[0]["t"]}


class TestExclusiveAudit:
    """UX-854's verifier, point 1: `PoolController.audit_leaks` and
    `Broker._audit_wrapper_leaks` share one ledger unlocked - two
    auditors racing it can each refill the same dead pid before either
    has written its own `leaked` row. `psi_paths["broker_owns_audit"] =
    True` makes the controller's side a no-op instead, deterministically
    - not a timing race to demonstrate."""

    def test_the_broker_is_the_sole_auditor_when_one_exists(self, tmp_path):
        global_scratch = str(tmp_path / "global")
        os.makedirs(global_scratch, exist_ok=True)
        _path, fd, _tokens = tracer.open_jobserver(4, global_scratch)  # seeds 3
        os.set_blocking(fd, False)  # `_readable` below must never block
        ledger = str(tmp_path / "ledger.jsonl")
        # `PoolController.__init__` truncates `ledger_path` - both
        # constructed before the dead holder's own `acquire` row lands.
        pc = tracer.PoolController(fd, ceiling=4, ledger_path=ledger,
                                   psi_paths={"broker_owns_audit": True})
        broker = tracer.Broker(fd, {}, {}, ledger_path=ledger)
        dead_pid = 2**22 - 3
        _write_acquire(ledger, tool="mold", pid=dead_pid, tokens=1)
        os.read(fd, 1)  # the dead holder "took" 1 of the 3 seeded tokens
        assert _readable(fd) == 2

        pc_rows = pc.audit_leaks()  # one audit cycle of each, in this order
        broker.tick({})
        assert pc_rows == [], "the controller must not audit when the broker owns it"
        assert broker.leaks == 1
        assert _readable(fd) == 3, "the token came back exactly once"
        rows = _leaked_rows(ledger)
        assert len(rows) == 1
        assert rows[0] == {"event": "leaked", "tool": "mold", "pid": dead_pid,
                           "tokens": 1, "element": None, "t": rows[0]["t"]}


class TestPollRefreshesPidToElement:
    """UX-854's verifier, point 2: `poll()`'s once-a-second `pid_to_
    element` refresh, against a real raw log in the hook's own
    `START`/`END` shape (`tests/unit/test_the_token_ledger_has_two_
    shares.py::TestReadPidToElement`'s own fixture shape)."""

    def test_poll_maps_a_dead_holders_pid_and_refills_its_proxy(self, tmp_path):
        dead_pid = 2**22 - 5
        raw_log_path = str(tmp_path / "plane2.log")
        with open(raw_log_path, "w", encoding="utf-8") as handle:
            handle.write(
                f"START pid={dead_pid} ppid=1 ts=10.0 element=a.bst cmd=ninja\n"
                f"END pid={dead_pid} ppid=1 ts=10.5 element=a.bst cmd=ninja\n")
        global_scratch = str(tmp_path / "global")
        os.makedirs(global_scratch, exist_ok=True)
        _path, global_fd, _tokens = tracer.open_jobserver(1, global_scratch)  # 0 seed
        proxies_dir = str(tmp_path / "proxies")
        proxy_fds = tracer.create_jobserver_proxies(proxies_dir, {"a.bst": "make"})
        ledger = str(tmp_path / "ledger.jsonl")
        broker = tracer.Broker(
            global_fd, proxy_fds, {"a.bst": 5}, ledger_path=ledger,
            scratch={"proxies_dir": proxies_dir, "raw_log_path": raw_log_path})
        broker.note_running("a.bst", max_jobs=4)
        _write_acquire(ledger, tool="ninja", pid=dead_pid, tokens=2)

        broker.poll()
        assert broker.pid_to_element == {dead_pid: "a.bst"}
        assert _readable(proxy_fds["a.bst"]) == 2
        leaked = _leaked_rows(ledger)
        assert len(leaked) == 1
        assert leaked[0]["pid"] == dead_pid
        assert leaked[0]["element"] == "a.bst"


def test_without_a_plan_the_shims_argv_is_byte_for_byte_unchanged():
    """The Decisions' own guard: `proxy_fifo` left at its default `None`
    must produce exactly the argv the mode already produced without it."""
    read_fd, write_fd = os.pipe()
    try:
        kwargs = dict(
            real_bwrap="/usr/bin/bwrap",
            bst_args=[
                "--dir", "buildstream/proj/core.bst",
                "--chdir", "buildstream/proj/core.bst",
                "--setenv", "MAKEFLAGS", "-j4",
                "sh", "-c", "make",
            ],
            bind_src="/tmp/host-trace-dir",
            bind_dst="/tmp/.bst-native-trace",
            preload_so="/tmp/.bst-native-trace/hook.so",
            trace_log="/tmp/.bst-native-trace/trace.log",
            jobserver_fd=read_fd,
            project_max_jobs=4,
            element_kind="make",
        )
        with_default = build_shim_argv(**kwargs)
        without_param = build_shim_argv(proxy_fifo=None, **kwargs)
        assert with_default == without_param
    finally:
        os.close(read_fd)
        os.close(write_fd)
