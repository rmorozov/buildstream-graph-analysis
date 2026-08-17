"""UX-61: `max_concurrency` reported 5,268 on a 4-core runner.

The cause was not the unterminated processes the metric already excludes.
It was `pair_events` keying START/END on `(element, pid)`. Pids inside a
bwrap sandbox are **namespaced**, so they collide freely across
sandboxes; the element name was doing all the disambiguating, and under a
project-wide `build-root` override every process shares one name
(`UX-56`). A START in one sandbox then pairs with an END in another.

Measured on a real collapsed capture of `examples/06`: 822 records over
**113 distinct pids** across 9 sandboxes, paired "durations" of 23.48s
inside a ~30s build, and `max_concurrency` 34 on a `--builders 4
--max-jobs 4` run. Keying on the sandbox id instead: longest duration
8.63s (the real `core.bst` build) and concurrency 20 — which is
believable for 4 builders x 4 jobs plus their shell and `make` wrappers.

So this was a symptom of `UX-56` rather than an independent defect, and
`UX-56`'s sandbox id is what fixes it.
"""
from tools.bst_native_build_tracer import (
    compute_max_concurrency,
    pair_events,
    parse_trace_log,
)

# Two sandboxes, both with a process at pid 5, running at the same time -
# the exact shape that collides once the element name collapses.
COLLAPSED = (
    "START pid=5 ppid=1 ts=1.0 element=buildstream-build inv=100 cmd=/usr/bin/cc a.c\n"
    "START pid=5 ppid=1 ts=2.0 element=buildstream-build inv=200 cmd=/usr/bin/cc b.c\n"
    "END pid=5 ppid=1 ts=3.0 element=buildstream-build inv=100 cmd=/usr/bin/cc a.c\n"
    "END pid=5 ppid=1 ts=4.0 element=buildstream-build inv=200 cmd=/usr/bin/cc b.c\n"
)


def test_colliding_pids_are_paired_within_their_own_sandbox():
    records = {r["invocation"]: r for r in pair_events(parse_trace_log(COLLAPSED))}

    assert records["100"]["start_ts"] == 1.0 and records["100"]["end_ts"] == 3.0
    assert records["200"]["start_ts"] == 2.0 and records["200"]["end_ts"] == 4.0


def test_the_element_name_is_no_longer_load_bearing():
    """Every process here carries the same collapsed name, and the
    pairing is still correct - which is the whole point."""
    records = pair_events(parse_trace_log(COLLAPSED))

    assert {r["element"] for r in records} == {"buildstream-build"}
    assert all(not r["open"] for r in records)
    assert sorted(r["end_ts"] - r["start_ts"] for r in records) == [2.0, 2.0]


def test_a_pre_ux56_capture_falls_back_to_the_element_name():
    """No `inv=` field at all. Keying on the element is what this always
    did, and it is still correct whenever the element name is real."""
    old = (
        "START pid=5 ppid=1 ts=1.0 element=a.bst cmd=/usr/bin/cc a.c\n"
        "START pid=5 ppid=1 ts=2.0 element=b.bst cmd=/usr/bin/cc b.c\n"
        "END pid=5 ppid=1 ts=3.0 element=a.bst cmd=/usr/bin/cc a.c\n"
        "END pid=5 ppid=1 ts=4.0 element=b.bst cmd=/usr/bin/cc b.c\n"
    )

    records = {r["element"]: r for r in pair_events(parse_trace_log(old))}

    assert records["a.bst"]["end_ts"] == 3.0
    assert records["b.bst"]["end_ts"] == 4.0


def test_mispairing_inflates_concurrency_and_correct_pairing_does_not():
    """The reported symptom, in miniature: two 2-second processes that
    overlap by one second. Correct pairing sees 2 concurrent; the
    cross-sandbox mispairing this replaced would stretch one interval
    across the other and still see 2 - so the test that matters is the
    duration, which is what actually inflated at scale."""
    records = pair_events(parse_trace_log(COLLAPSED))

    assert compute_max_concurrency(records) == 2
    assert max(r["end_ts"] - r["start_ts"] for r in records) == 2.0


def test_unterminated_processes_are_still_excluded():
    """The exclusion the metric always documented, unchanged - it was
    never the cause, and removing it would be the wrong fix."""
    text = COLLAPSED + "START pid=9 ppid=1 ts=1.5 element=buildstream-build inv=100 cmd=/bin/sh\n"

    records = pair_events(parse_trace_log(text))

    assert any(r["open"] for r in records)
    assert compute_max_concurrency(records) == 2
