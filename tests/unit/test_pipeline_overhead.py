"""Tests for P4-14: BuildStream's own top-level "main:core activity"
pipeline phases (Query cache, Resolving elements, Loading elements,
Initializing remote caches) are real work with a real elapsed cost -
confirmed material on a real ~2000-element fully-cached rebuild (Query
cache + Resolving elements were ~87% of total wall time there) - but were
previously invisible to bga entirely: tools/chrome_trace_to_bga_trace.py
already, deliberately, drops action="main" events as "not a real element
task". See docs/tasks/P4-14-cache-query-overhead-visibility.md.

Two layers:
1. WrapperTraceConverter's own extraction (tools/bst_log_to_chrome_trace.py) -
   fast, hermetic, uses real captured log text (see the module docstring's
   log excerpt in docs/ingestion-pipeline.md's fact 11).
2. Analyzer/report wiring (RunContext -> AnalysisResult -> text/json) -
   synthetic run dirs, same pattern as tests/unit/test_report_key_findings.py.
"""
import json

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text
from bga.report.json import format_json
from tools.bst_log_to_chrome_trace import WrapperTraceConverter

# A real, empirically captured log excerpt (BuildStream 2.7.0, default
# verbosity, no --verbose needed) - see docs/ingestion-pipeline.md's fact
# 11 and docs/tasks/P4-14-cache-query-overhead-visibility.md's Background.
# Elapsed values here are all 0 in the real capture (a trivial one-element
# project) - kept verbatim as the "real shape" test; a separate test below
# constructs a synthetic nonzero-elapsed case to check the arithmetic.
REAL_LOG_EXCERPT = """\
[--:--:--][        ][    main:core activity                 ] START   Build
[--:--:--][        ][    main:core activity                 ] START   Loading elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity                 ] START   Resolving elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Resolving elements
[--:--:--][        ][    main:core activity                 ] START   Initializing remote caches
[00:00:00][        ][    main:core activity                 ] SUCCESS Initializing remote caches
[--:--:--][        ][    main:core activity                 ] START   Query cache
[00:00:00][        ][    main:core activity                 ] SUCCESS Query cache
[00:00:00][        ][    main:core activity                 ] SUCCESS Build
"""


def _feed_raw(converter, text):
    for line in text.splitlines(keepends=True):
        converter.process_line_raw(line)
    converter.end_current_command(converter.last_known_ts)


def test_converter_extracts_the_four_real_phases():
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_LOG_EXCERPT)

    phases = [e["phase"] for e in converter.pipeline_overhead]
    assert phases == [
        "Loading elements",
        "Resolving elements",
        "Initializing remote caches",
        "Query cache",
    ]


def test_converter_excludes_the_outer_build_wrapper():
    """"Build" spans the entire invocation - redundant with the horizon
    bga already computes elsewhere, deliberately not recorded."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_LOG_EXCERPT)

    assert "Build" not in [e["phase"] for e in converter.pipeline_overhead]


def test_converter_does_not_emit_main_activity_as_a_trace_event():
    """Regression: action="main" events must never leak into
    trace_events/active_tasks (that's chrome_trace_to_bga_trace.py's own
    documented drop behavior for the *existing*, unrelated code path -
    this is a second, independent guarantee that the new side-channel
    doesn't accidentally also open spans for them)."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_LOG_EXCERPT)

    # raw mode synthesizes its own "bst (raw log)" bst-invocation B/E pair
    # (unrelated to main-activity handling) - the assertion is specifically
    # that no *bst-builder* span (the per-element span category) was opened
    # for any of the main-level pseudo-activities.
    assert [e for e in converter.trace_events if e["cat"] == "bst-builder"] == []
    assert converter.active_tasks == {}


def test_converter_computes_correct_nonzero_elapsed():
    """Synthetic (not real-captured) - checks the arithmetic specifically,
    independent of whether a real short build happens to round to zero at
    1-second elapsed precision (see docs/ingestion-pipeline.md fact 10).

    START lines show "--:--:--" (real BuildStream behavior - elapsed
    isn't known yet when an activity starts; see UX-06) - only the
    terminal line's own elapsed is real and used, applied on top of the
    watermark in effect when this specific activity's START was seen."""
    log = (
        "[--:--:--][        ][    main:core activity   ] START   Build\n"
        "[--:--:--][        ][    main:core activity   ] START   Query cache\n"
        "[00:00:02][        ][    main:core activity   ] SUCCESS Query cache\n"
        "[00:00:02][        ][    main:core activity   ] SUCCESS Build\n"
    )
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, log)

    assert converter.pipeline_overhead == [{"phase": "Query cache", "elapsed_us": 2_000_000}]


def test_converter_unmatched_terminal_status_is_ignored_defensively():
    """A terminal status with nothing open (e.g. a truncated log) must not
    raise - just silently produce no entry for the incomplete phase."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, "[00:00:00][        ][    main:core activity   ] SUCCESS Query cache\n")
    assert converter.pipeline_overhead == []


# --- Regression tests: `bst source track`/`bst source checkout`/`bst
# artifact checkout` also use action="main", but wrap differently than
# `bst build` does - real captured logs (BuildStream 2.7.0) surfaced two
# bugs the original P4-14 implementation had, both fixed here. -----------

# Real capture: `bst source track` on a one-element project with a real
# `kind: git` source (trimmed to the lines BST_LOG_RE matches).
REAL_TRACK_LOG_EXCERPT = """\
[--:--:--][        ][    main:core activity                 ] START   Track
[--:--:--][        ][    main:core activity                 ] START   Loading elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity                 ] START   Resolving elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Resolving elements
[--:--:--][????????][   track:thing.bst                     ] START   ci-flow-test/thing/????????-track.log
[--:--:--][????????][   track:thing.bst                     ] START   Tracking master from file:///srcrepo
[00:00:00][????????][   track:thing.bst                     ] SUCCESS Tracking master from file:///srcrepo
[00:00:00][????????][   track:thing.bst                     ] SUCCESS ci-flow-test/thing/????????-track.log
[00:00:00][        ][    main:core activity                 ] SUCCESS Track
"""


def test_track_wrapper_excluded_from_pipeline_overhead():
    """`bst source track` wraps its own pipeline-level phases in a "Track"
    bracket (not "Build") - the pre-fix code only excluded the literal
    string "Build", so "Track" would have been miscounted as if it were
    real, measurable overhead (it spans the entire invocation, same as
    "Build")."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_TRACK_LOG_EXCERPT)

    phases = [e["phase"] for e in converter.pipeline_overhead]
    assert "Track" not in phases
    assert phases == ["Loading elements", "Resolving elements"]


def test_track_wrapper_real_per_element_track_event_still_captured():
    """The real per-element `track:thing.bst` action (already a
    recognized TaskKind) must be unaffected by the "main" special-casing
    above it."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_TRACK_LOG_EXCERPT)

    builder_events = [e for e in converter.trace_events if e["cat"] == "bst-builder"]
    assert len(builder_events) == 2
    assert builder_events[0]["args"]["action"] == "track"
    assert builder_events[0]["args"]["element"] == "thing.bst"


# Real capture: `bst artifact checkout` on a one-element project (trimmed) -
# "Staging dependencies"/"Integrating sandbox"/"Checking out files in ..."
# are logged under action="main" but with the checked-out element's own
# *real* hash, not a blank one - confirmed against BuildStream 2.7.0's
# Stream.checkout() (`_prepare_sandbox()`/`_export_artifact()`, see
# docs/tasks/P4-15-stack-consolidation-heuristic.md's Background). `bst
# source checkout`'s "Staging sources" follows the identical pattern.
REAL_ARTIFACT_CHECKOUT_LOG_EXCERPT = """\
[--:--:--][        ][    main:core activity                 ] START   Loading elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity                 ] START   Query cache
[00:00:00][        ][    main:core activity                 ] SUCCESS Query cache
[--:--:--][c26a5e9e][    main:thing.bst                     ] START   Staging dependencies
[00:00:00][c26a5e9e][    main:thing.bst                     ] SUCCESS Staging dependencies
[--:--:--][c26a5e9e][    main:thing.bst                     ] START   Integrating sandbox
[00:00:00][c26a5e9e][    main:thing.bst                     ] SUCCESS Integrating sandbox
[--:--:--][c26a5e9e][    main:thing.bst                     ] START   Checking out files in '/out'
[00:00:00][c26a5e9e][    main:thing.bst                     ] SUCCESS Checking out files in '/out'
"""


def test_real_hash_scoped_main_events_not_swept_into_pipeline_overhead():
    """Regression: a real element hash under action="main" (checkout
    phases) must never land in the blank-hash-only pipeline_overhead
    bucket - it's genuinely per-element work, not pipeline-level."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_ARTIFACT_CHECKOUT_LOG_EXCERPT)

    phases = [e["phase"] for e in converter.pipeline_overhead]
    assert phases == ["Loading elements", "Query cache"]
    assert "Staging dependencies" not in phases
    assert "Integrating sandbox" not in phases


def test_real_hash_scoped_main_events_appear_as_builder_events_instead():
    """Falls through to the normal per-hash active_tasks path - three
    separate real B/E pairs, one per checkout phase, each attributable to
    the real element. (Not consumed by bga's core TaskKind pipeline at
    all - see tools/bst_checkout_cost.py, a deliberately separate,
    standalone tool, since a checkout invocation shares no horizon with a
    build trace.)"""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    _feed_raw(converter, REAL_ARTIFACT_CHECKOUT_LOG_EXCERPT)

    builder_events = [e for e in converter.trace_events if e["cat"] == "bst-builder"]
    phases = [e["args"].get("Message", e["name"]) for e in builder_events if e["ph"] == "E"]
    assert phases == ["Staging dependencies", "Integrating sandbox", "Checking out files in '/out'"]
    assert all(e["args"]["element"] == "thing.bst" for e in builder_events)
    assert all(e["args"]["action"] == "main" for e in builder_events)


# --- Analyzer / report wiring --------------------------------------------

def _write_run_dir(tmp_path, pipeline_overhead):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    run_context = {
        "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 20000,
        "pipeline_overhead": pipeline_overhead,
    }
    graph = {"elements": [{"uid": "a.bst", "requested_target": True}], "dependencies": []}
    trace = {
        "spans": [
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


@pytest.fixture
def result_with_overhead(tmp_path):
    run_dir = _write_run_dir(
        tmp_path,
        pipeline_overhead=[
            {"phase": "Resolving elements", "elapsed_us": 5000},
            {"phase": "Query cache", "elapsed_us": 2000},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


@pytest.fixture
def result_without_overhead(tmp_path):
    run_dir = _write_run_dir(tmp_path, pipeline_overhead=[])
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer.analyze()


def test_analysis_result_carries_totals_and_fraction(result_with_overhead):
    overhead = result_with_overhead.pipeline_overhead
    assert overhead["total_us"] == 7000
    assert overhead["phases"] == [
        {"phase": "Resolving elements", "elapsed_us": 5000},
        {"phase": "Query cache", "elapsed_us": 2000},
    ]
    # horizon here is the single 10000us task span, not wall_clock -
    # total_us (7000) / horizon_us (10000) = 0.7, exactly - no rounding
    # ambiguity to guard against.
    assert result_with_overhead.total_duration_us == 10000
    assert overhead["fraction_of_horizon"] == pytest.approx(0.7)


def test_text_report_includes_pipeline_overhead_section(result_with_overhead):
    output = format_text(result_with_overhead)
    assert "Pipeline Overhead (not attributable to individual elements):" in output
    assert "Resolving elements" in output
    assert "Query cache" in output
    assert "Total: 0.01s (70.0% of total duration)" in output


def test_text_report_omits_section_when_no_overhead_present(result_without_overhead):
    output = format_text(result_without_overhead)
    assert "Pipeline Overhead" not in output


def test_json_report_includes_pipeline_overhead_key(result_with_overhead):
    data = json.loads(format_json(result_with_overhead))
    assert data["pipeline_overhead"]["total_us"] == 7000
    assert data["pipeline_overhead"]["fraction_of_horizon"] == pytest.approx(0.7)


def test_json_report_omits_key_when_no_overhead_present(result_without_overhead):
    data = json.loads(format_json(result_without_overhead))
    assert "pipeline_overhead" not in data


def test_json_section_output_still_omits_pipeline_overhead(result_with_overhead):
    """pipeline_overhead is a full-report-only signal (section is None),
    same gating as structural/confidence/violations - a section-scoped
    request (e.g. --format json --section floors) must not carry it."""
    data = json.loads(format_json(result_with_overhead, section="floors"))
    assert "pipeline_overhead" not in data
