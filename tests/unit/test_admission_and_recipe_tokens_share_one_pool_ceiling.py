"""UX-1005 track C, Ruslan's verifier fix: admission draws its token
from the *same* FIFO the recipe pool does, so an admitted sandbox's
own hold and its recipe's extra `-jK` wrapper draws can never together
exceed the pool's ceiling - a separate admission pool let a giant draw
up to its own recipe tokens on top of every admitted sandbox's, nearly
doubling the ceiling (barely better than no admission at all).

Real `run_traced_build` wiring, not a hand-built FIFO: capacity 4, 3
single-core admitted sandboxes (real subprocesses, `run_admitted`) plus
one "recipe" thread spinning for the 8 extra wrapper tokens a `-j8`
giant would draw - every hold interval logged to the ledger, and the
peak concurrent count read back from it must never exceed 4. Mutation:
a second, separate admission FIFO (the pre-fix shape) - `run_admitted`
and the wrapper draws then read from different pools, and the giant's
draws are no longer capped by what admission already spent."""
import json
import os
import stat
import sys
import threading
import time

import pytest

from tools import bst_native_build_tracer as tracer

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# `run_admitted` already writes one `admission_wait` row per sandbox -
# `wait_us` is exactly the span from process start to token grant, so
# `t_start + wait_us` is when the hold itself began (the only part that
# has to respect the pool's ceiling); `t_end` (just after `run_admitted`
# returns, past its own release) closes it.
_RUN_ONE = """
import sys, json, time
sys.path.insert(0, {srcdir!r})
from tools.native_trace.bwrap_shim import run_admitted
t_start = time.time()
status = run_admitted(sys.argv[1], [sys.argv[1]], (None, None),
                      (sys.argv[2], None), (sys.argv[3], sys.argv[4]))
t_end = time.time()
with open(sys.argv[3], "a", encoding="utf-8") as handle:
    handle.write(json.dumps({{"event": "admission_process", "element": sys.argv[4],
                             "t_start": t_start, "t_end": t_end}}) + "\\n")
sys.exit(status)
"""


def _fake_bwrap(path, sleep_s):
    path.write_text(f"#!/bin/sh\nsleep {sleep_s}\nexit 0\n")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)
    return str(path)



@pytest.fixture(autouse=True)
def _admission_on(monkeypatch):
    monkeypatch.setenv("BGA_ADMISSION", "1")

def _stub_shim(monkeypatch):
    monkeypatch.setattr(tracer, "compile_hook", lambda d: None)
    monkeypatch.setattr(tracer, "install_bwrap_shim", lambda d: "/usr/bin/bwrap")
    monkeypatch.setattr(tracer, "write_bwrap_shim", lambda d: os.path.join(d, "bwrap"))
    monkeypatch.setattr(tracer, "probe_bwrap_shim", lambda p: None)


def _recipe_draws(pool_path, ledger_path, hold_s, deadline):
    """The giant's own extra `-jK` draws - a real non-blocking read
    against the *same* FIFO admission uses, logged the same interval
    shape (`t_start`/`t_end`) so the test can compute peak concurrency
    across both roles from one ledger."""
    fd = os.open(pool_path, os.O_RDWR | os.O_NONBLOCK)
    threads = []

    def _one():
        try:
            got = os.read(fd, 1)
        except BlockingIOError:
            return
        if not got:
            return
        t_start = time.time()
        time.sleep(hold_s)
        t_end = time.time()
        os.write(fd, b"+")
        with open(ledger_path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(
                {"event": "recipe_hold", "t_start": t_start, "t_end": t_end}) + "\n")

    while time.time() < deadline:
        threads.append(threading.Thread(target=_one))
        threads[-1].start()
        time.sleep(hold_s / 4)
    for thread in threads:
        thread.join(timeout=5)
    os.close(fd)


def _peak_concurrent_holds_from_lines(lines):
    rows = [json.loads(line) for line in lines]
    waits = {row["element"]: row["wait_us"] for row in rows
             if row.get("event") == "admission_wait"}
    events = []
    for row in rows:
        if row.get("event") == "recipe_hold":
            events.append((row["t_start"], 1))
            events.append((row["t_end"], -1))
        elif row.get("event") == "admission_process":
            hold_start = row["t_start"] + waits.get(row["element"], 0) / 1_000_000
            events.append((hold_start, 1))
            events.append((row["t_end"], -1))
    held, peak = 0, 0
    for _t, delta in sorted(events):
        held += delta
        peak = max(peak, held)
    return peak


def test_admission_and_recipe_draws_never_exceed_the_pool_capacity(tmp_path, monkeypatch):
    project = tmp_path / "proj"
    project.mkdir()
    raw_log = tmp_path / "trace.log"
    _stub_shim(monkeypatch)
    hold_s = 0.15
    seen: dict = {}
    real_popen = tracer.subprocess.Popen

    def fake_popen(cmd, cwd=None, env=None, **kw):
        admission_pool_path = env["BST_TRACE_ADMISSION_POOL"]
        recipe_pool_path = env["BST_TRACE_JOBSERVER"]
        ledger_path = os.path.join(env["BST_TRACE_BIND_SRC"], "jobserver_ledger.jsonl")
        seen["ledger_path"] = ledger_path
        bwrap = _fake_bwrap(tmp_path / "bwrap", hold_s)
        runner_path = str(tmp_path / "run_one.py")
        with open(runner_path, "w", encoding="utf-8") as handle:
            handle.write(_RUN_ONE.format(srcdir=_REPO_ROOT))

        admitted = [
            real_popen([sys.executable, runner_path, bwrap, admission_pool_path,
                       ledger_path, f"mod-{i}.bst"])
            for i in range(3)]
        # The recipe's own extra `-jK` draws come from the *recipe*
        # pool, not the admission one - only the fix makes these the
        # same FIFO; the mutation must be free to give them separate
        # supplies for this guard to tell the two shapes apart.
        recipe_thread = threading.Thread(
            target=_recipe_draws,
            args=(recipe_pool_path, ledger_path, hold_s, time.time() + hold_s * 4))
        recipe_thread.start()
        for proc in admitted:
            assert proc.wait(timeout=5) == 0
        recipe_thread.join(timeout=5)
        # UX-1005 track C, verifier fix: `run_traced_build`'s own
        # scratch (`bind_dir`, hence this ledger) is removed the moment
        # it returns - read it here, while the fake build is still
        # "running", not after.
        with open(ledger_path, encoding="utf-8") as handle:
            seen["ledger_lines"] = handle.readlines()
        return type("P", (), {"wait": lambda self: 0})()

    monkeypatch.setattr(tracer.subprocess, "Popen", fake_popen)

    tracer.run_traced_build(str(project), ["bst", "build", "x.bst"],
                            str(raw_log), jobserver=4, jobserver_pool="fixed")

    assert "ledger_lines" in seen
    peak = _peak_concurrent_holds_from_lines(seen["ledger_lines"])
    assert peak <= 4, f"{peak} tokens held at once against a capacity of 4"
    assert peak >= 3, "the scenario never actually overlapped - not a real guard"
