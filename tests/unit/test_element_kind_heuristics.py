"""Tests for P4-12 (element-kind-based heuristics): Directions 1-3 -
element_kind annotations on diagnostic signal listings, structural-kind
flagging (linked with P4-15 Direction 2), and the `bga graph --by-kind`
aggregate summary view. See
docs/tasks/P4-12-element-kind-based-heuristics.md.

Two layers, matching tests/unit/test_bst_show_to_graph.py's convention:
1. A real, `bst`-gated end-to-end check that the extended
   tests/fixtures/bst_show_project/ fixture (now with `all.bst`, kind:
   stack, and `manual.bst`, kind: manual - added for this task alongside
   the pre-existing `subproj-junction.bst`, kind: junction, and the
   fixture's original `kind: import` elements) really does extract 4
   diverse real element_kind values via `bst show` - not assumed.
2. Synthetic, hand-built run dirs (same pattern as
   tests/unit/test_report_key_findings.py) exercising the actual
   analysis/report wiring deterministically.
"""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.report.text import format_text
from bga.report.json import format_json

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"
BST_AVAILABLE = shutil.which("bst") is not None


@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_fixture_has_four_diverse_element_kinds():
    from tools.bst_show_to_graph import extract_graph

    graph = extract_graph(
        str(FIXTURE_PROJECT),
        ["app.bst", "manual.bst", "all.bst", "subproj-junction.bst"],
    )
    kinds_by_uid = {e["uid"]: e.get("element_kind") for e in graph["elements"]}

    assert kinds_by_uid["base.bst"] == "import"
    assert kinds_by_uid["manual.bst"] == "manual"
    assert kinds_by_uid["all.bst"] == "stack"
    assert kinds_by_uid["subproj-junction.bst"] == "junction"


# --- Synthetic run dir: root.bst (import, structural) fans out to
# manual.bst (manual, NOT structural - real compute work) and a.bst (no
# element_kind at all - the explicit "unknown" bucket). root.bst has the
# highest blast radius (2 downstream) and is on the critical path -
# deliberately the top-ranked entry in both blast-radius and criticality
# listings, so the structural-kind tag's presence/absence is exercised
# on real ranking output, not just the raw signal dict. -----------------

def _write_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [
            {"uid": "root.bst", "requested_target": False, "element_kind": "import"},
            {"uid": "manual.bst", "requested_target": True, "element_kind": "manual"},
            {"uid": "a.bst", "requested_target": True},  # no element_kind at all
        ],
        "dependencies": [
            {"predecessor": "root.bst", "successor": "manual.bst"},
            {"predecessor": "root.bst", "successor": "a.bst"},
        ],
    }
    trace = {
        "spans": [
            {"task_key": "root.bst|BUILD|BUILD|0", "ts_us": 0, "dur_us": 10000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "manual.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 20000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
            {"task_key": "a.bst|BUILD|BUILD|0", "ts_us": 10000, "dur_us": 5000,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"},
        ],
        "phases": [],
    }
    run_context = {"trace_epsilon_us": 1000, "wall_start_us": 0, "wall_end_us": 30000}
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


@pytest.fixture
def analyzed_result(tmp_path):
    run_dir = _write_run_dir(tmp_path)
    analyzer = BuildEfficiencyAnalyzer(run_dir, run_diagnostics=True)
    analyzer.load()
    return analyzer.analyze()


def test_element_kind_summary_groups_correctly(analyzed_result):
    summary = analyzed_result.element_kind_summary
    assert summary["import"]["count"] == 1
    assert summary["import"]["total_duration_us"] == 10000
    assert summary["manual"]["count"] == 1
    assert summary["manual"]["total_duration_us"] == 20000
    # No element_kind at all -> explicit "unknown" bucket, never dropped.
    assert summary["unknown"]["count"] == 1
    assert summary["unknown"]["total_duration_us"] == 5000


def test_blast_radius_signal_carries_kind_and_structural_flag(analyzed_result):
    blast_radius = analyzed_result.signals["blast_radius"]
    assert blast_radius["root.bst"]["element_kind"] == "import"
    assert blast_radius["root.bst"]["is_structural_kind"] is True
    assert blast_radius["manual.bst"]["element_kind"] == "manual"
    assert blast_radius["manual.bst"]["is_structural_kind"] is False
    assert blast_radius["a.bst"]["element_kind"] == "unknown"
    assert blast_radius["a.bst"]["is_structural_kind"] is False


def test_key_findings_tags_structural_top_element_but_not_real_work_one(analyzed_result):
    output = format_text(analyzed_result)
    key_findings = output.split("Certified Floors:")[0]

    # UX-65 changed which ranking this fixture gets. It is chain-bound
    # (T-infinity is essentially the whole wall clock), so "worth
    # optimizing first" now ranks by share of the critical path, and that
    # ranking *excludes* structural elements outright rather than listing
    # them with a caveat.
    #
    # The guarantee this test exists for is unchanged and now stronger:
    # a structural element is never presented as a thing to go and make
    # faster. Previously that was satisfied by tagging `root.bst`; now it
    # is satisfied by not ranking it at all.
    assert "Elements Most Worth Optimizing First (by what optimizing them" in key_findings
    assert "root.bst (2 downstream elements)" not in key_findings
    # Wherever any line does mention these elements, a structural tag
    # must never be attached to the one that does real work.
    assert "manual.bst [structural" not in key_findings


def test_leaf_analysis_detail_carries_kind_and_structural_flag(analyzed_result):
    detail = analyzed_result.signals["leaf_analysis"]["leaves_detail"]
    assert detail["manual.bst"]["element_kind"] == "manual"
    assert detail["manual.bst"]["is_structural_kind"] is False
    assert detail["a.bst"]["element_kind"] == "unknown"


# --- `bga graph --by-kind` (P4-12 Direction 3) ---------------------------

def test_by_kind_absent_from_text_report_by_default(analyzed_result):
    output = format_text(analyzed_result, section="graph")
    assert "By Element Kind:" not in output


def test_by_kind_present_when_requested_in_text_report(analyzed_result):
    output = format_text(analyzed_result, section="graph", by_kind=True)
    assert "By Element Kind:" in output
    assert "import" in output
    assert "manual" in output
    assert "unknown" in output


def test_by_kind_absent_from_json_by_default(analyzed_result):
    data = json.loads(format_json(analyzed_result, section="graph"))
    assert "element_kind_summary" not in data


def test_by_kind_present_in_json_when_requested(analyzed_result):
    data = json.loads(format_json(analyzed_result, section="graph", by_kind=True))
    assert data["element_kind_summary"]["import"]["count"] == 1
    assert data["element_kind_summary"]["manual"]["total_duration_us"] == 20000


def test_by_kind_flag_does_not_leak_into_other_sections(analyzed_result):
    """by_kind is graph-section-specific - passing it while requesting a
    different section (e.g. the full report) must not surface
    element_kind_summary anywhere unexpected."""
    data = json.loads(format_json(analyzed_result, section="floors", by_kind=True))
    assert "element_kind_summary" not in data


@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_cli_graph_by_kind_end_to_end(tmp_path):
    """Real CLI invocation, real subprocess - `bga graph RUN --by-kind`
    against the synthetic-trace run dir (real bst not needed for the CLI
    itself, just confirming the flag wiring end-to-end through argparse)."""
    import sys

    run_dir = _write_run_dir(tmp_path)
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "graph", str(run_dir), "--by-kind"],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert "By Element Kind:" in proc.stdout

    proc_default = subprocess.run(
        [sys.executable, "-m", "bga.cli", "graph", str(run_dir)],
        capture_output=True, text=True,
    )
    assert proc_default.returncode == 0, proc_default.stderr
    assert "By Element Kind:" not in proc_default.stdout
