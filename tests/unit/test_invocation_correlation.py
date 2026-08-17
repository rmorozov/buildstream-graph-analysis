"""UX-56: recover collapsed element names by correlating sandboxes with
Plane 1's BUILD spans.

Plane 2 tags each process with bwrap's `--dir` last segment, which is the
build root. Under BuildStream's default per-element layout that *is* the
element; under a project-wide override — `freedesktop-sdk` uses
`build-root: /buildstream-build` — every element collapses into one
bucket. Measured on the real capture: 126,890 of 127,630 processes
(99.4%). A local reproduction of the same one-line override collapses
234 of 234.

Two candidate sources were ruled out by measurement first: the bwrap argv
carries the element only through the build root, three times over, so an
overriding project loses all three together; and the shim's ancestry is
`buildbox-run` → the `bst` main process, with no per-element job to read
a name from.

What remains is correlation, and the discipline it needs is *not
guessing*. Under `--builders N` several BUILD spans overlap, so this
resolves only what is forced — an element hosts at most one sandbox, so a
single-candidate invocation claims it and thereby constrains the others —
and reports the rest rather than picking a likely answer.
"""
from tools.bst_native_build_tracer import (
    apply_correlation,
    correlate_invocations,
    pair_events,
    parse_open_records,
    parse_trace_log,
)

SPANS = [
    {"element": "a.bst", "start": 0.0, "end": 10.0},
    {"element": "b.bst", "start": 5.0, "end": 20.0},
]


def _inv(*pairs):
    return [{"invocation_id": i, "started_at": t} for i, t in pairs]


# --- resolving -----------------------------------------------------------


def test_a_uniquely_contained_sandbox_is_certain():
    result = correlate_invocations(_inv((1, 2.0)), SPANS)

    assert result["resolved"] == {"1": "a.bst"}
    assert result["certain"] == 1
    assert result["deduced"] == 0


def test_an_overlapping_sandbox_is_resolved_by_elimination():
    """The invocation at t=7 sits inside both spans. It is not guessed:
    the one at t=2 can only be `a.bst`, which removes `a.bst` from the
    other's candidates and forces `b.bst`."""
    result = correlate_invocations(_inv((1, 2.0), (2, 7.0)), SPANS)

    assert result["resolved"] == {"1": "a.bst", "2": "b.bst"}
    assert result["certain"] == 1
    assert result["deduced"] == 1


def test_what_cannot_be_deduced_is_reported_not_guessed():
    """Two sandboxes, both inside both spans. Either assignment is
    consistent, so neither is made - UX-46 already refuses to judge a
    truncated read set, and a mis-attributed one is worse than a missing
    one."""
    result = correlate_invocations(_inv((1, 7.0), (2, 8.0)), SPANS)

    assert result["resolved"] == {}
    assert result["ambiguous"] == ["1", "2"]


def test_a_contradiction_is_reported_separately_from_ambiguity():
    """Two sandboxes that both had to be `a.bst` means the
    one-sandbox-per-element premise failed for this capture - which
    invalidates the method here, where ambiguity only limits its reach.
    Conflating them would hide that."""
    result = correlate_invocations(_inv((1, 2.0), (2, 3.0)), SPANS)

    assert result["conflicting"] == ["2"]
    assert result["ambiguous"] == []


def test_a_sandbox_outside_every_span_is_unmatched():
    """A sandbox that belongs to no BUILD span at all - a fetch, or two
    planes that do not cover the same window."""
    result = correlate_invocations(_inv((1, 99.0)), SPANS)

    assert result["unmatched"] == ["1"]
    assert result["resolved"] == {}


def test_an_invocation_without_a_timestamp_is_unmatched_not_dropped():
    result = correlate_invocations([{"invocation_id": 1}], SPANS)

    assert result["unmatched"] == ["1"]


def test_no_spans_at_all_resolves_nothing():
    """A raw Plane 1 log yields no wall-clock spans (UX-06), and this
    must degrade to 'nothing resolved' rather than to a wrong answer."""
    result = correlate_invocations(_inv((1, 2.0)), [])

    assert result["resolved"] == {}
    assert result["unmatched"] == ["1"]


# --- applying ------------------------------------------------------------


TRACE = (
    "START pid=5 ppid=1 ts=1.0 element=buildstream-build inv=900 cmd=/usr/bin/cc a.c\n"
    "END pid=5 ppid=1 ts=2.0 element=buildstream-build inv=900"
    " utime=0.1 stime=0.0 cutime=0.0 cstime=0.0 maxrss_kb=10 cmaxrss_kb=0 cmd=/usr/bin/cc a.c\n"
)


def test_resolving_one_sandbox_relabels_every_process_in_it():
    """The property that makes this worth doing: one correlated
    invocation fixes every process that ran inside it, however many."""
    records = pair_events(parse_trace_log(TRACE))

    relabelled = apply_correlation(records, {"900": "core.bst"})

    assert relabelled == 1
    assert records[0]["element"] == "core.bst"


def test_an_unresolved_sandbox_keeps_its_collapsed_name():
    """Never overwritten with a guess, and never blanked - the collapsed
    name is still what was observed."""
    records = pair_events(parse_trace_log(TRACE))

    assert apply_correlation(records, {}) == 0
    assert records[0]["element"] == "buildstream-build"


def test_open_records_are_relabelled_too():
    """Declared-vs-used is keyed on this name, and leaving OPENS blocks
    uncorrected is exactly how UX-46 came back entirely empty on the real
    freedesktop-sdk capture."""
    text = "OPENS pid=5 element=buildstream-build inv=900 unique=1 dropped=0 part=0\n/usr/include/x.h\n"

    corrected = parse_open_records(text, open_element_overrides={"900": "core.bst"})

    assert set(corrected) == {"core.bst"}
    assert corrected["core.bst"]["paths"] == {"/usr/include/x.h"}


def test_a_pre_ux56_capture_still_parses_everywhere():
    """No `inv=` field at all - the correction is simply unavailable, and
    nothing else may change."""
    old_trace = "START pid=5 ppid=1 ts=1.0 element=core.bst cmd=/usr/bin/cc a.c\n"
    old_opens = "OPENS pid=5 element=core.bst unique=1 dropped=0 part=0\n/usr/include/x.h\n"

    assert parse_trace_log(old_trace)[0]["invocation"] is None
    assert set(parse_open_records(old_opens)) == {"core.bst"}


def test_the_hook_emits_none_rather_than_omitting_the_field():
    """A sandbox created without the id (an older shim against a newer
    hook) reads back as absent, not as a sandbox called 'none'."""
    text = "START pid=5 ppid=1 ts=1.0 element=core.bst inv=none cmd=/bin/sh\n"

    assert parse_trace_log(text)[0]["invocation"] is None
