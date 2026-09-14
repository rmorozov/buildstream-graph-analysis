"""UX-847: analyze/v6's `jobserver` block, over a synthetic ledger.

`compute_jobserver_shares` reads only `PoolController` ticks (rows
carrying `action`) - a wrapper's `event` row (UX-846) is not a control
step. `compute_jobserver_per_element`/`compute_jobserver_block` classify
every Plane 1 element as pinned, held, yes or unknown_kind.
`compute_max_jobs_advice` refuses a pinned element rather than guessing
a number. `tokens_by_element` (`tools/bst_native_build_tracer.py`) is
the producer: UX-846's wrapper rows joined to an element by pid.
"""
from bga.correlate import (
    compute_jobserver_block,
    compute_jobserver_per_element,
    compute_jobserver_shares,
    compute_max_jobs_advice,
)
from tools.bst_native_build_tracer import (
    read_pid_to_element,
    summarize_jobserver_tokens_by_element,
)
from tools.bst_native_build_tracer import (
    tokens_by_element as producer_tokens_by_element,
)


def _tick(busy_cores, pool, action="hold"):
    return {"t_us": 0, "busy_cores": busy_cores, "psi_some10": None,
            "pool": pool, "action": action, "reason": "synthetic"}


def _wrapper_row(event="acquire", tool="lld", pid=111, tokens=2):
    return {"event": event, "tool": tool, "pid": pid, "tokens": tokens, "t": 0}


class TestTheTwoShares:
    def test_no_rows_is_zero_and_zero(self):
        assert compute_jobserver_shares([], capacity=4) == (0.0, 0.0)

    def test_one_idle_row(self):
        # busy 1 < capacity(4) - 1, pool > 0: idle.
        rows = [_tick(1.0, pool=2)]
        assert compute_jobserver_shares(rows, capacity=4) == (1.0, 0.0)

    def test_one_starved_row(self):
        rows = [_tick(1.0, pool=0)]
        assert compute_jobserver_shares(rows, capacity=4) == (0.0, 1.0)

    def test_many_rows_mixed(self):
        rows = [
            _tick(1.0, pool=2),   # idle
            _tick(1.0, pool=0),   # starved
            _tick(3.9, pool=2),   # within band - neither
            _tick(1.0, pool=1),   # idle
        ]
        idle, starved = compute_jobserver_shares(rows, capacity=4)
        assert idle == 0.5
        assert starved == 0.25

    def test_a_wrapper_row_is_not_a_tick(self):
        """The population is controller ticks, not every ledger row -
        UX-846's acquire/release rows have no `action` and must not be
        counted as one, however their fields would compare."""
        rows = [_tick(1.0, pool=2), _wrapper_row()]
        idle, starved = compute_jobserver_shares(rows, capacity=4)
        assert idle == 1.0, "one tick, idle; the wrapper row is skipped"
        assert starved == 0.0


class TestThePerElementTable:
    def test_run_without_the_mode_is_absent(self):
        assert compute_jobserver_block({}, ["a.bst"]) is None
        assert compute_jobserver_block(
            {"jobserver": None}, ["a.bst"]) is None

    def test_every_element_joined(self):
        decisions = [{"element": "a.bst", "decision": "joined"},
                     {"element": "b.bst", "decision": "capped_pending"}]
        table = compute_jobserver_per_element(["a.bst", "b.bst"], decisions)
        assert table["a.bst"]["joined"] == "yes"
        assert table["b.bst"]["joined"] == "yes"

    def test_one_pinned_and_one_held(self):
        decisions = [{"element": "pinned.bst", "decision": "pinned"},
                     {"element": "held.bst", "decision": "joined"}]
        tokens_by_element = {
            "held.bst": {"tokens_held_p50": 2, "tokens_held_max": 4}}
        table = compute_jobserver_per_element(
            ["pinned.bst", "held.bst", "unseen.bst"], decisions,
            tokens_by_element)
        assert table["pinned.bst"]["joined"] == "pinned"
        assert table["pinned.bst"]["tokens_held_p50"] is None
        assert table["held.bst"]["joined"] == "held"
        assert table["held.bst"]["tokens_held_p50"] == 2
        assert table["held.bst"]["tokens_held_max"] == 4
        assert table["unseen.bst"]["joined"] == "unknown_kind"

    def test_the_full_block(self):
        native_report = {
            "jobserver": 4,
            "jobserver_pool": {"mode": "dynamic", "ceiling": 4, "capacity": 4},
            "jobserver_ledger": [_tick(1.0, pool=2), _tick(1.0, pool=0)],
            "jobserver_decisions": [
                {"element": "pinned.bst", "decision": "pinned"},
                {"element": "held.bst", "decision": "joined"},
                {"element": "yes.bst", "decision": "joined"},
            ],
        }
        block = compute_jobserver_block(
            native_report, ["pinned.bst", "held.bst", "yes.bst"],
            tokens_by_element={"held.bst": {"tokens_held_p50": 1,
                                            "tokens_held_max": 3}})
        assert block["mode"] == "dynamic"
        assert block["pool_ceiling"] == 4
        assert block["tokens_idle_share"] == 0.5
        assert block["tokens_starved_share"] == 0.5
        assert block["per_element"]["pinned.bst"]["joined"] == "pinned"
        assert block["per_element"]["held.bst"]["joined"] == "held"
        assert block["per_element"]["yes.bst"]["joined"] == "yes"


class TestAPinnedElementRefuses:
    def _host_samples(self):
        return {"header": {"monotonic_at_start": 0, "wall_at_start": 0},
                "samples": [{"t": 0, "cpu_busy_cores": 1.0, "cores": 4},
                            {"t": 2, "cpu_busy_cores": 1.0, "cores": 4},
                            {"t": 4, "cpu_busy_cores": 1.0, "cores": 4}]}

    def test_a_pinned_element_gets_no_number(self):
        tasks = [{"element": "pinned.bst", "start_us": 0, "finish_us": 4_000_000}]
        advice = compute_max_jobs_advice(
            self._host_samples(), tasks, {"pinned.bst": 1},
            pinned_elements={"pinned.bst"})
        row = advice["elements"][0]
        assert row["refusal"] == "pinned by the project"
        assert row["recommended_max_jobs"] is None


class TestTheTokensByElementProducer:
    """UX-847's hold: `held`/`tokens_held_*` were always null in a real
    capture - no producer joined UX-846's wrapper `acquire` rows to an
    element. `tokens_by_element` is that join, over the raw pid; this
    class is its population, zero/one/many, plus the two shapes a
    ledger's wrapper rows come in that must not be counted as a hold."""

    def test_no_acquire_rows_is_empty(self):
        assert producer_tokens_by_element([], {1: "a.bst"}) == ({}, 0)

    def test_one_acquire_row(self):
        rows = [_wrapper_row(pid=1, tokens=3)]
        assert producer_tokens_by_element(rows, {1: "held.bst"}) == (
            {"held.bst": [3]}, 0)

    def test_a_release_row_is_ignored(self):
        rows = [_wrapper_row(event="release", pid=1, tokens=3)]
        assert producer_tokens_by_element(rows, {1: "held.bst"}) == ({}, 0)

    def test_a_pid_no_element_owns_is_unmapped(self):
        rows = [_wrapper_row(pid=99, tokens=3)]
        assert producer_tokens_by_element(rows, {1: "held.bst"}) == ({}, 1)

    def test_two_acquires_by_one_element_keep_both_values(self):
        """Many: the join accumulates, it does not overwrite - the
        input `statistics.median`/`max` (the existing reduction) need
        to disagree about which one to report."""
        rows = [_wrapper_row(pid=1, tokens=2), _wrapper_row(pid=1, tokens=4)]
        raw, unmapped = producer_tokens_by_element(rows, {1: "held.bst"})
        assert raw == {"held.bst": [2, 4]}
        assert unmapped == 0
        by_element, unmapped = summarize_jobserver_tokens_by_element(
            rows, {1: "held.bst"})
        assert by_element == {
            "held.bst": {"tokens_held_p50": 3, "tokens_held_max": 4}}
        assert unmapped == 0

    def test_a_malformed_row_does_not_raise(self):
        rows = [{"event": "acquire"}, "not a dict", None]
        assert producer_tokens_by_element(rows, {1: "held.bst"}) == ({}, 0)


class TestReadPidToElement:
    """`read_pid_to_element`'s own guard - `test_the_full_block` above
    fed it a `pid_to_element` dict directly and could not tell a real
    reader from `return {}`; every case here writes a real raw log in
    the tracer's own `START pid=.. ppid=.. ts=.. element=.. cmd=..`
    format (`parse_trace_log`'s own shape)."""

    def _write(self, tmp_path, text):
        path = tmp_path / "plane2.log"
        path.write_text(text, encoding="utf-8")
        return str(path)

    def test_two_elements_three_pids(self, tmp_path):
        path = self._write(tmp_path,
            "START pid=100 ppid=1 ts=10.0 element=a.bst cmd=cc1 -c a.c\n"
            "END pid=100 ppid=1 ts=10.5 element=a.bst cmd=cc1 -c a.c\n"
            "START pid=101 ppid=1 ts=11.0 element=a.bst cmd=cc1 -c b.c\n"
            "END pid=101 ppid=1 ts=11.5 element=a.bst cmd=cc1 -c b.c\n"
            "START pid=200 ppid=1 ts=12.0 element=b.bst cmd=ld -o b\n"
            "END pid=200 ppid=1 ts=12.5 element=b.bst cmd=ld -o b\n")
        assert read_pid_to_element(path) == {
            100: "a.bst", 101: "a.bst", 200: "b.bst"}

    def test_an_empty_log_is_an_empty_map(self, tmp_path):
        path = self._write(tmp_path, "")
        assert read_pid_to_element(path) == {}

    def test_a_malformed_line_does_not_drop_the_well_formed_pids(self, tmp_path):
        path = self._write(tmp_path,
            "START pid=100 ppid=1 ts=10.0 element=a.bst cmd=cc1 -c a.c\n"
            "this is unrelated stderr noise that ended up in the same file\n"
            "START pid=bogus ppid=1 ts=oops element=a.bst cmd=broken\n"
            "END pid=100 ppid=1 ts=10.5 element=a.bst cmd=cc1 -c a.c\n")
        assert read_pid_to_element(path) == {100: "a.bst"}
