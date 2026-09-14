"""UX-849: the Acceptance Test's own guard. `Broker` moves tokens out of
the global jobserver FIFO into per-element proxies, real FIFOs
throughout - never round-robin, always the running element with the
least slack first, capped at its own `-jK` minus one. An element `plan`
does not name gets the plan's own median slack; a tie is broken by
name. Without `--plan` nothing about the shim's argv changes at all.
"""
import os

from tools import bst_native_build_tracer as tracer
from tools.native_trace.bwrap_shim import build_shim_argv


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
