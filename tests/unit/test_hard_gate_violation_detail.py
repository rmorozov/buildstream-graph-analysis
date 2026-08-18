"""Tests for UX-25: `critical_path_coverage`/`dominator_coverage` hard-
gate violations gain a real `detail` field naming the specific missing
element(s) and, where the existing STRUCTURAL_ELEMENT_KINDS heuristic
(P4-12) already explains it, the real reason - not just a bare ratio.

Reproduces the exact real shape found in docs/backlog/scenarios/UX-25's own
Motivation (a real bga analyze run against examples/05-cmake-cpp-
toolchain): a `kind: stack` element (`all.bst`) on the critical path
with no matching task, producing critical_path_coverage < 1.0 - the
report's own critical-path ranking already knows this is structural,
this fix makes the violation say so too.
"""
from bga.ingest.models import Element, Graph
from bga.report.text import _format_violation_summary
from bga.validation.invariants import compute_confidence


def _confidence(graph, critical_path=None, dominators=None, normalized_tasks=None):
    confidence, new_violations = compute_confidence(
        normalized_tasks=normalized_tasks or [],
        run_context=None,
        trace=None,
        graph=graph,
        violations=[],
        attribution_segments=[],
        graph_analysis={
            "critical_path": critical_path or [],
            "dominators": dominators if dominators is not None else {e.uid: [] for e in graph.elements},
        },
        attribution={},
        floors={},
    )
    return confidence, new_violations


def _task_for(uid):
    from bga.ingest.models import NormalizedTask, TaskKey, TaskKind
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=0, start_us=0, finish_us=1000,
    )


def test_stack_element_missing_from_critical_path_gets_structural_detail():
    graph = Graph(elements=[
        Element(uid="core.bst", element_kind="cmake"),
        Element(uid="all.bst", element_kind="stack"),
    ])
    tasks = [_task_for("core.bst")]  # all.bst has no task of its own

    confidence, new_violations = _confidence(
        graph, critical_path=["core.bst", "all.bst"], normalized_tasks=tasks,
    )

    assert confidence["critical_path_coverage"] == 0.5
    assert confidence["hard_gates"]["critical_path_coverage_full"] is False
    gate_violation = next(v for v in new_violations if v["gate"] == "critical_path_coverage")
    assert gate_violation["detail"] == [
        {"element_uid": "all.bst", "element_kind": "stack", "is_structural_kind": True},
    ]


def test_genuine_non_structural_gap_reports_element_without_false_structural_claim():
    """A missing task for a real, non-structural element (e.g. a genuine
    extraction bug or a real gap worth investigating) must still be
    named, but never mislabeled as structural just because some element
    on the path happens to be missing."""
    graph = Graph(elements=[
        Element(uid="core.bst", element_kind="cmake"),
        Element(uid="app.bst", element_kind="cmake"),
    ])
    tasks = [_task_for("core.bst")]  # app.bst has no task - a real gap, not structural

    confidence, new_violations = _confidence(
        graph, critical_path=["core.bst", "app.bst"], normalized_tasks=tasks,
    )

    gate_violation = next(v for v in new_violations if v["gate"] == "critical_path_coverage")
    assert gate_violation["detail"] == [
        {"element_uid": "app.bst", "element_kind": "cmake", "is_structural_kind": False},
    ]


def test_full_coverage_produces_no_violation_and_no_detail_needed():
    graph = Graph(elements=[Element(uid="core.bst", element_kind="cmake")])
    tasks = [_task_for("core.bst")]

    confidence, new_violations = _confidence(graph, critical_path=["core.bst"], normalized_tasks=tasks)

    assert confidence["critical_path_coverage"] == 1.0
    assert confidence["hard_gates"]["critical_path_coverage_full"] is True
    assert not any(v.get("gate") == "critical_path_coverage" for v in new_violations)


def test_dominator_coverage_gap_gets_the_same_real_detail():
    graph = Graph(elements=[
        Element(uid="core.bst", element_kind="cmake"),
        Element(uid="all.bst", element_kind="stack"),
    ])

    confidence, new_violations = _confidence(
        graph, critical_path=[], dominators={"core.bst": []},  # all.bst missing from dominators
    )

    assert confidence["dominator_coverage"] == 0.5
    gate_violation = next(v for v in new_violations if v["gate"] == "dominator_coverage")
    assert gate_violation["detail"] == [
        {"element_uid": "all.bst", "element_kind": "stack", "is_structural_kind": True},
    ]


def test_unknown_element_kind_never_silently_omitted():
    """An element with no element_kind at all (e.g. an older/hand-built
    graph.json) must report 'unknown', not crash or silently vanish from
    detail (P4-12's own established discipline)."""
    graph = Graph(elements=[
        Element(uid="core.bst", element_kind="cmake"),
        Element(uid="mystery.bst", element_kind=None),
    ])
    tasks = [_task_for("core.bst")]

    confidence, new_violations = _confidence(
        graph, critical_path=["core.bst", "mystery.bst"], normalized_tasks=tasks,
    )

    gate_violation = next(v for v in new_violations if v["gate"] == "critical_path_coverage")
    assert gate_violation["detail"] == [
        {"element_uid": "mystery.bst", "element_kind": "unknown", "is_structural_kind": False},
    ]


# --- text-report rendering (_format_violation_summary) --------------------

def test_text_summary_names_the_structural_element_and_reason():
    violation = {
        "type": "hard_gate_failed", "gate": "critical_path_coverage", "value": 0.8,
        "detail": [{"element_uid": "all.bst", "element_kind": "stack", "is_structural_kind": True}],
    }
    summary = _format_violation_summary(violation)

    assert "critical_path_coverage = 0.8" in summary
    assert "all.bst" in summary
    assert "stack" in summary
    assert "structural" in summary


def test_text_summary_names_a_genuine_gap_without_claiming_structural():
    violation = {
        "type": "hard_gate_failed", "gate": "critical_path_coverage", "value": 0.8,
        "detail": [{"element_uid": "app.bst", "element_kind": "cmake", "is_structural_kind": False}],
    }
    summary = _format_violation_summary(violation)

    assert "app.bst" in summary
    assert "genuine coverage gap" in summary
    assert "structural" not in summary


def test_text_summary_falls_back_to_bare_ratio_when_no_detail_present():
    """Backward compatible - a violation dict from before this fix (or
    any other hard-gate-shaped violation with no detail) still renders,
    unchanged."""
    violation = {"type": "hard_gate_failed", "gate": "critical_path_coverage", "value": 0.8}
    summary = _format_violation_summary(violation)

    assert summary == "hard gate failed: critical_path_coverage = 0.8"
