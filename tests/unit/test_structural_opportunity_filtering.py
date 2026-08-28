"""Tests for UX-34: `Top Improvement Opportunities` ranked `stack`/
`import` elements at sensitivity 1.00 above every element that does real
work, on both real example projects tested.

A structural element sitting on the critical path genuinely does have
sensitivity 1.00 by `compute_sensitivity`'s own definition - the problem
is that a `stack` has no build commands, so "optimize all.bst" is not an
action. `STRUCTURAL_ELEMENT_KINDS` (P4-12) and the tagging `UX-25`
already applies to coverage violations existed; this list never picked
them up.

Filtered rather than dropped (`UX-26`'s pattern), and because
`compute_sensitivity` returns ten candidates while only five are
published, filtering surfaces the next real candidate instead of
shortening the list.
"""
from bga.analyzer import BuildEfficiencyAnalyzer
from bga.ingest.models import (
    DependencyEdge, Element, Graph, NormalizedTask, RunContext, TaskKey, TaskKind, Trace,
)
from bga.report.text import format_text


def _task(uid, start_us, finish_us):
    return NormalizedTask(
        task_key=TaskKey(uid, TaskKind.BUILD, "BUILD", 0),
        ready_us=start_us, start_us=start_us, finish_us=finish_us,
    )


def _analyzer_with_structural_head_and_tail():
    """A real-shaped graph: an `import` toolchain everything depends on,
    three real cmake libraries, and a `stack` target on top - the exact
    shape both `examples/05` and `examples/06` have, and the shape that
    produced the two structural elements at the top of the ranking."""
    elements = [
        Element(uid="toolchain.bst", element_kind="import"),
        Element(uid="lib-a.bst", element_kind="cmake"),
        Element(uid="lib-b.bst", element_kind="cmake"),
        Element(uid="app.bst", element_kind="cmake"),
        Element(uid="all.bst", element_kind="stack"),
    ]
    dependencies = [
        DependencyEdge(predecessor="toolchain.bst", successor="lib-a.bst"),
        DependencyEdge(predecessor="toolchain.bst", successor="lib-b.bst"),
        DependencyEdge(predecessor="lib-a.bst", successor="app.bst"),
        DependencyEdge(predecessor="lib-b.bst", successor="app.bst"),
        DependencyEdge(predecessor="app.bst", successor="all.bst"),
    ]
    tasks = [
        _task("toolchain.bst", 0, 1),
        _task("lib-a.bst", 1, 3_000_000),
        _task("lib-b.bst", 1, 2_000_000),
        _task("app.bst", 3_000_000, 5_000_000),
        _task("all.bst", 5_000_000, 5_000_001),
    ]
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.graph = Graph(elements=elements, dependencies=dependencies)
    analyzer.trace = Trace(spans=[])
    analyzer.run_context = RunContext(resource_capacities={"PROCESS": 2})
    analyzer.normalized_tasks = tasks
    return analyzer


def _sensitivity():
    return _analyzer_with_structural_head_and_tail()._compute_structural_analysis()["sensitivity"]


def test_structural_elements_are_not_ranked_as_improvement_opportunities():
    ranked = [row["element_uid"]
              for row in _sensitivity()["top_opportunities"]]
    assert "all.bst" not in ranked
    assert "toolchain.bst" not in ranked


def test_real_elements_still_rank():
    ranked = [row["element_uid"]
              for row in _sensitivity()["top_opportunities"]]
    assert "app.bst" in ranked
    assert "lib-a.bst" in ranked


def test_omitted_structural_elements_are_listed_not_silently_dropped():
    omitted = _sensitivity()["omitted_structural_opportunities"]
    by_element = {o["element"]: o["element_kind"] for o in omitted}
    assert by_element == {"all.bst": "stack", "toolchain.bst": "import"}


def test_serialized_pairs_are_no_longer_anchored_on_structural_elements():
    """`serialized_pairs` is derived purely from the candidate list, so
    filtering candidates fixes it transitively - previously every printed
    pair on a real run had a `stack` or `import` on one side."""
    structural = _analyzer_with_structural_head_and_tail()._compute_structural_analysis()
    pairs = structural["batch_opportunities"]["serialized_pairs"]
    flattened = {uid for pair in pairs for uid in pair}
    assert "all.bst" not in flattened
    assert "toolchain.bst" not in flattened


def test_report_states_what_was_omitted_and_why():
    class _Result:
        run_id = "t"
        total_duration_us = 5_000_000
        signals = {}
        floors = {}
        attribution = {}
        confidence = {}
        violations = []
        utilisation = {}
        occupancy = {}
        pipeline_overhead = {}
        structural = {
            "metrics": {"num_elements": 5, "num_edges": 5, "max_depth": 3},
            "bottleneck": {},
            "parallelism": {},
            "sensitivity": {
                "top_opportunities": [{"element_uid": "app.bst",
                                       "sensitivity": 0.82,
                                       "saving_us": 816000}],
                "omitted_structural_opportunities": [
                    {"element": "all.bst", "element_kind": "stack"},
                ],
                "total_improvable_time_us": 2_000_000,
                "best_case_speedup": 1.4,
            },
        }

    out = format_text(_Result(), section="graph")
    assert "1 structural element(s) omitted" in out
    assert "all.bst [stack]" in out
    assert "no build commands to speed up" in out
