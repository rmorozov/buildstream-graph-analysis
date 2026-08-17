"""UX-63: measured peak RSS per element.

`UX-21` added a memory dimension to the oversubscription guard and had to
run it entirely on two operator-*declared* numbers, deferring measurement
because it "would need the same kind of intra-sandbox visibility" that
was hypothetical at the time. `UX-11` built that visibility and `UX-45`
put `getrusage` in the hook's destructor; `ru_maxrss` is one field of the
same struct.

The single most important property here is that peaks are **never
summed**. `ru_maxrss` is a per-process peak over that process's whole
lifetime, so two processes that each peaked at 500 MB at different
moments never held 1 GB between them. Summing them would manufacture a
concurrent total nothing measured — the same class of error as reading
occupancy as CPU (`UX-36`) or summing per-element redundancy savings
(`UX-37`).
"""
from tools.bst_native_build_tracer import (
    compute_peak_memory,
    pair_events,
    parse_trace_log,
)

TRACE = (
    "START pid=10 ppid=1 ts=1.0 element=core.bst cmd=/usr/bin/cc a.c\n"
    "END pid=10 ppid=1 ts=2.0 element=core.bst utime=0.5 stime=0.1"
    " cutime=0.0 cstime=0.0 maxrss_kb=512000 cmaxrss_kb=0 cmd=/usr/bin/cc a.c\n"
    "START pid=11 ppid=1 ts=3.0 element=core.bst cmd=/usr/bin/cc b.c\n"
    "END pid=11 ppid=1 ts=4.0 element=core.bst utime=0.5 stime=0.1"
    " cutime=0.0 cstime=0.0 maxrss_kb=500000 cmaxrss_kb=0 cmd=/usr/bin/cc b.c\n"
)


def _records(text):
    return pair_events(parse_trace_log(text))


def test_the_peak_is_the_largest_process_not_the_sum():
    """The two processes peaked at 512 MB and 500 MB at *different*
    moments (1-2s and 3-4s), so they never held 1012 MB together."""
    result = compute_peak_memory(_records(TRACE))

    assert result["per_element"]["core.bst"]["peak_rss_kb"] == 512000
    assert result["per_element"]["core.bst"]["peak_rss_kb"] != 512000 + 500000


def test_the_note_says_it_must_not_be_summed():
    """A per-element list under a 'Peak Memory' heading reads as a
    concurrent total unless it says otherwise."""
    result = compute_peak_memory(_records(TRACE))

    assert "NOT summed" in result["note"] or "not summed" in result["note"]


def test_coverage_is_reported_not_assumed():
    """A process killed before its destructor ran contributes nothing,
    and saying how many is the difference between a measurement and a
    guess (the rule UX-45 established)."""
    killed = TRACE + "START pid=12 ppid=1 ts=5.0 element=core.bst cmd=/bin/sh\n"

    entry = compute_peak_memory(_records(killed))["per_element"]["core.bst"]

    assert entry["measured"] == 2
    assert entry["unmeasured"] == 1


def test_a_pre_ux63_trace_is_unavailable_not_zero():
    """Every capture taken before this shipped omits the field, and a
    zero would read as 'this build used no memory'."""
    old = (
        "START pid=10 ppid=1 ts=1.0 element=core.bst cmd=/usr/bin/cc a.c\n"
        "END pid=10 ppid=1 ts=2.0 element=core.bst utime=0.5 stime=0.1"
        " cutime=0.0 cstime=0.0 cmd=/usr/bin/cc a.c\n"
    )

    result = compute_peak_memory(_records(old))

    assert result["available"] is False
    assert "peak RSS" in result["note"]


def test_the_field_survives_start_end_pairing():
    """`pair_events` builds a fresh record and copies only named keys, so
    a field added to the hook is silently dropped unless it is copied
    here too - which is exactly what happened on the first attempt."""
    record = next(r for r in _records(TRACE) if r["pid"] == 10)

    assert record["max_rss_kb"] == 512000
    assert record["children_max_rss_kb"] == 0


def test_elements_are_kept_separate():
    two = TRACE + (
        "START pid=20 ppid=1 ts=1.0 element=app.bst cmd=/usr/bin/ld\n"
        "END pid=20 ppid=1 ts=2.0 element=app.bst utime=0.1 stime=0.1"
        " cutime=0.0 cstime=0.0 maxrss_kb=100 cmaxrss_kb=0 cmd=/usr/bin/ld\n"
    )

    per_element = compute_peak_memory(_records(two))["per_element"]

    assert per_element["core.bst"]["peak_rss_kb"] == 512000
    assert per_element["app.bst"]["peak_rss_kb"] == 100
