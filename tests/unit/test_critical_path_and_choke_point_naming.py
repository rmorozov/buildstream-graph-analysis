"""Tests for UX-33: the text report withheld the critical path entirely
above 5 elements (`if len(critical_path) <= 5`) and printed
`Bottlenecks Identified: N` without ever naming the choke points - both
already computed, both already in `--format json`.

Real repro from the doc's Motivation: a real `bga analyze` against
`examples/06-macro-micro-optimization`, whose entire problem is a
ten-element artificial dependency chain, printed
`Critical Path Length: 10 elements` and nothing else, and
`Bottlenecks Identified: 5` for the five chained libraries that *were*
the answer.
"""
from bga.report.text import format_text


class _Result:
    """Minimal AnalysisResult stand-in - `format_text` reads attributes
    off the result with `hasattr`/`.get`, so a namespace object with the
    two sections under test is enough and keeps these tests hermetic."""

    def __init__(self, signals=None, structural=None):
        self.run_id = "test-run"
        self.total_duration_us = 40_000_000
        self.signals = signals or {}
        self.structural = structural or {}
        self.floors = {}
        self.attribution = {}
        self.confidence = {}
        self.violations = []
        self.utilisation = {}
        self.occupancy = {}
        self.pipeline_overhead = {}


def _detail(uid, duration_us, share, kind="cmake", structural=False):
    return {
        "element_uid": uid,
        "element_kind": kind,
        "is_structural_kind": structural,
        "duration_us": duration_us,
        "share_of_path": share,
    }


def _long_path_result():
    path = ["toolchain.bst"] + [f"lib-{c}.bst" for c in "abcdef"] + ["app.bst", "all.bst"]
    detail = [_detail("toolchain.bst", 0, 0.0, kind="import", structural=True)]
    detail += [_detail(f"lib-{c}.bst", 3_000_000, 0.1) for c in "abcdef"]
    detail += [
        _detail("app.bst", 4_200_000, 0.14),
        _detail("all.bst", 0, 0.0, kind="stack", structural=True),
    ]
    return _Result(signals={
        "critical_path": path,
        "critical_path_length": len(path),
        "critical_path_detail": detail,
    })


def test_long_critical_path_is_printed_not_withheld():
    out = format_text(_long_path_result(), section="graph")
    assert "Critical Path Length: 9 elements" in out
    for uid in ["toolchain.bst", "lib-a.bst", "lib-f.bst", "app.bst", "all.bst"]:
        assert uid in out, f"{uid} missing from a printed critical path"


def test_long_critical_path_shows_per_element_duration_and_share():
    out = format_text(_long_path_result(), section="graph")
    assert "4.20s" in out, "app.bst's real duration should be shown"
    assert "% of path" in out, "each link's share of the path should be shown"


def test_structural_elements_on_the_path_are_tagged_not_hidden():
    out = format_text(_long_path_result(), section="graph")
    # Both are real graph structure and belong on the printed chain, but
    # neither has build commands to speed up - the reader needs to know.
    assert out.count("[structural:") == 2
    assert "no build commands to speed up" in out


def test_short_critical_path_keeps_the_one_line_arrow_form():
    path = ["core.bst", "lib-a.bst", "app.bst"]
    result = _Result(signals={
        "critical_path": path,
        "critical_path_length": len(path),
        "critical_path_detail": [_detail(uid, 1_000_000, 0.33) for uid in path],
    })
    out = format_text(result, section="graph")
    assert "Path: core.bst → lib-a.bst → app.bst" in out


def test_long_path_without_detail_still_prints_the_chain():
    """An older run directory (or any result built without normalized
    tasks) has no `critical_path_detail` - the chain must still be
    printed, never dropped back to a bare length."""
    path = [f"e{i}.bst" for i in range(9)]
    result = _Result(signals={"critical_path": path, "critical_path_length": len(path)})
    out = format_text(result, section="graph")
    assert "e0.bst → e1.bst" in out
    assert "e8.bst" in out


def test_choke_points_are_named():
    result = _Result(structural={
        "metrics": {"num_elements": 11, "num_edges": 34, "max_depth": 9},
        "bottleneck": {"choke_points": ["lib-a.bst", "lib-b.bst", "lib-c.bst"]},
        "parallelism": {},
    })
    out = format_text(result, section="graph")
    assert "Bottlenecks Identified: 3 - lib-a.bst, lib-b.bst, lib-c.bst" in out


def test_choke_point_overflow_is_stated_not_silently_dropped():
    choke_points = [f"lib-{i}.bst" for i in range(12)]
    result = _Result(structural={
        "metrics": {"num_elements": 20, "num_edges": 40, "max_depth": 9},
        "bottleneck": {"choke_points": choke_points},
        "parallelism": {},
    })
    out = format_text(result, section="graph")
    assert "Bottlenecks Identified: 12 - " in out
    assert "(+4 more, see --format json)" in out
