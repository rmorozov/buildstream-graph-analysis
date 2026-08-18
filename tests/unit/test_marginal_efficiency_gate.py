"""UX-79: judge the efficiency of the change, not of the repository.

`--fail-on-efficiency-regression` reads dispatch occupancy, a whole-build
average, so its sensitivity is inversely proportional to project size.
Measured on real builds in round 10, two maximally-mis-added elements
moved global occupancy **6.1pp in an 11-element project** — barely past
the 5.0pp default — and the same two elements added to a 90-element
closure would move it under 1pp and pass. A gate that gets weaker as the
project grows is weakest exactly where CI matters most.

These fixtures reproduce that at two scales and show the marginal metric
does not move: the numbers in `test_the_marginal_gate_is_scale_invariant`
are the evidence for the default threshold.
"""
import json
import subprocess
import sys

from bga.compare import compare_runs

EXIT_OK = 0
EXIT_EFFICIENCY_REGRESSION = 5

D = 4_000_000  # one element's duration
B = 4          # builders


def _run_bga(args):
    return subprocess.run(
        [sys.executable, "-m", "bga.cli"] + args, capture_output=True, text=True,
    )


def _write_run(tmp_path, name, elements, deps, spans, builders=B):
    run_dir = tmp_path / name
    run_dir.mkdir()
    identity = {"manifest_hash": "shape-fixture", "targets": list(elements)}
    end = max(start + dur for _, start, dur in spans)
    (run_dir / "run-context.json").write_text(json.dumps({
        "trace_epsilon_us": 1000,
        "resource_capacities": {"PROCESS": builders},
        "run_identity": identity,
        "wall_clock": {"start_us": 0, "end_us": end},
    }))
    (run_dir / "graph.json").write_text(json.dumps({
        "elements": [{"uid": uid, "requested_target": True} for uid in elements],
        "dependencies": [
            {"predecessor": a, "successor": b, "dependency_type": "build"}
            for a, b in deps
        ],
        "run_identity_hash": identity["manifest_hash"],
    }))
    (run_dir / "trace.json").write_text(json.dumps({
        "run_identity_hash": identity["manifest_hash"],
        "spans": [
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": start, "dur_us": dur,
             "resources": ["PROCESS"], "primary_resource": "PROCESS"}
            for uid, start, dur in spans
        ],
        "phases": [],
    }))
    return run_dir


def _shape(n, add=None):
    """`n` independent elements off one root, packed onto B builders."""
    elements = ["root.bst"] + [f"e{i}.bst" for i in range(n)]
    deps = [("root.bst", f"e{i}.bst") for i in range(n)]
    spans = [("root.bst", 0, D)] + [
        (f"e{i}.bst", D + (i // B) * D, D) for i in range(n)
    ]
    tail = D + ((n + B - 1) // B) * D
    if add == "good":
        # Two more, filling spare slots in the existing waves.
        elements += ["g.bst", "h.bst"]
        deps += [("root.bst", "g.bst"), ("root.bst", "h.bst")]
        spans += [("g.bst", D, D), ("h.bst", D, D)]
    elif add == "bad":
        # The same two, chained behind everything and then behind each other.
        elements += ["g.bst", "h.bst"]
        deps += [(f"e{i}.bst", "g.bst") for i in range(n)] + [("g.bst", "h.bst")]
        spans += [("g.bst", tail, D), ("h.bst", tail + D, D)]
    return elements, deps, spans


def _trio(tmp_path, n):
    return (
        _write_run(tmp_path, f"base{n}", *_shape(n)),
        _write_run(tmp_path, f"good{n}", *_shape(n, "good")),
        _write_run(tmp_path, f"bad{n}", *_shape(n, "bad")),
    )


# --- the diff itself ----------------------------------------------------


def test_the_diff_names_exactly_the_added_elements(tmp_path):
    base, good, _bad = _trio(tmp_path, 10)

    diff = compare_runs(base, good).element_diff

    assert [e["element_uid"] for e in diff["new"]] == ["g.bst", "h.bst"]
    assert diff["removed"] == []
    assert diff["baseline_element_count"] == 11
    assert diff["candidate_element_count"] == 13


def test_a_well_added_element_carries_its_duration_and_its_position(tmp_path):
    """A good addition is off the critical path by construction, so a
    metric that could only see path members would score it as zero work
    and have nothing to compare - which is why `element_durations` is
    published for every element."""
    base, good, _bad = _trio(tmp_path, 10)

    new = {e["element_uid"]: e for e in compare_runs(base, good).element_diff["new"]}

    assert new["g.bst"]["duration_us"] == D
    assert new["g.bst"]["on_critical_path"] is False


# --- the metric ---------------------------------------------------------


def test_a_well_added_pair_scores_zero_stretch(tmp_path):
    base, good, _bad = _trio(tmp_path, 10)

    marginal = compare_runs(base, good).marginal_efficiency

    assert marginal["added_work_us"] == 2 * D
    assert marginal["stretch"] == 0.0


def test_a_serialized_pair_scores_full_stretch(tmp_path):
    base, _good, bad = _trio(tmp_path, 10)

    marginal = compare_runs(base, bad).marginal_efficiency

    assert marginal["stretch"] == 1.0
    assert marginal["on_critical_path"] == ["g.bst", "h.bst"]


def test_a_change_that_adds_nothing_declines_to_judge(tmp_path):
    """The ordinary case for a change that edits rather than adds. A
    verdict invented here would be a gate reporting green while checking
    nothing."""
    base, _good, _bad = _trio(tmp_path, 10)

    assert compare_runs(base, base).marginal_efficiency is None


# --- the property the task exists for -----------------------------------


def test_the_marginal_gate_is_scale_invariant(tmp_path):
    """`UX-79`'s third acceptance criterion, and the evidence behind the
    default threshold.

    The same two maximally-mis-added elements, at 11 elements and at
    1201:

    | | whole-build occupancy | marginal stretch |
    |---|---|---|
    | 11 elements  | -14.6pp (gate fails) | 1.00 |
    | 1201 elements | **-0.5pp (gate passes)** | **1.00** |

    The whole-build gate goes blind as the project grows; the marginal
    metric does not move, because it mentions only the added elements.
    """
    small_base, _sg, small_bad = _trio(tmp_path, 10)
    large_base, _lg, large_bad = _trio(tmp_path, 1200)

    small = compare_runs(small_base, small_bad)
    large = compare_runs(large_base, large_bad)

    def occupancy_drop_pp(comparison):
        before = comparison.baseline_metrics["occupancy_ratio"]
        after = comparison.candidate_metrics["occupancy_ratio"]
        return (before - after) * 100

    # The whole-build signal dilutes by more than an order of magnitude.
    assert occupancy_drop_pp(small) > 10.0
    assert occupancy_drop_pp(large) < 1.0

    # The marginal one is identical at both scales.
    assert small.marginal_efficiency["stretch"] == 1.0
    assert large.marginal_efficiency["stretch"] == 1.0


def test_the_gate_passes_a_good_add_and_fails_a_bad_one(tmp_path):
    base, good, bad = _trio(tmp_path, 10)

    assert _run_bga([
        "compare", str(base), str(good), "--fail-on-inefficient-additions",
    ]).returncode == EXIT_OK

    failed = _run_bga([
        "compare", str(base), str(bad), "--fail-on-inefficient-additions",
    ])
    assert failed.returncode == EXIT_EFFICIENCY_REGRESSION
    assert "Marginal efficiency gate FAILED" in failed.stderr
    assert "g.bst, h.bst" in failed.stderr


def test_the_gate_still_fails_the_bad_add_where_the_whole_build_gate_goes_blind(tmp_path):
    """The same pair at 1201 elements: the whole-build gate provably
    passes it, the marginal gate provably does not."""
    base, _good, bad = _trio(tmp_path, 1200)

    whole_build = _run_bga([
        "compare", str(base), str(bad), "--fail-on-efficiency-regression",
    ])
    marginal = _run_bga([
        "compare", str(base), str(bad), "--fail-on-inefficient-additions",
    ])

    assert whole_build.returncode == EXIT_OK
    assert marginal.returncode == EXIT_EFFICIENCY_REGRESSION


def test_an_empty_check_says_so_rather_than_reporting_green(tmp_path):
    base, _good, _bad = _trio(tmp_path, 10)

    result = _run_bga([
        "compare", str(base), str(base), "--fail-on-inefficient-additions",
    ])

    assert result.returncode == EXIT_OK
    assert "Marginal gate not applied" in result.stderr
    assert "not a pass" in result.stderr
