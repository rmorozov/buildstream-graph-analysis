"""Tests for UX-29: `native_max_jobs` was only ever recorded when the
operator passed `--native-max-jobs` by hand, so the whole capacity-guard
chain (UX-12/15/16/17/21) sat inert on every run the documented pipeline
produced - `"native_max_jobs": null`, `violations: []`.

The value is in the log the extractor already parses: a wrapped log's
first line is
`Executing command: bst --builders 4 --max-jobs 4 build all.bst`, and
`EXEC_CMD_RE` already matched it for the trace side.
"""
import json

from tools._run_context_common import (
    NATIVE_MAX_JOBS_OPERATOR_DECLARED,
    NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION,
    add_cpu_capacity_fields,
)
from tools.bst_log_to_chrome_trace import WrapperTraceConverter

_EXEC_LINE = (
    "[wrapper][2026-08-16 18:22:59,383] INFO: Executing command: "
    "bst --builders 4 --max-jobs 4 build all.bst"
)


def _converter_for(line):
    converter = WrapperTraceConverter()
    converter.process_line_wrapped(line)
    return converter


def test_max_jobs_is_recovered_from_the_wrapped_invocation_line():
    config = _converter_for(_EXEC_LINE).get_scheduler_config()
    assert config["native_max_jobs"] == 4


def test_equals_spelling_is_recovered_too():
    """Both are real click syntax."""
    line = _EXEC_LINE.replace("--max-jobs 4", "--max-jobs=8")
    assert _converter_for(line).get_scheduler_config()["native_max_jobs"] == 8


def test_invocation_without_the_flag_records_nothing():
    """Absent, not defaulted - the consumer must be able to tell "the
    build didn't set it" from "the build set it to N"."""
    line = _EXEC_LINE.replace(" --max-jobs 4", "")
    assert _converter_for(line).get_scheduler_config()["native_max_jobs"] is None


def test_raw_log_has_no_invocation_line_and_stays_none():
    converter = WrapperTraceConverter(raw_start_time_us=0)
    converter.process_line_raw("    Maximum Build Tasks:     4")
    assert converter.get_scheduler_config()["native_max_jobs"] is None


def test_parsed_value_is_published_with_its_provenance():
    run_context = {}
    add_cpu_capacity_fields(run_context, parsed_native_max_jobs=4)
    assert run_context["native_max_jobs"] == 4
    assert run_context["native_max_jobs_source"] == NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION


def test_explicit_operator_declaration_wins_over_the_parsed_value():
    """An operator overriding what the command line said is making a
    deliberate statement (e.g. correcting for a wrapper script that
    rewrites flags) - and the report must be able to say which one it
    certified against."""
    run_context = {}
    add_cpu_capacity_fields(run_context, native_max_jobs=2, parsed_native_max_jobs=4)
    assert run_context["native_max_jobs"] == 2
    assert run_context["native_max_jobs_source"] == NATIVE_MAX_JOBS_OPERATOR_DECLARED


def test_neither_source_leaves_both_fields_absent():
    run_context = {}
    add_cpu_capacity_fields(run_context)
    assert "native_max_jobs" not in run_context
    assert "native_max_jobs_source" not in run_context


def test_run_context_loader_round_trips_the_provenance(tmp_path):
    from bga.ingest.loader import load_run_context

    path = tmp_path / "run-context.json"
    path.write_text(json.dumps({
        "trace_epsilon_us": 50000,
        "resource_capacities": {"PROCESS": 4},
        "native_max_jobs": 4,
        "native_max_jobs_source": NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION,
        "host_cpu_count": 4,
    }))
    run_context = load_run_context(str(path))
    assert run_context.native_max_jobs == 4
    assert run_context.native_max_jobs_source == NATIVE_MAX_JOBS_PARSED_FROM_INVOCATION


def test_report_says_when_capacity_checks_did_not_run():
    """Item 4: a guard that declines to run is otherwise
    indistinguishable, in the report, from one that ran and passed."""
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.ingest.models import RunContext

    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(resource_capacities={"PROCESS": 4})
    analyzer._check_process_oversubscription()
    assert "native_max_jobs" in analyzer.capacity_check_skipped_inputs
    note = analyzer._build_capacity_model_note()
    assert "Capacity checks (over/under-subscription, memory) did not run" in note
    assert "inert here, not passing" in note


def test_note_stays_clean_when_the_checks_did_run():
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.ingest.models import RunContext

    analyzer = BuildEfficiencyAnalyzer()
    analyzer.run_context = RunContext(
        resource_capacities={"PROCESS": 4}, native_max_jobs=4, host_cpu_count=8,
    )
    analyzer._check_process_oversubscription()
    assert analyzer.capacity_check_skipped_inputs == []
    assert "did not run" not in analyzer._build_capacity_model_note()
