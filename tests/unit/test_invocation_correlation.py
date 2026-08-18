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
guessing*. `UX-64` then measured two things that reshaped it: a sandbox
must be matched on its **end**, because Plane 1's timestamps lag the
events they describe, and an element may host **several** sandboxes, so
resolving one must not strike its element from the others.
"""
from tools.bst_native_build_tracer import (
    apply_correlation,
    correlate_invocations,
    pair_events,
    parse_open_records,
    parse_trace_log,
)

def _inv(*pairs):
    return [{"invocation_id": i, "started_at": t} for i, t in pairs]


# --- resolving -----------------------------------------------------------


def test_a_sandbox_is_matched_on_its_end_not_its_start():
    """Measured, not chosen for tidiness. Plane 1 timestamps a line when
    the *wrapper reads* it, which lags the event: on a real traced build
    all 9 sandboxes began 0.18-0.46s BEFORE their element's logged BUILD
    START. Requiring the start inside the span left 7 of 9 unmatched.
    The end is the reliable edge - BuildStream cannot log a terminal
    status until the sandbox has finished."""
    spans = [{"element": "a.bst", "start": 10.0, "end": 20.0}]
    # Starts 0.5s before the span, as real sandboxes do.
    result = correlate_invocations(_inv((1, 9.5)), spans, durations={"1": 5.0})

    assert result["resolved"] == {"1": "a.bst"}


def test_a_sandbox_longer_than_its_span_still_matches():
    """The same lag makes the span systematically shorter than the
    sandbox, so 'no longer than its span' is not a safe test either:
    `app.bst`'s real sandbox ran 2.03s against a 1.62s span."""
    spans = [{"element": "app.bst", "start": 30.04, "end": 31.65}]

    result = correlate_invocations(_inv((1, 29.53)), spans, durations={"1": 2.03})

    assert result["resolved"] == {"1": "app.bst"}


def test_the_interval_discriminates_where_the_start_alone_cannot():
    """Two spans opening together, one short and one long. A start
    instant is inside both; the end separates them."""
    spans = [{"element": "short.bst", "start": 0.0, "end": 10.0},
             {"element": "long.bst", "start": 0.0, "end": 600.0}]

    assert correlate_invocations(_inv((1, 1.0)), spans)["ambiguous"] == ["1"]
    assert correlate_invocations(
        _inv((1, 1.0)), spans, durations={"1": 500.0}
    )["resolved"] == {"1": "long.bst"}


def test_what_cannot_be_deduced_is_reported_not_guessed():
    spans = [{"element": "a.bst", "start": 0.0, "end": 20.0},
             {"element": "b.bst", "start": 0.0, "end": 20.0}]

    result = correlate_invocations(_inv((1, 1.0)), spans, durations={"1": 5.0})

    assert result["resolved"] == {}
    assert result["ambiguous"] == ["1"]


def test_one_element_may_host_several_sandboxes():
    """The premise an earlier version leaned on, disproved on real data:
    `components/bison.bst` hosted two sandboxes 4.1s apart, and in one
    real build's first 54 seconds 15 sandboxes ran against at most 10
    concurrently-building elements. Resolving one sandbox must therefore
    NOT strike its element from the others - that does not merely
    under-resolve, it attributes to the wrong element."""
    spans = [{"element": "bison.bst", "start": 0.0, "end": 100.0}]

    result = correlate_invocations(
        _inv((1, 10.0), (2, 50.0)), spans, durations={"1": 5.0, "2": 5.0}
    )

    assert result["resolved"] == {"1": "bison.bst", "2": "bison.bst"}


def test_a_sandbox_outside_every_span_is_unmatched():
    spans = [{"element": "a.bst", "start": 0.0, "end": 10.0}]

    result = correlate_invocations(_inv((1, 90.0)), spans, durations={"1": 5.0})

    assert result["unmatched"] == ["1"]
    assert result["resolved"] == {}


def test_an_invocation_without_a_timestamp_is_unmatched_not_dropped():
    spans = [{"element": "a.bst", "start": 0.0, "end": 10.0}]

    assert correlate_invocations([{"invocation_id": 1}], spans)["unmatched"] == ["1"]


def test_no_spans_at_all_resolves_nothing():
    """A raw Plane 1 log yields no wall-clock spans (UX-06), and this
    must degrade to 'nothing resolved' rather than to a wrong answer."""
    result = correlate_invocations(_inv((1, 2.0)), [])

    assert result["resolved"] == {}
    assert result["unmatched"] == ["1"]


def test_whether_intervals_were_available_is_reported():
    """A reader should not have to infer whether they got a strong
    constraint or a weak one."""
    spans = [{"element": "a.bst", "start": 0.0, "end": 10.0}]

    assert correlate_invocations(_inv((1, 1.0)), spans)["intervals_used"] is False
    assert correlate_invocations(
        _inv((1, 1.0)), spans, durations={"1": 1.0}
    )["intervals_used"] is True


# --- sandbox durations ---------------------------------------------------


def test_a_sandbox_spans_all_of_its_own_processes():
    from tools.bst_native_build_tracer import sandbox_durations

    records = [
        {"invocation": "7", "start_ts": 10.0, "end_ts": 12.0},
        {"invocation": "7", "start_ts": 11.0, "end_ts": 18.0},
        {"invocation": "8", "start_ts": 20.0, "end_ts": 21.0},
    ]

    assert sandbox_durations(records) == {"7": 8.0, "8": 1.0}


def test_a_pre_ux56_record_contributes_no_duration():
    from tools.bst_native_build_tracer import sandbox_durations

    assert sandbox_durations([{"start_ts": 1.0, "end_ts": 2.0}]) == {}


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


# --- UX-80: the documented capture must produce the documented join ----


class _Args:
    def __init__(self, **kw):
        self.invocation_log = kw.get("invocation_log")
        self.no_invocation_log = kw.get("no_invocation_log", False)
        self.wrapped_log = kw.get("wrapped_log")


def test_a_wrapped_log_implies_an_invocation_record():
    """The defect `UX-80` was filed for: correlation ran only when both
    flags were passed, and `--invocation-log` appeared **zero times** in
    README.md, docs/cli.md and docs/real-project-guide.md - while the CI
    workflow that produced every number those documents quote did pass
    it. The documented command therefore could not produce the
    documented join on a project that overrides `build-root`."""
    from tools.bst_native_build_tracer import resolve_invocation_log_path

    path = resolve_invocation_log_path(_Args(wrapped_log="/tmp/plane1.log"))

    assert path and path.endswith("invocations.jsonl")


def test_an_explicit_path_is_honoured():
    from tools.bst_native_build_tracer import resolve_invocation_log_path

    args = _Args(wrapped_log="/tmp/plane1.log", invocation_log="/tmp/mine.jsonl")

    assert resolve_invocation_log_path(args) == "/tmp/mine.jsonl"


def test_no_wrapped_log_means_no_record():
    """Without Plane 1's timestamps there is nothing to correlate
    against, so recording invocations would buy nothing."""
    from tools.bst_native_build_tracer import resolve_invocation_log_path

    assert resolve_invocation_log_path(_Args()) is None


def test_the_opt_out_restores_the_old_behaviour():
    from tools.bst_native_build_tracer import resolve_invocation_log_path

    args = _Args(wrapped_log="/tmp/plane1.log", no_invocation_log=True)

    assert resolve_invocation_log_path(args) is None
