"""Tests for UX-20 (minimum tier): sensitivity.top_opportunities was
already computed (`bga/structural/analyzer.py::compute_sensitivity`)
but never rendered anywhere outside `--format json`'s
`structural.sensitivity` key - invisible to a user reading the text
report, the one most users actually read first.
"""
from pathlib import Path

from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "golden" / "mixed_task_kinds"


def _analyze():
    analyzer = BuildEfficiencyAnalyzer(FIXTURE)
    analyzer.load()
    return analyzer.analyze()


def test_text_report_surfaces_top_improvement_opportunities():
    result = _analyze()
    output = format_text(result)

    assert "Top Improvement Opportunities" in output
    # Real data from this fixture's own structural.sensitivity - not
    # just a section header with nothing under it.
    sensitivity = result.structural["sensitivity"]
    top_key = sensitivity["top_opportunities"][0][0]
    assert top_key in output


def test_text_report_names_best_case_speedup_and_improvable_time():
    result = _analyze()
    output = format_text(result)

    sensitivity = result.structural["sensitivity"]
    assert f"{sensitivity['best_case_speedup']:.2f}x" in output


def test_json_report_still_has_sensitivity_unchanged():
    """This is additive to the text report only - JSON's own
    structural.sensitivity shape (already correct) must stay unchanged."""
    from bga.report.json import format_json
    import json

    result = _analyze()
    data = json.loads(format_json(result))

    assert "top_opportunities" in data["structural"]["sensitivity"]
    assert "best_case_speedup" in data["structural"]["sensitivity"]


def test_text_report_surfaces_batch_opportunities():
    """UX-20's map-reduce tier: real, simulated combined-effect data,
    not just JSON-only (this fixture's own structural.batch_opportunities
    has one real group - app.bst/extra.bst - and real serialized pairs)."""
    result = _analyze()
    output = format_text(result)

    batch_opportunities = result.structural["batch_opportunities"]
    assert batch_opportunities["groups"]
    assert "Batch Opportunities" in output
    group = batch_opportunities["groups"][0]
    assert group["elements"][0] in output

    assert batch_opportunities["serialized_pairs"]
    assert "Serialized" in output


def test_json_report_has_batch_opportunities():
    from bga.report.json import format_json
    import json

    result = _analyze()
    data = json.loads(format_json(result))

    assert "batch_opportunities" in data["structural"]
    assert "groups" in data["structural"]["batch_opportunities"]
    assert "serialized_pairs" in data["structural"]["batch_opportunities"]
