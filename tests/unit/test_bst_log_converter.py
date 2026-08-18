"""Tests for P4-05 (tools/bst_log_to_chrome_trace.py raw-log support) and
two real bugs found while implementing it, confirmed against a real,
installed BuildStream 2.7.0 (see docs/spec/ingestion-pipeline.md):

1. The status-word alternation never matched a real build failure at all,
   in either wrapped or raw mode - real BuildStream emits "FAILURE", not
   "FAIL" (the synthetic fixture never exercises a failing build, so this
   went uncaught).
2. A real BuildStream task (e.g. one `build:` action) emits an *outer*
   START/terminal-status bracket plus one or more *nested* START/terminal
   pairs for internal sub-phases ("Staging sources", "Caching artifact"),
   all sharing the identical hash+action key. The pre-existing
   "force-close previous, open new" handling on every START would have
   produced 2-3 spurious short spans per real build task instead of one
   correct one - a real correctness bug for real logs, invisible against
   the synthetic fixture (which never nests). Fixed via per-(hash,action)
   depth counting.
"""

import pytest

from tools.bst_log_to_chrome_trace import (
    WrapperTraceConverter,
    parse_elapsed_to_seconds,
    _resolve_start_time_us,
    TARGETS_RE,
)


def _builder_events(converter):
    return [e for e in converter.trace_events if e.get("cat") == "bst-builder"]


# --- Raw-log parsing: real captured line shapes -------------------------

# Real lines captured from `bst -C tests/fixtures/bst_show_project build
# app.bst` against BuildStream 2.7.0 (see docs/spec/ingestion-pipeline.md) -
# the outer bracket's message is a logfile path, nested sub-phases use
# short human phrases, both sharing the same hash+action key.
REAL_BUILD_TASK_LINES = [
    "[--:--:--][4a9059d4][   build:base.bst                      ] START   bst-show-test-project/base/4a9059d4-build.log",
    "[--:--:--][4a9059d4][   build:base.bst                      ] START   Staging sources",
    "[00:00:00][4a9059d4][   build:base.bst                      ] SUCCESS Staging sources",
    "[--:--:--][4a9059d4][   build:base.bst                      ] START   Caching artifact",
    "[00:00:00][4a9059d4][   build:base.bst                      ] SUCCESS Caching artifact",
    "[00:00:00][4a9059d4][   build:base.bst                      ] SUCCESS bst-show-test-project/base/4a9059d4-build.log",
]


def test_raw_nested_subphases_produce_exactly_one_span_not_several():
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in REAL_BUILD_TASK_LINES:
        converter.process_line_raw(line)

    builder = _builder_events(converter)
    begins = [e for e in builder if e["ph"] == "B"]
    ends = [e for e in builder if e["ph"] == "E"]

    assert len(begins) == 1
    assert len(ends) == 1
    assert begins[0]["args"]["action"] == "build"
    # The E event's Status/Message reflect the *outer* (final, depth-0)
    # terminal event, not any of the nested sub-phase terminals.
    assert ends[0]["args"]["Status"] == "SUCCESS"
    assert ends[0]["args"]["Message"] == "bst-show-test-project/base/4a9059d4-build.log"


def test_raw_task_with_only_outer_bracket_no_nesting_still_works():
    """A fetch task (confirmed against a real build: no nested sub-phases
    for fetch, unlike build) - regression, must still open/close exactly
    once."""
    lines = [
        "[--:--:--][4a9059d4][   fetch:base.bst                      ] START   bst-show-test-project/base/4a9059d4-fetch.log",
        "[00:00:00][4a9059d4][   fetch:base.bst                      ] SUCCESS bst-show-test-project/base/4a9059d4-fetch.log",
    ]
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in lines:
        converter.process_line_raw(line)

    builder = _builder_events(converter)
    assert len([e for e in builder if e["ph"] == "B"]) == 1
    assert len([e for e in builder if e["ph"] == "E"]) == 1


def test_raw_failure_status_word_recognized():
    """Real bug: the original status alternation had "FAIL", not
    "FAILURE" - a real build failure would silently produce zero E event
    (the task stays "active" forever). Confirmed against a real failing
    build (BuildStream 2.7.0)."""
    lines = [
        "[--:--:--][a0312885][   build:broken.bst                    ] START   fail-test-project/broken/a0312885-build.log",
        "[--:--:--][a0312885][   build:broken.bst                    ] START   Running commands",
        "[00:00:00][a0312885][   build:broken.bst                    ] FAILURE Running commands",
        "[00:00:00][a0312885][   build:broken.bst                    ] FAILURE Staged artifacts do not provide command 'sh'",
    ]
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in lines:
        converter.process_line_raw(line)

    builder = _builder_events(converter)
    ends = [e for e in builder if e["ph"] == "E"]
    assert len(ends) == 1
    assert ends[0]["args"]["Status"] == "FAILURE"
    assert ends[0]["args"]["Message"] == "Staged artifacts do not provide command 'sh'"


def test_raw_mode_opens_a_synthetic_bst_invocation_span():
    """Raw logs have no wrapper 'Executing command:' line to trigger
    is_bst - the whole raw log is one continuous invocation by
    definition, needed so run-context wall_clock derivation (P4-09) works
    identically for raw and wrapped logs."""
    converter = WrapperTraceConverter(raw_start_time_us=1_000_000)
    converter.process_line_raw(REAL_BUILD_TASK_LINES[0])
    converter.end_current_command(converter.last_known_ts)

    invocations = [e for e in converter.trace_events if e.get("cat") == "bst-invocation"]
    assert any(e["ph"] == "B" for e in invocations)
    assert any(e["ph"] == "E" for e in invocations)


def test_scheduler_config_parsed_from_maximum_tasks_header_lines():
    """Real BuildStream prints its already-resolved (CLI-flag-or-default)
    scheduler limits unconditionally, as standalone lines in its summary
    header (confirmed against a real build - no [hash][action:element]
    bracket structure at all, unlike per-task log lines) - a more robust
    source than re-parsing --builders/--fetchers/--pushers CLI flags
    ourselves (see docs/spec/ingestion-pipeline.md)."""
    lines = [
        "    Maximum Fetch Tasks:     7",
        "    Maximum Build Tasks:     3",
        "    Maximum Push Tasks:      2",
    ]
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in lines:
        converter.process_line_raw(line)

    config = converter.get_scheduler_config()
    assert config == {
        "builders": 3, "fetchers": 7, "pushers": 2,
        # UX-29: BuildStream's own header never reports --max-jobs, and a
        # raw log has no wrapper invocation line to recover it from -
        # "not recorded", never a fabricated default.
        "native_max_jobs": None,
    }


def test_scheduler_config_parsed_in_wrapped_mode_too():
    """The same standalone header lines, as they'd appear wrapped by a CI
    tool (which wraps every line of bst's stdout, header included)."""
    converter = WrapperTraceConverter()
    converter.process_line_wrapped(
        "[wrapper][2026-08-14 11:00:00,000] INFO: Maximum Build Tasks:     3"
    )
    assert converter.get_scheduler_config()["builders"] == 3


def test_scheduler_config_defaults_match_buildstream_bundled_defaults():
    """No header lines seen at all - falls back to BuildStream's own
    bundled userconfig.yaml defaults (confirmed against a real install:
    fetchers=10, builders=4, pushers=4), not an invented guess."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    assert converter.get_scheduler_config() == {
        "builders": 4, "fetchers": 10, "pushers": 4,
        # UX-29: no invocation line parsed, so "not recorded" - never a
        # fabricated default.
        "native_max_jobs": None,
    }


# --- Wrapped-mode regression (must be entirely unaffected) --------------

def test_wrapped_mode_still_works_and_ignores_raw_only_state():
    """Regression: --format wrapped (or auto's wrapped branch) must
    behave exactly as before - the elapsed bracket is parsed but unused,
    the wrapper's own UTC timestamp is the only time source."""
    converter = WrapperTraceConverter()
    converter.process_line_wrapped(
        "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build base.bst"
    )
    converter.process_line_wrapped(
        "[wrapper][2026-08-14 11:00:00,100] INFO: "
        "[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log"
    )
    converter.process_line_wrapped(
        "[wrapper][2026-08-14 11:00:00,200] INFO: "
        "[00:00:00][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log"
    )
    converter.end_current_command(converter.last_known_ts)

    builder = _builder_events(converter)
    begins = [e for e in builder if e["ph"] == "B"]
    ends = [e for e in builder if e["ph"] == "E"]
    assert len(begins) == 1 and len(ends) == 1
    expected_begin = converter.parse_timestamp("2026-08-14 11:00:00,100")
    expected_end = converter.parse_timestamp("2026-08-14 11:00:00,200")
    assert begins[0]["ts"] == expected_begin
    assert ends[0]["ts"] == expected_end


def test_auto_format_detects_wrapped_and_raw_lines_independently():
    converter = WrapperTraceConverter(raw_start_time_us=0)
    # A wrapped line and a raw line, mixed - auto must handle both.
    converter.process_line(
        "[wrapper][2026-08-14 11:00:00,000] INFO: Executing command: bst build base.bst"
    )
    converter.process_line(
        "[wrapper][2026-08-14 11:00:00,100] INFO: "
        "[--:--:--][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log"
    )
    converter.process_line(
        "[wrapper][2026-08-14 11:00:00,200] INFO: "
        "[00:00:00][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log"
    )
    converter.end_current_command(converter.last_known_ts)

    builder = _builder_events(converter)
    assert len([e for e in builder if e["ph"] == "B"]) == 1
    assert len([e for e in builder if e["ph"] == "E"]) == 1


# --- Elapsed-time parsing -------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("00:00:00", 0.0),
    ("00:01:05", 65.0),
    ("01:02:03", 3723.0),
    ("00:00:01.500000", 1.5),
    ("--:--:--", 0.0),
    ("--:--:--.------", 0.0),
])
def test_parse_elapsed_to_seconds(raw, expected):
    assert parse_elapsed_to_seconds(raw) == expected


def test_parse_elapsed_to_seconds_rejects_garbage():
    assert parse_elapsed_to_seconds("not-a-time") is None


def test_raw_mode_anchors_a_tasks_first_start_to_the_current_watermark():
    """UX-06: a START event always anchors to "now" (the running
    watermark) - never to its own elapsed value. Real BuildStream START
    lines always show "--:--:--" anyway (elapsed isn't known yet); this
    synthetic line's own nonzero elapsed [00:00:05] is deliberately
    ignored, matching real semantics (see _process_raw_line's docstring
    and docs/backlog/scenarios/UX-06-raw-log-timestamp-corruption.md)."""
    converter = WrapperTraceConverter(raw_start_time_us=1_700_000_000_000_000)
    converter.process_line_raw(
        "[00:00:05][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log"
    )
    begin = _builder_events(converter)[0]
    assert begin["ts"] == 1_700_000_000_000_000


def test_raw_mode_applies_a_terminals_own_elapsed_to_its_tasks_anchor():
    """The closing (terminal) line of a task's outer bracket applies its
    own real elapsed on top of that task's own START anchor - this is
    the one raw-mode timestamp that must reflect the line's elapsed
    value, since it's what makes the task's real measured duration
    survive into the reconstructed timeline."""
    converter = WrapperTraceConverter(raw_start_time_us=1_700_000_000_000_000)
    converter.process_line_raw(
        "[--:--:--][4a9059d4][   build:base.bst] START   Running commands"
    )
    converter.process_line_raw(
        "[00:00:05][4a9059d4][   build:base.bst] SUCCESS base/4a9059d4-build.log"
    )
    end = _builder_events(converter)[-1]
    assert end["ph"] == "E"
    assert end["ts"] == 1_700_000_000_000_000 + 5_000_000


def test_raw_mode_requires_start_time():
    converter = WrapperTraceConverter(raw_start_time_us=None)
    with pytest.raises(ValueError):
        converter.process_line_raw(
            "[00:00:00][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log"
        )


# --- --start-time resolution ---------------------------------------------

def test_resolve_start_time_us_from_explicit_iso8601():
    us = _resolve_start_time_us("2026-08-14T00:00:00+00:00", "/nonexistent")
    assert us == 1786665600_000_000


def test_resolve_start_time_us_defaults_to_file_mtime(tmp_path):
    log_file = tmp_path / "raw.log"
    log_file.write_text("hello\n")
    us = _resolve_start_time_us(None, str(log_file))
    assert us > 0


# --- Targets: header line (used by tools/bst_extract_run.py, P4-10) -----

def test_targets_regex_matches_real_header_line():
    m = TARGETS_RE.match("    Targets:       base.bst, base2.bst")
    assert m.group(1) == "base.bst, base2.bst"


def test_targets_captured_during_raw_processing():
    converter = WrapperTraceConverter(raw_start_time_us=0)
    converter.process_line_raw("    Targets:       app.bst")
    assert converter.targets == "app.bst"


def test_targets_captured_during_wrapped_processing():
    converter = WrapperTraceConverter()
    converter.process_line_wrapped(
        "[wrapper][2026-08-14 11:00:00,000] INFO: Targets:       base.bst, base2.bst"
    )
    assert converter.targets == "base.bst, base2.bst"


# --- UX-06: raw-log cross-task timestamp reconstruction ------------------
#
# A third real bug, found while building examples/04-critical-path-
# optimization for a later, real optimization walkthrough (see
# docs/backlog/scenarios/UX-06-raw-log-timestamp-corruption.md): BuildStream's own
# `[HH:MM:SS]` elapsed prefix resets to zero at the start of *every*
# individual timed activity (confirmed against the real installed
# BuildStream 2.7.0 source, buildstream/_messenger.py's `timed_activity`)
# - not once per session. `_process_raw_line` previously anchored every
# line to the *same* single session-start timestamp, so any task starting
# after the first one collapsed toward the start of the file regardless
# of when it really ran - real evidence: a downstream task depending on a
# 4-second upstream task showed the *same* `[00:00:00]` elapsed its
# upstream showed at its own start, despite starting a real 4 seconds
# later.

# core.bst takes 4 real seconds (three sub-phases, "Running commands" is
# the slow one); lib.bst depends on core.bst and only starts once core.bst
# genuinely finishes - real shape captured from examples/04-critical-path-
# optimization's own build (see docs/backlog/scenarios/UX-06's Motivation section).
_UPSTREAM_THEN_DOWNSTREAM_LINES = [
    "[--:--:--][aaaaaaaa][   build:core.bst                      ] START   proj/core/aaaaaaaa-build.log",
    "[--:--:--][aaaaaaaa][   build:core.bst                      ] START   Staging dependencies at: /",
    "[00:00:00][aaaaaaaa][   build:core.bst                      ] SUCCESS Staging dependencies at: /",
    "[--:--:--][aaaaaaaa][   build:core.bst                      ] START   Running commands",
    "[00:00:04][aaaaaaaa][   build:core.bst                      ] SUCCESS Running commands",
    "[--:--:--][aaaaaaaa][   build:core.bst                      ] START   Caching artifact",
    "[00:00:00][aaaaaaaa][   build:core.bst                      ] SUCCESS Caching artifact",
    "[00:00:04][aaaaaaaa][   build:core.bst                      ] SUCCESS proj/core/aaaaaaaa-build.log",
    # lib.bst's own elapsed bracket resets to [00:00:00] here too - the
    # exact real symptom this bug produces - even though it really starts
    # a full 4 real seconds after core.bst began.
    "[--:--:--][bbbbbbbb][   build:lib.bst                       ] START   proj/lib/bbbbbbbb-build.log",
    "[--:--:--][bbbbbbbb][   build:lib.bst                       ] START   Staging dependencies at: /",
    "[00:00:00][bbbbbbbb][   build:lib.bst                       ] SUCCESS Staging dependencies at: /",
    "[--:--:--][bbbbbbbb][   build:lib.bst                       ] START   Running commands",
    "[00:00:02][bbbbbbbb][   build:lib.bst                       ] SUCCESS Running commands",
    "[--:--:--][bbbbbbbb][   build:lib.bst                       ] START   Caching artifact",
    "[00:00:00][bbbbbbbb][   build:lib.bst                       ] SUCCESS Caching artifact",
    "[00:00:02][bbbbbbbb][   build:lib.bst                       ] SUCCESS proj/lib/bbbbbbbb-build.log",
]


def _spans_by_hash(converter):
    begins = {e["tid"]: e for e in _builder_events(converter) if e["ph"] == "B"}
    ends = {e["tid"]: e for e in _builder_events(converter) if e["ph"] == "E"}
    return {
        tid: (begins[tid]["ts"], ends[tid]["ts"])
        for tid in begins
        if tid in ends
    }


def test_downstream_task_does_not_collapse_to_upstreams_own_start():
    """The core regression: lib.bst's reconstructed start must be at or
    after core.bst's real finish (4s in), never collapsed back to
    core.bst's own start just because its own elapsed bracket also read
    [00:00:00]."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in _UPSTREAM_THEN_DOWNSTREAM_LINES:
        converter.process_line_raw(line)

    spans = _spans_by_hash(converter)
    assert len(spans) == 2
    (core_start, core_end), (lib_start, lib_end) = spans.values()

    assert lib_start >= core_end


def test_each_tasks_own_real_duration_is_preserved():
    """Cross-task anchoring must not distort each task's own,
    independently-correct, real measured duration (core.bst: 4s total
    across its 3 sub-phases; lib.bst: 2s)."""
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in _UPSTREAM_THEN_DOWNSTREAM_LINES:
        converter.process_line_raw(line)

    spans = list(_spans_by_hash(converter).values())
    core_span, lib_span = spans
    assert core_span[1] - core_span[0] == 4_000_000
    assert lib_span[1] - lib_span[0] == 2_000_000


def test_nested_subphases_own_elapsed_does_not_corrupt_the_outer_span():
    """Regression for a real bug found while implementing this fix: the
    task-level closing line's message is a real artifact log path and its
    elapsed is relative to the *task's* own start - not the immediately
    preceding sub-phase's start. An earlier, naive "anchor = last START
    seen for this hash" implementation corrupted this badly (errors of
    several real seconds on examples/04's own real captured log) by
    re-anchoring on each nested sub-phase's own START."""
    converter = WrapperTraceConverter(raw_start_time_us=1_000_000)
    for line in _UPSTREAM_THEN_DOWNSTREAM_LINES:
        converter.process_line_raw(line)

    spans = list(_spans_by_hash(converter).values())
    core_span, _ = spans
    assert core_span[0] == 1_000_000
    assert core_span[1] == 1_000_000 + 4_000_000
