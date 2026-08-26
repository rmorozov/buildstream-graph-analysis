"""UX-310: the counter `TYPE_COUNTER` was reserved for.

`UX-298` pinned `TYPE_COUNTER = 4` with the comment "reserved rather
than used", under the rule that an event stream may carry only what a
capture measured. This is the caller - and it is **one** series, not
the three the item imagined, for two reasons worth having written down.

**The memory curve does not exist.** `max_rss_kb` is `ru_maxrss`: a
per-process peak over that process's *whole lifetime*, not a sample at
a moment. A curve drawn from it would sum peaks that never coexisted,
which is exactly what `compute_peak_memory` refuses at length - "two
processes that each peaked at 500 MB at different moments never held
1 GB between them". The rule that kept the constant reserved is the
rule that keeps this series out of the trace.

**"Cores busy" and "open process count" are the same question.** Both
are "how many traced processes were running at time t", and `bga` has
one answer to that already: `compute_max_concurrency`, over **matched**
records only, because a `sh -c` wrapper that `_exit()`s never runs its
destructor and its end is unknown. Excluding it from the peak and
including it in the curve would be two answers to one question.

So: one series, and the clause that makes it worth having is that its
peak **equals** the published `max_concurrency` - the reduction and
the series agreeing, which is the acceptance test's "one pass, one
truth".

**The stride, as a decision with a number.** A sample per endpoint is
two packets per process - 400,000 on a 200,000-process trace. The build
is bucketed into `COUNTER_WINDOWS` windows and each window contributes
its **maximum** and its closing value, so the cost is independent of
the build's size and the peak survives the stride exactly. Measured on
`examples/06`: 813 records, 1,626 raw endpoints, **538 samples**, and
the peak still 20.

**What it costs**, same snapshot, this tree against the commit before:

```text
              packets       raw        gzipped
before          2,338   348,014 B     58,150 B
after           2,877   361,521 B     61,561 B
                 +539   +13,507 B     +3,411 B
```

One packet per sample plus one for the track: 25.1 B a sample
uncompressed, 6.3 B compressed.
"""
import gzip
import hashlib
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from tools.bga_timeline import (  # noqa: E402
    CONCURRENCY_COUNTER, CONCURRENCY_UNIT, COUNTER_WINDOWS, DEFAULT_OUTPUT,
    FORMAT_TRACKEVENT, concurrency_series, render)
from tools.bst_native_build_tracer import (  # noqa: E402
    compute_max_concurrency, parse_trace_lines, stream_records,
    stream_trace_events)
from tools.native_trace import trackevent  # noqa: E402

from test_the_timeline_speaks_perfetto import _fields  # noqa: E402

REAL_CAPTURE = REPO / ("examples/06-macro-micro-optimization/.bga/runs/"
                       "20260821T170127Z")

# `examples/06`'s capture is real and **gitignored** - it exists on this
# machine and not in a clone. The measured figures below are taken from
# it and are worth having exactly, so the clauses that need it are
# skipped rather than deleted; every *property* they check is also
# checked on a committed fixture, so CI is not left believing something
# it never ran.
needs_real_capture = pytest.mark.skipif(
    not REAL_CAPTURE.is_dir(), reason="no real capture in this tree")



GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

# A shaped capture that carries every property this file asserts, so CI
# checks them without the gitignored one: overlapping processes so the
# curve rises above 1, a tie so the tie rule has something to decide, and
# an open record so the exclusion has something to exclude.
_SHAPED = [
    "START pid=2 ppid=1 ts=1000.0 element=e.bst inv=a src=spine cmd=sh",
    "START pid=3 ppid=1 ts=1000.1 element=e.bst inv=a src=spine cmd=cc0",
    "START pid=4 ppid=1 ts=1000.2 element=e.bst inv=a src=spine cmd=cc1",
    "END pid=4 ppid=1 ts=1000.4 element=e.bst inv=a src=spine exit=0 "
    "utime=0.01 stime=0.01 maxrss_kb=1024 cmd=cc1",
    "START pid=5 ppid=1 ts=1000.4 element=e.bst inv=a src=spine cmd=cc2",
    "END pid=3 ppid=1 ts=1000.5 element=e.bst inv=a src=spine exit=0 "
    "utime=0.01 stime=0.01 maxrss_kb=1024 cmd=cc0",
    "END pid=5 ppid=1 ts=1000.7 element=e.bst inv=a src=spine exit=0 "
    "utime=0.01 stime=0.01 maxrss_kb=1024 cmd=cc2",
    "END pid=2 ppid=1 ts=1000.9 element=e.bst inv=a src=spine exit=0 "
    "utime=0.01 stime=0.01 maxrss_kb=2048 cmd=sh",
    "START pid=6 ppid=1 ts=1000.8 element=e.bst inv=a src=spine cmd=never",
]

_SHAPED_LOG = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:e.bst] START Building
[wrapper][2026-08-21 12:00:02,100] INFO: [00:00:02][aaaaaaaa][   build:e.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:02,200] INFO: Return code: 0
"""


def _shaped_records():
    return list(stream_records(iter(parse_trace_lines(_SHAPED))))


def _shaped_snapshot(tmp_path):
    snapshot = tmp_path / "20260821T120000Z"
    snapshot.mkdir(parents=True)
    (snapshot / "build.log").write_text(_SHAPED_LOG, encoding="utf-8")
    shutil.copytree(GOLDEN, snapshot / "run")
    (snapshot / "run" / "expected_output.json").unlink(missing_ok=True)
    with gzip.open(snapshot / "plane2.log.gz", "wt", encoding="utf-8") as out:
        out.write("\n".join(_SHAPED) + "\n")
    return snapshot


def _records(path=REAL_CAPTURE / "plane2.log.gz"):
    with gzip.open(path, "rt", errors="ignore") as handle:
        return sorted(stream_records(stream_trace_events(handle)),
                      key=lambda record: record["start_ts"])


def _snapshot(tmp_path):
    snapshot = tmp_path / "20260821T170127Z"
    snapshot.mkdir(parents=True)
    shutil.copy(REAL_CAPTURE / "build.log", snapshot / "build.log")
    shutil.copy(REAL_CAPTURE / "plane2.log.gz", snapshot / "plane2.log.gz")
    shutil.copytree(REAL_CAPTURE / "run", snapshot / "run")
    return snapshot


def decode(path):
    """Counter tracks and their samples, from the wire."""
    raw = gzip.open(path, "rb").read()
    packets = [v for f, w, v in _fields(raw) if f == trackevent.TRACE_PACKET]
    counters, samples = {}, []
    for packet in packets:
        body = descriptor = timestamp = None
        for field, _wire, value in _fields(packet):
            if field == trackevent.PACKET_TRACK_EVENT:
                body = value
            elif field == trackevent.PACKET_TRACK_DESCRIPTOR:
                descriptor = value
            elif field == trackevent.PACKET_TIMESTAMP:
                timestamp = value
        if descriptor is not None:
            uuid = name = unit = unit_name = None
            for field, _wire, value in _fields(descriptor):
                if field == trackevent.TRACK_UUID:
                    uuid = value
                elif field == trackevent.TRACK_NAME:
                    name = value.decode("utf-8")
                elif field == trackevent.TRACK_COUNTER:
                    for inner, _w, payload in _fields(value):
                        if inner == trackevent.COUNTER_UNIT:
                            unit = payload
                        elif inner == trackevent.COUNTER_UNIT_NAME:
                            unit_name = payload.decode("utf-8")
            if unit is not None or unit_name is not None:
                counters[uuid] = {"name": name, "unit": unit,
                                  "unit_name": unit_name}
        if body is None:
            continue
        kind = track = value_seen = None
        for field, _wire, value in _fields(body):
            if field == trackevent.EVENT_TYPE:
                kind = value
            elif field == trackevent.EVENT_TRACK_UUID:
                track = value
            elif field == trackevent.EVENT_COUNTER_VALUE:
                value_seen = value
        if kind == trackevent.TYPE_COUNTER:
            samples.append({"track": track, "ts": timestamp,
                            "value": value_seen})
    return {"counters": counters, "samples": samples}


@pytest.fixture(scope="module")
def rendered(tmp_path_factory):
    if not REAL_CAPTURE.is_dir():
        pytest.skip("no real capture in this tree")
    tmp = tmp_path_factory.mktemp("counter")
    snapshot = _snapshot(tmp)
    out = tmp / DEFAULT_OUTPUT[FORMAT_TRACKEVENT]
    result = render(str(snapshot), str(out))
    return {"snapshot": snapshot, "path": out, "result": result,
            "trace": decode(out)}


class TestTheSeriesAndTheScalarAgree:

    @needs_real_capture
    def test_the_peak_equals_the_published_max_concurrency(self):
        """One pass, one truth. If the stride ever cost the peak, this
        is where it would show - and the stride is written to keep each
        window's maximum precisely so it cannot."""
        records = _records()
        series = concurrency_series(records)
        assert series
        assert max(value for _ts, value in series) == \
            compute_max_concurrency(records)

    @needs_real_capture
    def test_the_trace_carries_that_same_peak(self, rendered):
        records = _records()
        assert rendered["result"]["counter_peak"] == \
            compute_max_concurrency(records)
        values = [sample["value"] for sample in rendered["trace"]["samples"]]
        assert max(values) == compute_max_concurrency(records)

    def test_a_hand_folded_window_matches_the_series(self):
        """Four processes worked by hand, against the fold."""
        records = list(stream_records(iter(parse_trace_lines([
            "START pid=2 ppid=1 ts=10.0 element=e.bst inv=a cmd=a",
            "START pid=3 ppid=1 ts=11.0 element=e.bst inv=a cmd=b",
            "END pid=3 ppid=1 ts=12.0 element=e.bst inv=a utime=0.1 stime=0.1",
            "START pid=4 ppid=1 ts=11.5 element=e.bst inv=a cmd=c",
            "END pid=4 ppid=1 ts=13.0 element=e.bst inv=a utime=0.1 stime=0.1",
            "END pid=2 ppid=1 ts=14.0 element=e.bst inv=a utime=0.1 stime=0.1",
        ]))))
        series = concurrency_series(records, windows=0)
        assert series == [(10.0, 1), (11.0, 2), (11.5, 3), (12.0, 2),
                          (13.0, 1), (14.0, 0)]

    def test_a_start_exactly_as_another_ends_is_never_two(self):
        """The tie rule, taken from `compute_max_concurrency` rather
        than re-decided - a series that disagreed with the scalar about
        a tie would be a second answer to one question."""
        records = list(stream_records(iter(parse_trace_lines([
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a cmd=first",
            "END pid=2 ppid=1 ts=2.0 element=e.bst inv=a utime=0.1 stime=0.1",
            "START pid=3 ppid=1 ts=2.0 element=e.bst inv=a cmd=second",
            "END pid=3 ppid=1 ts=3.0 element=e.bst inv=a utime=0.1 stime=0.1",
        ]))))
        series = concurrency_series(records, windows=0)
        assert max(value for _ts, value in series) == 1
        assert compute_max_concurrency(records) == 1

    def test_an_open_record_is_excluded_from_the_curve_too(self):
        """It is excluded from the peak because its end is unknown; a
        curve that included it would be inventing one."""
        records = list(stream_records(iter(parse_trace_lines([
            "START pid=2 ppid=1 ts=1.0 element=e.bst inv=a cmd=never-exits",
            "START pid=3 ppid=1 ts=1.5 element=e.bst inv=a cmd=ordinary",
            "END pid=3 ppid=1 ts=2.5 element=e.bst inv=a utime=0.1 stime=0.1",
        ]))))
        assert max(v for _t, v in concurrency_series(records, windows=0)) == 1


class TestTheStrideIsBounded:

    @needs_real_capture
    def test_the_sample_count_cannot_grow_with_the_build(self):
        records = _records()
        assert len(records) == 813
        series = concurrency_series(records)
        assert len(series) == 538, len(series)
        assert len(series) <= 2 * COUNTER_WINDOWS + 2

    @needs_real_capture
    def test_a_tighter_stride_gives_fewer_samples_and_the_same_peak(self):
        """The stride is a knob with a measured effect, not a constant
        nobody has turned."""
        records = _records()
        peak = compute_max_concurrency(records)
        counts = []
        for windows in (10, 100, 1000):
            series = concurrency_series(records, windows=windows)
            counts.append(len(series))
            assert max(value for _ts, value in series) == peak, windows
        assert counts == sorted(counts), counts
        assert counts[0] < counts[-1], counts

    @needs_real_capture
    def test_the_timestamps_never_go_backwards(self, rendered):
        """Perfetto draws a step function; a sample behind the previous
        one is a step that is not one."""
        stamps = [sample["ts"] for sample in rendered["trace"]["samples"]]
        assert stamps == sorted(stamps)
        assert len(stamps) == rendered["result"]["counters"]


class TestTheTrackSaysWhatItCounts:

    @needs_real_capture
    def test_there_is_exactly_one_counter_track_and_it_names_its_unit(
            self, rendered):
        counters = rendered["trace"]["counters"]
        assert len(counters) == 1, counters
        (entry,) = counters.values()
        assert entry["name"] == CONCURRENCY_COUNTER
        assert entry["unit_name"] == CONCURRENCY_UNIT
        assert entry["unit"] == trackevent.UNIT_COUNT

    @needs_real_capture
    def test_there_is_no_memory_series(self, rendered):
        """The clause that records a refusal rather than an omission.

        `max_rss_kb` is a lifetime peak, not a sample. If a memory
        counter ever appears here, the question it has to answer first
        is what it sampled - and `compute_peak_memory`'s own docstring
        is the argument it has to beat."""
        names = {entry["name"] for entry in
                 rendered["trace"]["counters"].values()}
        assert not any("rss" in name.lower() or "mem" in name.lower()
                       for name in names), names

    @needs_real_capture
    def test_every_sample_is_on_that_track(self, rendered):
        tracks = {sample["track"] for sample in rendered["trace"]["samples"]}
        assert tracks == set(rendered["trace"]["counters"])


class TestWhatTheSeriesCosts:

    @needs_real_capture
    def test_it_is_one_packet_a_sample_and_one_for_the_track(
            self, tmp_path, monkeypatch):
        """The property, measured rather than remembered: the same
        capture rendered with the series and without it."""
        import tools.bga_timeline as timeline

        snapshot = _snapshot(tmp_path)
        out = tmp_path / "with.gz"
        withc = render(str(snapshot), str(out))
        with gzip.open(out, "rb") as handle:
            with_body = handle.read()

        monkeypatch.setattr(timeline, "concurrency_series", lambda *a, **k: [])
        bare = tmp_path / "without.gz"
        without = render(str(snapshot), str(bare))
        with gzip.open(bare, "rb") as handle:
            without_body = handle.read()

        assert without["counters"] == 0
        assert withc["counters"] == 538, withc["counters"]
        assert withc["packets"] - without["packets"] == withc["counters"] + 1
        per_sample = (len(with_body) - len(without_body)) / withc["counters"]
        assert 20.0 <= per_sample <= 30.0, per_sample

    @needs_real_capture
    def test_the_trace_is_the_same_trace_twice(self, tmp_path):
        snapshot = _snapshot(tmp_path)
        digests = []
        for index in (1, 2):
            out = tmp_path / f"trace-{index}.gz"
            render(str(snapshot), str(out))
            with gzip.open(out, "rb") as handle:
                digests.append(hashlib.sha256(handle.read()).hexdigest())
        assert digests[0] == digests[1]


class TestTheSameClaimsOnACommittedFixture:
    """Everything above, on a capture a clone actually has.

    The gitignored `examples/06` is where the *figures* come from; a
    guard whose only data is a path git does not track passes here and
    fails in CI before an assertion runs, which is what
    `test_a_guard_reads_only_what_a_clone_has.py` exists to catch - and
    did catch, on the first draft of this file.
    """

    def test_the_peak_equals_the_scalar_here_too(self):
        records = _shaped_records()
        series = concurrency_series(records)
        assert series
        assert max(value for _ts, value in series) == \
            compute_max_concurrency(records) == 3

    def test_the_open_record_is_out_of_both(self):
        records = _shaped_records()
        assert any(record["open"] for record in records), (
            "the fixture no longer has an open record, so the exclusion "
            "clause tests nothing")
        assert max(v for _t, v in concurrency_series(records, windows=0)) == 3

    def test_the_tie_is_resolved_the_scalars_way(self):
        """`cc1` ends at 1000.4 and `cc2` starts at 1000.4 - if the tie
        went the other way the peak would read 4."""
        records = _shaped_records()
        assert compute_max_concurrency(records) == 3
        assert max(v for _t, v in concurrency_series(records, windows=0)) == 3

    def test_a_tighter_stride_keeps_the_peak(self):
        records = _shaped_records()
        for windows in (1, 10, 1000):
            series = concurrency_series(records, windows=windows)
            assert max(v for _t, v in series) == 3, windows

    def test_the_trace_carries_one_counter_track_and_no_memory_one(
            self, tmp_path):
        snapshot = _shaped_snapshot(tmp_path)
        out = tmp_path / "trace.gz"
        result = render(str(snapshot), str(out))
        trace = decode(out)
        assert len(trace["counters"]) == 1, trace["counters"]
        (entry,) = trace["counters"].values()
        assert entry["name"] == CONCURRENCY_COUNTER
        assert entry["unit_name"] == CONCURRENCY_UNIT
        assert entry["unit"] == trackevent.UNIT_COUNT
        assert not any("rss" in (e["name"] or "").lower()
                       for e in trace["counters"].values())
        assert result["counter_peak"] == 3
        stamps = [sample["ts"] for sample in trace["samples"]]
        assert stamps == sorted(stamps)
        assert len(stamps) == result["counters"] > 0

    def test_a_flow_of_samples_costs_one_packet_each(self, tmp_path,
                                                     monkeypatch):
        import tools.bga_timeline as timeline

        snapshot = _shaped_snapshot(tmp_path)
        with_out = tmp_path / "with.gz"
        withc = render(str(snapshot), str(with_out))
        monkeypatch.setattr(timeline, "concurrency_series", lambda *a, **k: [])
        without_out = tmp_path / "without.gz"
        without = render(str(snapshot), str(without_out))
        assert without["counters"] == 0
        assert withc["packets"] - without["packets"] == withc["counters"] + 1
