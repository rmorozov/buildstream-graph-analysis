"""UX-45: real per-process CPU time from the Plane 2 hook's destructor.

Before this, `bga` had no CPU-time measurement anywhere - which is why I9
reconciliation is disabled on every real run and why three separate
report caveats have to say "this is occupancy, not CPU". The hook already
ran code in every traced process at exit; it just never called
`getrusage`.

Two properties matter as much as the measurement itself:

- an unmeasured CPU time and a genuinely-zero one are different claims,
  so a process that ran no destructor is counted as *unmeasured*, and a
  trace captured with the previous hook reports CPU as unavailable rather
  than as a confident 0.00s;
- coverage is always reported, because a per-element total that silently
  omits a fifth of its processes is worse than no total.
"""
from tools.bst_native_build_tracer import (
    compute_cpu_time,
    pair_events,
    parse_trace_log,
    summarize,
)


NEW = (
    "START pid=2 ppid=1 ts=100.0 element=core.bst cmd=cc1plus -c a.cpp\n"
    "END pid=2 ppid=1 ts=104.0 element=core.bst utime=3.500000 stime=0.250000 "
    "cutime=0.000000 cstime=0.000000 cmd=cc1plus -c a.cpp\n"
)

OLD = (
    "START pid=2 ppid=1 ts=100.0 element=core.bst cmd=cc1plus -c a.cpp\n"
    "END pid=2 ppid=1 ts=104.0 element=core.bst cmd=cc1plus -c a.cpp\n"
)


def test_cpu_time_is_parsed_from_the_end_line():
    events = parse_trace_log(NEW)
    end = [e for e in events if e["event"] == "END"][0]

    assert end["cpu_us"] == 3_750_000
    assert end["children_cpu_us"] == 0


def test_cmd_survives_the_new_fields():
    """The rusage fields sit between `element=` and `cmd=`, and `cmd=` is
    parsed as "everything after". A positional parser that did not know
    about the new fields would silently blank the command out."""
    events = parse_trace_log(NEW)

    assert all(e["cmd"] == "cc1plus -c a.cpp" for e in events)


def test_pre_ux45_trace_reports_unavailable_not_zero():
    report = summarize(pair_events(parse_trace_log(OLD)))

    assert report["cpu_time"]["available"] is False
    assert report["cpu_time"]["total_cpu_us"] == 0
    assert "before UX-45" in report["cpu_time"]["note"]


def test_pre_ux45_trace_still_parses_everything_else():
    # `UX-297`: the record is asserted where it now lives - the parse -
    # rather than in the report, which publishes the reductions over it.
    records = pair_events(parse_trace_log(OLD))
    report = summarize(records)

    assert report["process_count"] == 1
    assert records[0]["cmd"] == "cc1plus -c a.cpp"
    assert "cpu_us" not in records[0]


def test_per_element_totals_and_coverage():
    records = [
        {"element": "core.bst", "cmd": "cc1", "start_ts": 0.0, "end_ts": 4.0,
         "duration_s": 4.0, "open": False, "pid": 2, "ppid": 1, "cpu_us": 3_000_000},
        {"element": "core.bst", "cmd": "as", "start_ts": 1.0, "end_ts": 2.0,
         "duration_s": 1.0, "open": False, "pid": 3, "ppid": 2, "cpu_us": 1_000_000},
        # No `cpu_us`: exited abnormally, so unmeasured rather than zero.
        {"element": "core.bst", "cmd": "sh", "start_ts": 0.0, "end_ts": None,
         "duration_s": None, "open": True, "pid": 4, "ppid": 1},
    ]

    cpu = compute_cpu_time(records)
    entry = cpu["per_element"]["core.bst"]

    assert entry["cpu_us"] == 4_000_000
    assert entry["measured"] == 2 and entry["unmeasured"] == 1
    assert entry["coverage"] == 2 / 3
    assert cpu["measured_processes"] == 2
    assert cpu["unmeasured_processes"] == 1


def test_cores_busy_answers_cpu_bound_or_waiting():
    """The question the micro-optimization half of the walkthrough could
    not answer. 2s of CPU over a 4s span is half a core."""
    records = [
        {"element": "x.bst", "cmd": "cc1", "start_ts": 0.0, "end_ts": 4.0,
         "duration_s": 4.0, "open": False, "pid": 2, "ppid": 1, "cpu_us": 2_000_000},
    ]

    entry = compute_cpu_time(records)["per_element"]["x.bst"]

    assert entry["wall_span_s"] == 4.0
    assert entry["cpu_per_wall_second"] == 0.5


def test_children_cpu_is_tracked_separately_not_summed_in():
    """A parent's RUSAGE_CHILDREN already includes CPU its reaped
    children reported for themselves, so adding both would double-count.
    Self time is the additive quantity."""
    records = [
        {"element": "x.bst", "cmd": "make", "start_ts": 0.0, "end_ts": 4.0,
         "duration_s": 4.0, "open": False, "pid": 2, "ppid": 1,
         "cpu_us": 100_000, "children_cpu_us": 9_000_000},
    ]

    entry = compute_cpu_time(records)["per_element"]["x.bst"]

    assert entry["cpu_us"] == 100_000
    assert entry["children_cpu_us"] == 9_000_000


def test_partial_rusage_fields_are_not_reported_as_complete():
    """A truncated write could leave `utime=` without `stime=`. Half a
    pair must not be published as a measurement."""
    text = (
        "START pid=2 ppid=1 ts=100.0 element=a.bst cmd=cc1\n"
        "END pid=2 ppid=1 ts=104.0 element=a.bst utime=3.500000 cmd=cc1\n"
    )
    end = [e for e in parse_trace_log(text) if e["event"] == "END"][0]

    assert "cpu_us" not in end
    assert end["cmd"] == "cc1"


def test_unparseable_rusage_value_does_not_lose_the_command():
    text = (
        "START pid=2 ppid=1 ts=100.0 element=a.bst cmd=cc1 -c x.cpp\n"
        "END pid=2 ppid=1 ts=104.0 element=a.bst utime=NOTANUMBER cmd=cc1 -c x.cpp\n"
    )
    end = [e for e in parse_trace_log(text) if e["event"] == "END"][0]

    assert "cpu_us" not in end


def test_no_records_reports_unavailable():
    cpu = compute_cpu_time([])

    assert cpu["available"] is False
    assert cpu["per_element"] == {}
