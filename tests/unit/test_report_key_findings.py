"""Tests for P4-02: report text output leads with a synthesized "Key
Findings" summary (confidence, biggest wait-category opportunity, top
blast-radius/criticality elements, certified headroom in plain language),
plus a confidence/violations block that was previously entirely missing
from text output (only reachable via --format json).
"""
import json

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text, format_csv
from bga.report.json import format_json


def _write_run_dir(tmp_path, run_context, elements, dependencies, spans):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "requested_target": is_target} for uid, is_target in elements],
        "dependencies": [
            {"predecessor": pred, "successor": succ} for pred, succ in dependencies
        ],
    }
    trace = {"spans": spans, "phases": []}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


@pytest.fixture
def analyzed_result(tmp_path):
    """root.bst fans out to a.bst/b.bst/c.bst (root has the highest
    downstream_count = worst blast radius, unambiguous - the others have
    0). a.bst has a large, deliberate DEPENDENCY_WAIT gap (starts long
    after it became ready) - the clear dominant non-execution attribution
    category, distinct from b.bst/c.bst which start immediately.
    """
    run_dir = _write_run_dir(
        tmp_path,
        # No max_jobs declared - classify_scheduler_wait requires it as
        # evidence (Part 9) and otherwise defers, so a.bst's wait falls
        # through to DEPENDENCY_WAIT, the deliberate dominant category
        # this fixture is designed to produce.
        run_context={
            "trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 110000,
        },
        elements=[("root.bst", False), ("a.bst", True), ("b.bst", True), ("c.bst", True)],
        dependencies=[("root.bst", "a.bst"), ("root.bst", "b.bst"), ("root.bst", "c.bst")],
        spans=[
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "c.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 100000, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    result = analyzer.analyze()
    return result


def test_key_findings_block_appears_before_certified_floors(analyzed_result):
    output = format_text(analyzed_result)
    assert "Key Findings:" in output
    assert output.index("Key Findings:") < output.index("Certified Floors:")


def test_key_findings_names_the_correct_dominant_wait_category(analyzed_result):
    output = format_text(analyzed_result)
    key_findings_section = output.split("Certified Floors:")[0]
    assert "Biggest Opportunity" in key_findings_section
    assert "DEPENDENCY WAIT" in key_findings_section
    # Not any of the other categories, which are all much smaller here.
    assert "RESOURCE WAIT" not in key_findings_section
    assert "SCHEDULER WAIT" not in key_findings_section


def test_key_findings_names_the_correct_worst_blast_radius_element(analyzed_result):
    output = format_text(analyzed_result)
    key_findings_section = output.split("Certified Floors:")[0]
    assert "Elements Most Worth Optimizing First" in key_findings_section
    assert "root.bst" in key_findings_section
    assert "3 downstream elements" in key_findings_section


def test_key_findings_criticality_list_excludes_zero_probability_elements(analyzed_result):
    """b.bst/c.bst have 0% criticality probability in this fixture - they
    must not pad out the "Highest Criticality Elements" list just to
    reach 3 entries (only root.bst/a.bst, both 100%, genuinely qualify)."""
    output = format_text(analyzed_result)
    key_findings_section = output.split("Certified Headroom")[0]
    criticality_section = key_findings_section.split("Highest Criticality Elements:")[1]
    assert "b.bst" not in criticality_section
    assert "c.bst" not in criticality_section


def test_key_findings_shows_confidence_headline(analyzed_result):
    output = format_text(analyzed_result)
    assert "Confidence:" in output


def test_key_findings_shows_certified_headroom_in_plain_language(analyzed_result):
    output = format_text(analyzed_result)
    key_findings_section = output.split("Certified Floors:")[0]
    assert "Certified Headroom" in key_findings_section
    assert "available" in key_findings_section


def test_confidence_and_violations_block_present_in_default_text_output(analyzed_result):
    """Previously result.confidence/.violations were fully populated but
    never printed in text output at all - only reachable via --format json."""
    output = format_text(analyzed_result)
    assert "Confidence:" in output
    assert "Overall:" in output


def test_violations_are_listed_one_line_each(tmp_path):
    """A fixture with a genuine ordering violation must show up in the
    text report's Violations block, not just JSON."""
    run_dir = _write_run_dir(
        tmp_path,
        run_context={"trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 100000},
        elements=[("a.bst", False), ("b.bst", True)],
        dependencies=[("a.bst", "b.bst")],
        spans=[
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 50000, "dur_us": 50000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "b.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
    )
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    result = analyzer.analyze()

    output = format_text(result)
    assert "Violations (" in output
    assert "ordering:" in output
    assert "a.bst" in output and "b.bst" in output


def test_no_violations_produces_no_violations_block(analyzed_result):
    """A clean fixture (no ordering issues) must not print an empty/
    misleading Violations block."""
    output = format_text(analyzed_result)
    assert "Violations (" not in output


def test_key_findings_and_confidence_block_absent_for_subcommand_sections(analyzed_result):
    """Only the full report (section=None) gets the synthesized summary -
    subcommand-specific text output (graph/floors/replay/utilisation/
    diagnostics) is unaffected, matching format_json's own confidence/
    violations gating."""
    for section in ("graph", "floors", "utilisation", "diagnostics"):
        output = format_text(analyzed_result, section=section)
        assert "Key Findings:" not in output


def test_format_json_output_unchanged_by_key_findings(analyzed_result):
    """This is presentation-only for the text formatter - JSON output
    must be byte-identical to what it already was (confidence/violations
    were already present in JSON before this change)."""
    output = format_json(analyzed_result)
    data = json.loads(output)
    assert "confidence" in data
    assert "violations" in data
    assert "Key Findings" not in output  # JSON never gets prose


def test_format_csv_output_unchanged_by_key_findings(analyzed_result):
    output = format_csv(analyzed_result)
    assert output.startswith("category,duration_us,duration_s,percent")
    assert "Key Findings" not in output
