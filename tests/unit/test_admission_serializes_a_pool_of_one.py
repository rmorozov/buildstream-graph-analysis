"""UX-1005 track B: `run_admitted` (`tools/native_trace/bwrap_shim.py`)
reads a real token from the pool before starting `bwrap`, and only
releases it once `waitpid` returns - so a pool of 1 serializes two
sandboxes rather than letting them run at once.

Each call runs in its own subprocess, not a Python thread: `run_admitted`
calls `os.fork()`, and forking from one thread of a multi-threaded
process while another thread holds an unrelated lock is exactly the
hazard that leaves the fork'd copy deadlocked - not this guard's
target."""
import json
import os
import subprocess
import sys
import time

_RUN_ONE = """
import sys
sys.path.insert(0, {srcdir!r})
from tools.native_trace.bwrap_shim import run_admitted
status = run_admitted(sys.argv[1], [sys.argv[1]], (None, None),
                      (sys.argv[2], None), (sys.argv[3], sys.argv[4]))
sys.exit(status)
"""


def _fake_bwrap(path, sleep_s):
    path.write_text(f"#!/bin/sh\nsleep {sleep_s}\nexit 0\n")
    path.chmod(0o755)
    return str(path)


def _seed_pool(path, tokens=1):
    """A FIFO's buffer is discarded once every fd on it closes - the
    seeding fd has to outlive the test, the same reason `open_jobserver`
    (`tools/jobserver/pool.py`) keeps its own fd open for the FIFO's
    whole life. Returns the fd so the caller can hold it."""
    os.mkfifo(path)
    fd = os.open(path, os.O_RDWR)
    os.write(fd, b"+" * tokens)
    return fd


def _spawn(runner_path, real_bwrap, pool_path, ledger_path, element):
    return subprocess.Popen(
        [sys.executable, runner_path, real_bwrap, pool_path, ledger_path, element])


def test_a_pool_of_one_serializes_the_second_shim_behind_the_first(tmp_path):
    pool_path = str(tmp_path / "admission")
    seed_fd = _seed_pool(pool_path, tokens=1)
    ledger_path = str(tmp_path / "ledger.jsonl")
    sleep_s = 0.3
    bwrap = _fake_bwrap(tmp_path / "bwrap", sleep_s)

    repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    runner_path = str(tmp_path / "run_one.py")
    with open(runner_path, "w", encoding="utf-8") as handle:
        handle.write(_RUN_ONE.format(srcdir=repo_root))

    overall_start = time.time()
    procs = [
        _spawn(runner_path, bwrap, pool_path, ledger_path, "mod-a.bst"),
        _spawn(runner_path, bwrap, pool_path, ledger_path, "mod-b.bst"),
    ]
    for proc in procs:
        assert proc.wait(timeout=5) == 0
    overall_elapsed = time.time() - overall_start

    # Serialized: two sleeps back to back, not overlapped.
    assert overall_elapsed >= 2 * sleep_s * 0.9, (
        f"the two sandboxes overlapped: wall {overall_elapsed:.2f}s for "
        f"two {sleep_s}s sandboxes on a pool of 1")

    rows = [json.loads(line) for line in open(ledger_path, encoding="utf-8")]
    waits = {row["element"]: row["wait_us"] for row in rows
             if row["event"] == "admission_wait"}
    assert set(waits) == {"mod-a.bst", "mod-b.bst"}
    # Whichever ran second waited roughly the other's sleep for its token.
    assert max(waits.values()) >= sleep_s * 0.5 * 1_000_000
    os.close(seed_fd)
