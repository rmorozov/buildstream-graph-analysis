"""Tests for P4-05 (tools/bst_log_to_chrome_trace.py raw-log support) and
two real bugs found while implementing it, confirmed against a real,
installed BuildStream 2.7.0 (see docs/ingestion-pipeline.md):

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
# app.bst` against BuildStream 2.7.0 (see docs/ingestion-pipeline.md) -
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
    ourselves (see docs/ingestion-pipeline.md)."""
    lines = [
        "    Maximum Fetch Tasks:     7",
        "    Maximum Build Tasks:     3",
        "    Maximum Push Tasks:      2",
    ]
    converter = WrapperTraceConverter(raw_start_time_us=0)
    for line in lines:
        converter.process_line_raw(line)

    config = converter.get_scheduler_config()
    assert config == {"builders": 3, "fetchers": 7, "pushers": 2}


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
    assert converter.get_scheduler_config() == {"builders": 4, "fetchers": 10, "pushers": 4}


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


def test_raw_mode_converts_elapsed_to_absolute_microseconds():
    converter = WrapperTraceConverter(raw_start_time_us=1_700_000_000_000_000)
    converter.process_line_raw(
        "[00:00:05][4a9059d4][   build:base.bst] START   base/4a9059d4-build.log"
    )
    begin = _builder_events(converter)[0]
    assert begin["ts"] == 1_700_000_000_000_000 + 5_000_000


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
