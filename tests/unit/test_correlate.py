"""UX-51: joining the two planes on element UID.

`docs/design-directions.md` named the seam between Plane 1 ("which
elements matter") and Plane 2 ("what happened inside them") as the
biggest remaining gap. It is closed as an explicit join rather than a
merge, and these tests pin the properties that make the join trustworthy
rather than merely present.

The payoff to protect is the sentence neither plane can produce alone:
*the element that dominates your critical path is not compute-bound, so
fix how it is built, not what it builds.*
"""
import pytest

from bga.correlate import correlate, format_correlation


def _analysis(critical_path=(), opportunities=(), critical_path_us=20_000_000, blast=None):
    return {
        "signals": {
            "critical_path": list(critical_path),
            "blast_radius": blast or {},
        },
        "structural": {
            "sensitivity": {
                "top_opportunities": [list(o) for o in opportunities],
                "critical_path_us": critical_path_us,
            }
        },
    }


def _native(parallelism=(), cpu=None, unused=()):
    return {
        "by_element": {entry["element"]: 1 for entry in parallelism},
        "per_element_parallelism": list(parallelism),
        "cpu_time": {"per_element": cpu or {}},
        "declared_vs_used": {"unused_candidates": list(unused)},
    }


def _cpu(cores_busy, coverage=1.0):
    return {"cpu_per_wall_second": cores_busy, "coverage": coverage}


# --- the finding the join exists for -----------------------------------

def test_critical_path_element_that_is_waiting_is_told_to_fix_its_parallelism():
    """The real `core.bst` case: 25% of the critical path at 0.85 cores
    busy with `-j1`. Plane 1 knows the first half, Plane 2 the second,
    and only the join can say what to do."""
    result = correlate(
        _analysis(critical_path=["core.bst"], opportunities=[("core.bst", 0.25, 25.0)]),
        _native(
            parallelism=[{"element": "core.bst", "requested_jobs": 1,
                          "findings": ["pinned_to_one_job"]}],
            cpu={"core.bst": _cpu(0.85)},
        ),
    )

    steps = result["actionable"][0]["recommendations"]
    assert result["actionable"][0]["element"] == "core.bst"
    assert "waiting, not computing" in steps[0]
    assert "notparallel" in steps[0]


def test_critical_path_element_that_is_busy_is_told_the_opposite():
    """The negative result is the other half of the value: it stops a
    reader looking at the micro plane for an element that has nothing to
    give there."""
    result = correlate(
        _analysis(critical_path=["heavy.bst"], opportunities=[("heavy.bst", 0.4, 40.0)]),
        _native(
            parallelism=[{"element": "heavy.bst", "requested_jobs": 4, "findings": []}],
            cpu={"heavy.bst": _cpu(3.8)},
        ),
    )

    step = result["actionable"][0]["recommendations"][0]
    assert "already compute-bound" in step
    assert "less work" in step


def test_underachieving_element_is_distinguished_from_a_pinned_one():
    """Asked for -j4 and got one core: a different fix from `-j1`."""
    result = correlate(
        _analysis(critical_path=["slow.bst"], opportunities=[("slow.bst", 0.3, 30.0)]),
        _native(
            parallelism=[{"element": "slow.bst", "requested_jobs": 4, "findings": []}],
            cpu={"slow.bst": _cpu(0.9)},
        ),
    )

    step = result["actionable"][0]["recommendations"][0]
    assert "despite asking for -j4" in step
    assert "notparallel" not in step


def test_unused_dependencies_are_reported_as_a_macro_fix():
    result = correlate(
        _analysis(),
        _native(unused=[{"element": "lib.bst", "dependency": "codegen.bst"}]),
    )

    step = result["actionable"][0]["recommendations"][0]
    assert "1 declared build dependency" in step
    # UX-68: never a verdict - the producer cannot distinguish a
    # runtime-only dependency from an unused one.
    assert "free" not in step
    assert "evidence, not a verdict" in step
    assert "codegen.bst" in step


# --- the ways this could mislead ---------------------------------------

def test_element_on_the_path_but_unable_to_move_the_finish_makes_no_claim():
    """An element can sit on the critical path and still have zero
    measurable saving (UX-44). An earlier version rendered "holds 0% of
    the critical path and is genuinely compute-bound" for exactly that
    case - a confident statement about nothing."""
    result = correlate(
        _analysis(critical_path=["app.bst"], opportunities=[]),
        _native(
            parallelism=[{"element": "app.bst", "requested_jobs": 4, "findings": []}],
            cpu={"app.bst": _cpu(1.3)},
        ),
    )

    assert result["actionable"] == []


def test_untraced_but_impactful_elements_are_named_not_assumed_fine():
    """Plane 1 says this element matters; Plane 2 never saw it. Silence
    would read as "nothing to report inside it"."""
    result = correlate(
        _analysis(critical_path=["ghost.bst"], opportunities=[("ghost.bst", 0.5, 50.0)]),
        _native(),
    )

    assert result["coverage"]["plane1_only_with_impact"] == ["ghost.bst"]
    assert "ghost.bst" in format_correlation(result)


def test_partial_cpu_coverage_is_surfaced():
    """UX-45's coverage must survive the join - a recommendation built on
    81% of an element's processes should say so."""
    result = correlate(
        _analysis(critical_path=["core.bst"], opportunities=[("core.bst", 0.5, 50.0)]),
        _native(
            parallelism=[{"element": "core.bst", "requested_jobs": 1,
                          "findings": ["pinned_to_one_job"]}],
            cpu={"core.bst": _cpu(0.8, coverage=0.81)},
        ),
    )

    assert "81% of this element's processes were measured" in format_correlation(result)


def test_ranking_follows_plane1_impact():
    """Plane 2 explains the top of Plane 1's list; it must not reorder
    it, or the user's question changes under them."""
    result = correlate(
        _analysis(
            opportunities=[("small.bst", 0.1, 10.0), ("big.bst", 0.6, 60.0)],
            critical_path_us=10_000_000,
        ),
        _native(
            parallelism=[
                {"element": "big.bst", "requested_jobs": 1, "findings": ["pinned_to_one_job"]},
                {"element": "small.bst", "requested_jobs": 1, "findings": ["pinned_to_one_job"]},
            ],
            cpu={"big.bst": _cpu(0.5), "small.bst": _cpu(0.5)},
        ),
    )

    assert [e["element"] for e in result["actionable"]] == ["big.bst", "small.bst"]


def test_empty_inputs_are_safe():
    result = correlate(_analysis(), _native())

    assert result["actionable"] == []
    assert "No element has a finding in both planes" in format_correlation(result)


@pytest.mark.parametrize("count,expected", [(1, "1 declared build dependency"), (3, "3 declared build dependencies")])
def test_dependency_pluralisation(count, expected):
    unused = [{"element": "x.bst", "dependency": f"d{i}.bst"} for i in range(count)]

    result = correlate(_analysis(), _native(unused=unused))

    assert expected in result["actionable"][0]["recommendations"][0]


def test_join_reports_its_own_coverage():
    result = correlate(
        _analysis(critical_path=["a.bst", "b.bst"], opportunities=[("a.bst", 0.5, 50.0)]),
        _native(
            parallelism=[{"element": "a.bst", "requested_jobs": 4, "findings": []}],
            cpu={"a.bst": _cpu(2.0)},
        ),
    )

    coverage = result["coverage"]
    assert coverage["joined_elements"] == 1
    assert coverage["plane2_elements"] == 1
    assert coverage["plane1_elements"] >= 2
