"""UX-852: `PoolController.audit_leaks` against a real FIFO and real
pids - a wrapper `acquire` row whose pid is gone gets its tokens back
and a `leaked` ledger row; a live holder's tokens stay held. The killed
holder is a real Python child reading real bytes off the real FIFO,
never a proxy for the kernel object or the process table.
"""
import array
import fcntl
import json
import os
import signal
import subprocess
import sys
import termios
import time

from tools import bst_native_build_tracer as tracer

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


def _fifo(tmp_path, tokens):
    path = str(tmp_path / "jobserver")
    os.mkfifo(path)
    fd = os.open(path, os.O_RDWR)
    os.write(fd, b"+" * tokens)
    return path, fd


def _controller(tmp_path, fd, ceiling=8):
    ledger = str(tmp_path / "ledger.jsonl")
    # The pool thread must not move tokens under the audit's own guard:
    # capacity far above any busy-core reading, and the PSI path pinned
    # away from the host's file (CI's runner has one, avg10 19.31).
    pc = tracer.PoolController(fd, ceiling, capacity=10**6, ledger_path=ledger,
                               psi_paths={"cpu": str(tmp_path / "no-psi"),
                                          "memory": str(tmp_path / "no-memory-psi")})
    return pc, ledger


def _readable(fd):
    buf = array.array("i", [0])
    fcntl.ioctl(fd, termios.FIONREAD, buf, True)
    return buf[0]


def _leaked_rows(ledger):
    rows = []
    with open(ledger, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                row = json.loads(line)
                if row.get("event") == "leaked":
                    rows.append(row)
    return rows


def _write_acquire(ledger, tool, pid, tokens):
    row = {"event": "acquire", "tool": tool, "pid": pid, "tokens": tokens,
          "t": time.time()}
    with open(ledger, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


def _spawn_holder(tmp_path, fifo_path, tokens, ledger, tool="ld.lld"):
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


class TestAKilledHolderIsRefilledWithinTwoSeconds:
    """The Acceptance Test: SIGKILL a fake holder between its own
    `acquire` row and the release it will now never write; the pool's
    own audit thread (started by `start()`) must find it and refill."""

    def test_sigkilled_holder_is_refilled_and_named(self, tmp_path):
        path, fd = _fifo(tmp_path, tokens=4)
        pc, ledger = _controller(tmp_path, fd)
        holder = _spawn_holder(tmp_path, path, 2, ledger, tool="ninja")
        pid = holder.pid
        assert _readable(fd) == 2, "2 of 4 tokens held by the fake holder"

        pc.start()
        try:
            holder.send_signal(signal.SIGKILL)
            holder.wait(timeout=5)

            deadline = time.monotonic() + 2.0
            while time.monotonic() < deadline and _readable(fd) < 4:
                time.sleep(0.05)
            assert _readable(fd) == 4, "all 4 tokens readable within 2s of the kill"

            rows = _leaked_rows(ledger)
            assert len(rows) == 1
            assert rows[0]["pid"] == pid
            assert rows[0]["tool"] == "ninja"
            assert rows[0]["tokens"] == 2
        finally:
            pc.stop()
        os.close(fd)


class TestALiveHolderKeepsItsTokens:
    def test_a_sleeping_holder_is_left_alone(self, tmp_path):
        path, fd = _fifo(tmp_path, tokens=4)
        pc, ledger = _controller(tmp_path, fd)
        holder = _spawn_holder(tmp_path, path, 2, ledger, tool="mold")
        try:
            assert _readable(fd) == 2
            pc.start()
            time.sleep(1.5)  # at least one audit cycle (1s)
            assert _readable(fd) == 2, "a live holder's tokens are never refilled"
            assert _leaked_rows(ledger) == []
        finally:
            pc.stop()
            holder.kill()
            holder.wait(timeout=5)
        os.close(fd)


class TestOutstandingPidsAreCheckedIndependently:
    """A pid this test's own process holds (alive) beside one that was
    never alive (`2**22 - 1`) - written straight into the ledger, no
    wrapper subprocess needed to exercise the liveness split itself."""

    def test_the_live_pid_is_kept_the_dead_one_is_refilled(self, tmp_path):
        never_alive = 2**22 - 1
        path, fd = _fifo(tmp_path, tokens=4)
        pc, ledger = _controller(tmp_path, fd)
        _write_acquire(ledger, tool="mold", pid=os.getpid(), tokens=1)
        _write_acquire(ledger, tool="ld.gold", pid=never_alive, tokens=1)
        os.read(fd, 2)  # both "took" their tokens
        assert _readable(fd) == 2

        rows = pc.audit_leaks()
        assert [r["pid"] for r in rows] == [never_alive]
        assert _readable(fd) == 3, "only the never-alive pid's token came back"

        again = pc.audit_leaks()
        assert again == [], "the same pid is never refilled twice"
        assert _readable(fd) == 3
        os.close(fd)


class TestPopulationOfOutstandingHolders:
    def test_zero_holders_is_a_noop(self, tmp_path):
        path, fd = _fifo(tmp_path, tokens=4)
        pc, ledger = _controller(tmp_path, fd)
        assert pc.audit_leaks() == []
        assert _readable(fd) == 4
        os.close(fd)

    def test_one_dead_holder_is_refilled(self, tmp_path):
        path, fd = _fifo(tmp_path, tokens=4)
        pc, ledger = _controller(tmp_path, fd)
        _write_acquire(ledger, tool="ld.lld", pid=2**22 - 1, tokens=1)
        os.read(fd, 1)
        rows = pc.audit_leaks()
        assert len(rows) == 1
        assert _readable(fd) == 4
        os.close(fd)

    def test_many_dead_holders_are_all_refilled(self, tmp_path):
        path, fd = _fifo(tmp_path, tokens=6)
        pc, ledger = _controller(tmp_path, fd)
        dead_pids = [2**22 - 1, 2**22 - 2, 2**22 - 3]
        for pid in dead_pids:
            _write_acquire(ledger, tool="ld.lld", pid=pid, tokens=1)
        os.read(fd, 3)
        assert _readable(fd) == 3

        rows = pc.audit_leaks()
        assert {r["pid"] for r in rows} == set(dead_pids)
        assert _readable(fd) == 6
        os.close(fd)
