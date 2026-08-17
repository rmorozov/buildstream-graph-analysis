"""UX-53: one per-element duration definition, shared by both planes.

`bga` collapses an element's several tasks into one number in two
places - `analyze_graph`, which feeds `floors.t_infinity_observed` and
`signals.critical_path`, and `StructuralAnalyzer`, which feeds
`structural.sensitivity.*`, the level decomposition and the choke
points. UX-50 gave the second one its own construction (the *sum* of an
element's tasks) while the first kept the *maximum*, so the two
published a 22% disagreement on
`tests/fixtures/synthetic_multi_subproject` - the repository's oldest
fixture - for a quantity `UX-52`'s acceptance criterion says must be
equal.

Every fixture that pins that invariant (`UX-50`'s topology sweep,
`UX-52`'s runtime-edge tests, the 1202-element scale fixture) gives each
element exactly *one* task, where max and sum coincide. Real captures
never do: every element has at least a FETCH and a BUILD. These tests
exist to give the suite the shape that would have caught it.
"""
import json
import subprocess
import sys

import pytest

from bga.graph.edg import compute_element_durations
from bga.ingest.models import NormalizedTask, TaskKey, TaskKind


def _task(uid, kind, dur_us):
    return NormalizedTask(
        task_key=TaskKey(element_uid=uid, task_kind=kind, phase="EXECUTION"),
        ready_us=0,
        start_us=0,
        finish_us=dur_us,
    )


def test_an_elements_duration_is_its_longest_task():
    tasks = [
        _task("core.bst", TaskKind.FETCH, 500_000),
        _task("core.bst", TaskKind.BUILD, 3_000_000),
    ]

    assert compute_element_durations(tasks) == {"core.bst": 3_000_000}


def test_task_order_does_not_change_the_result():
    """UX-50's defect was order-dependent: it struck 0 of 11 elements on
    two real captures and 2 of 11 on a third."""
    fetch = _task("core.bst", TaskKind.FETCH, 500_000)
    build = _task("core.bst", TaskKind.BUILD, 3_000_000)

    assert compute_element_durations([fetch, build]) == compute_element_durations(
        [build, fetch]
    )


def test_a_fetch_longer_than_the_build_still_yields_the_longest_task():
    """Not a hypothetical: a large tarball over a slow link outlasts a
    small element's compile. The element still occupies at least that
    long, so the maximum stays a safe floor."""
    tasks = [
        _task("big-tarball.bst", TaskKind.FETCH, 9_000_000),
        _task("big-tarball.bst", TaskKind.BUILD, 1_000_000),
    ]

    assert compute_element_durations(tasks) == {"big-tarball.bst": 9_000_000}


def test_durations_are_not_summed():
    """The explicit negative. Summing is the unsafe direction for a
    certified lower bound: under unlimited capacity BuildStream's fetch
    queue runs an element's FETCH alongside other elements' builds, so
    FETCH + BUILD is not forced to be sequential on the chain."""
    tasks = [
        _task("core.bst", TaskKind.FETCH, 500_000),
        _task("core.bst", TaskKind.BUILD, 3_000_000),
    ]

    assert compute_element_durations(tasks)["core.bst"] != 3_500_000


def test_an_element_with_no_tasks_is_absent_rather_than_zero():
    assert compute_element_durations([]) == {}


def test_several_elements_are_independent():
    tasks = [
        _task("a.bst", TaskKind.FETCH, 100),
        _task("a.bst", TaskKind.BUILD, 900),
        _task("b.bst", TaskKind.BUILD, 400),
        _task("b.bst", TaskKind.FETCH, 700),
    ]

    assert compute_element_durations(tasks) == {"a.bst": 900, "b.bst": 700}


# --- the end-to-end cross-check, on a fixture with mixed task kinds ----


@pytest.fixture(scope="module")
def multi_kind_report():
    """The real report for `tests/fixtures/synthetic_multi_subproject`,
    which is the only checked-in fixture whose elements each have
    several task kinds (9 BUILD, 8 TRACK, 7 FETCH across 9 elements)."""
    result = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", "-d",
         "tests/fixtures/synthetic_multi_subproject", "-f", "json"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def test_sensitivity_critical_path_agrees_with_t_infinity(multi_kind_report):
    """UX-52's acceptance criterion, on a fixture with more than one task
    per element. Before UX-53 this read 144_500_000 against 118_000_000."""
    assert (
        multi_kind_report["structural"]["sensitivity"]["critical_path_us"]
        == multi_kind_report["floors"]["t_infinity_observed"]
    )


def test_critical_path_length_agrees_with_the_named_path(multi_kind_report):
    assert multi_kind_report["structural"]["metrics"]["critical_path_length"] == len(
        multi_kind_report["signals"]["critical_path"]
    )


def test_t_infinity_is_not_the_summed_path(multi_kind_report):
    """Pins the magnitude of what was wrong rather than only that it is
    now right: the summed path over this fixture's critical path is
    144.5s against a real floor of 118s, so the disagreement was 22% and
    in the unsafe direction."""
    assert multi_kind_report["floors"]["t_infinity_observed"] == 118_000_000
    assert multi_kind_report["structural"]["sensitivity"]["critical_path_us"] != 144_500_000
