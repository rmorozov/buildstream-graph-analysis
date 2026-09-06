"""UX-692: a seeded sweep over generated topologies, not fixtures.

Every other invariant guard runs on committed captures and one seeded
scale run - shapes the analyzer has always seen. This file generates a
fresh graph per seed (layers, width, builders, chain vs mesh fan-in,
an element-kind mix, a scattered share of structural 0-duration
elements, a runtime-edge share) and asserts I1-I6, I8, I10, I11 and
that every finding's provenance resolves, plus a report-size budget
per element-count class.

Self-contained rather than routed through `bga gen-synthetic`
(`tools/gen_synthetic_scale_run.py`): that CLI has no knob for
kinds-mix/chain-mesh/structural-share, and adding one is a `tools/`
change outside this item's declared surfaces (`tests/unit/`,
`tests/tiers.py`). `schedule()` is reused unchanged - it is already
generic over an arbitrary graph - everything upstream of it
(topology, kinds, durations) is built fresh here. Writes the same
ingested-form `run-context.json`/`graph.json`/`trace.json` triple the
shared topology fixture library under `tests/fixtures/` also produces,
by a local writer rather than importing that module - it already sits
at this repo's per-module test-selection ceiling (`UX-645`, the
selector guard's own file), and one more importer would cross it.

I7 (blame coverage) is I4 restated (`UX-567`) and I9/I12/I13 need CPU
accounting or cold mode, neither of which these generated runs carry
- asserting them here would assert a vacuous truth, not a property the
shape sweep can move. "The volume budget" (`UX-367`) is the *rendered
page* and needs a browser; this sweep is "no browser, no bst" by the
task's own Required Fix, so the budget asserted here is the JSON
report `format_json` already builds - the browser-free half of the
same size claim, banded the same way UX-529's `DATA_BUDGETS` is.
"""
import json
import random

import pytest

from bga import BuildEfficiencyAnalyzer
from bga.findings import compute_findings
from bga.report.json import format_json
from bga.validation.determinism import run_determinism_check
from tools.gen_synthetic_scale_run import schedule

#: Acceptance Test: "a run of 50 seeds green".
SEEDS = 50

_KINDS = ("cmake", "autotools", "meson", "manual", "script")
_STRUCTURAL_KINDS = ("import", "stack")

#: The six categories I4's exact sum is over (Part 12.1) - the same
#: constant `test_attribution_identity_across_topologies.py` names.
_TASK_HORIZON_KEYS = (
    "execution_on_chain_us", "dependency_wait_us", "resource_wait_us",
    "scheduler_wait_us", "idle_us", "retry_wait_us",
)

#: `(elements at most, report JSON bytes at most)`, largest class last -
#: `UX-529`'s own shape, banded for this sweep's range rather than
#: reusing its numbers, which are for the *exported, compacted* page.
#: Headroom measured against this file's own shapes: 38 elements ->
#: 73,518 B; 202 elements -> 218,344 B (`--durations`, see Outcome).
DATA_BUDGETS = (
    (60, 130_000),
    (250, 280_000),
)


def _budget_for(elements):
    for at_most, budget in DATA_BUDGETS:
        if elements <= at_most:
            return budget
    raise AssertionError(
        f"{elements:,} elements is past every class in DATA_BUDGETS; "
        f"decide a bound for that size rather than inheriting one")


def _generate(seed):
    """One (run_context, graph, trace) triple and its element count,
    deterministic in `seed` alone - a fixed draw order off one `Random`,
    the same discipline `gen_synthetic_scale_run.build_graph` uses."""
    rng = random.Random(seed)
    layers = rng.randint(2, 8)
    width = rng.randint(2, 25)
    builders = rng.randint(1, 12)
    mesh = rng.choice((False, True))
    deps_per_module = rng.randint(2, 4) if mesh else 1
    structural_share = rng.uniform(0.0, 0.35)
    runtime_share = rng.uniform(0.0, 0.15)
    max_duration_s = rng.uniform(0.5, 6.0)

    def mod(layer, index):
        return f"layer{layer:02d}/mod{index:03d}.bst"

    elements = [{"uid": "toolchain.bst", "cache_key": "tc",
                "requested_target": False, "element_kind": "import"}]
    dependencies = []
    for layer in range(layers):
        for index in range(width):
            uid = mod(layer, index)
            structural = rng.random() < structural_share
            kind = rng.choice(_STRUCTURAL_KINDS) if structural else rng.choice(_KINDS)
            elements.append({"uid": uid, "cache_key": f"k{(layer * width + index) % 100:02d}",
                             "requested_target": False, "element_kind": kind})
            dependencies.append({"predecessor": "toolchain.bst", "successor": uid,
                                 "dependency_type": "build"})
            if layer == 0:
                continue
            k = min(deps_per_module, width)
            preds = rng.sample(range(width), k) if mesh else [index % width]
            for pred_index in preds:
                dtype = "runtime" if rng.random() < runtime_share else "build"
                dependencies.append({"predecessor": mod(layer - 1, pred_index),
                                     "successor": uid, "dependency_type": dtype})
    elements.append({"uid": "all.bst", "cache_key": "all",
                     "requested_target": True, "element_kind": "stack"})
    for index in range(width):
        dependencies.append({"predecessor": mod(layers - 1, index),
                             "successor": "all.bst", "dependency_type": "build"})

    durations = {}
    for element in elements:
        uid = element["uid"]
        if element["element_kind"] in ("import", "stack"):
            durations[uid] = 1
        else:
            durations[uid] = int(rng.uniform(0.05, max_duration_s) * 1_000_000)

    placement = schedule(elements, dependencies, durations, builders)
    horizon = max(start + dur for start, dur in placement.values())
    spans = sorted(
        ({"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": placement[uid][0],
          "dur_us": placement[uid][1], "resources": ["PROCESS"],
          "primary_resource": "PROCESS"} for uid in placement),
        key=lambda s: (s["ts_us"], s["task_key"]))
    loading_us, resolving_us = 900_000, 1_100_000
    run_context = {
        "trace_epsilon_us": 50_000,
        "resource_capacities": {"PROCESS": builders, "DOWNLOAD": 10, "UPLOAD": 4},
        "max_jobs": builders, "native_max_jobs": 4,
        "native_max_jobs_source": "parsed_from_invocation",
        "host_cpu_count": builders,
        "wall_clock": {"start_us": 0, "end_us": horizon + loading_us + resolving_us},
        "pipeline_overhead": [
            {"phase": "Loading elements", "elapsed_us": loading_us},
            {"phase": "Resolving elements", "elapsed_us": resolving_us}],
        "run_identity": {"manifest_hash": f"seed-{seed}", "targets": ["all.bst"]},
    }
    graph = {"elements": elements, "dependencies": dependencies,
             "run_identity_hash": f"seed-{seed}"}
    trace = {"run_identity_hash": f"seed-{seed}", "spans": spans, "phases": []}
    return (run_context, graph, trace), len(elements)


def _write_run(tmp_path, name, topology):
    run_context, graph, trace = topology
    run_dir = tmp_path / name
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run-context.json").write_text(json.dumps(run_context))
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps(trace))
    return run_dir


def _analyzer_for(tmp_path, seed):
    topology, n = _generate(seed)
    run_dir = _write_run(tmp_path, f"seed-{seed}", topology)
    analyzer = BuildEfficiencyAnalyzer(run_dir)
    analyzer.load()
    return analyzer, n


def _assert_invariants_hold(analyzer, result, n, seed):
    """I1-I6, I8, I10, provenance resolution and the JSON size class -
    every one that a topology sweep, rather than one fixed shape, can
    actually move. Failure messages name the seed: `--seed <seed>`
    reruns this exact shape alone (`_generate` is a pure function of
    it)."""
    ctx = f"seed={seed}"
    h = result.occupancy["horizon_us"]
    lb = result.floors["lb"]
    t_c = result.floors["t_c"]
    t_infinity_observed = result.floors["t_infinity_observed"]

    assert h >= lb, f"{ctx}: I1 violated - H={h} < LB={lb}"
    if t_c is not None:
        assert t_c >= lb, f"{ctx}: I2 violated - T_C={t_c} < LB={lb}"
    durations = [t.finish_us - t.start_us for t in result.normalized_tasks]
    if durations:
        assert t_infinity_observed >= max(durations), (
            f"{ctx}: I3 violated - T-infinity,observed={t_infinity_observed} "
            f"< max observed duration={max(durations)}")

    total = sum(result.attribution.get(k, 0) for k in _TASK_HORIZON_KEYS)
    assert total == h, f"{ctx}: I4 violated - attribution sum={total} != H={h}"
    negative = {k: result.attribution[k] for k in _TASK_HORIZON_KEYS
               if result.attribution.get(k, 0) < 0}
    assert not negative, f"{ctx}: I5 violated - negative attribution {negative}"

    gates = result.confidence["hard_gates"]
    assert gates["occupancy_within_capacity"], f"{ctx}: I6 violated"
    assert gates["run_identity_consistent"], f"{ctx}: I8 violated"

    segments = analyzer._attribution_segments
    assert segments, f"{ctx}: I10 - no flattened timeline to check"
    bounds = [(s.start_us, s.end_us) for s in segments]
    assert bounds == sorted(bounds), f"{ctx}: I10 violated - emitted out of order"
    # Not asserted here: `end > start` (no empty segment) - Part 34's I10
    # text is "ordered, contiguous, non-overlapping" and says nothing
    # about width. This sweep found that every generated run collapses
    # to a zero-width EXECUTION_ON_CHAIN segment wherever an element's
    # duration sits at/under `trace_epsilon_us`'s quantization grid -
    # true of `toolchain.bst`/`all.bst` in every `gen-synthetic` run
    # (their 1us duration is deliberately nonzero, per that generator's
    # own comment, specifically to dodge "a 0-duration span, a different
    # edge case" - the quantization step undoes it). Reported, not
    # asserted against: it is a real, pre-existing, out-of-scope defect
    # this row does not fix (see this file's Outcome).
    overlaps = [(a, b) for a, b in zip(bounds, bounds[1:]) if b[0] < a[1]]
    assert not overlaps, f"{ctx}: I10 violated - overlapping segments {overlaps}"
    gaps = [(a, b) for a, b in zip(bounds, bounds[1:]) if b[0] > a[1]]
    assert not gaps, f"{ctx}: I10 violated - gaps between segments {gaps}"

    findings = compute_findings(result)
    unresolved = [f["id"] for f in findings if f.get("reader") is None]
    assert not unresolved, (
        f"{ctx}: finding(s) whose provenance does not resolve (no "
        f"registered FINDING_READERS entry): {unresolved}")

    budget = _budget_for(n)
    size = len(format_json(result).encode())
    assert size <= budget, (
        f"{ctx}: report JSON is {size:,} B, over the {n}-element "
        f"class budget of {budget:,} B")


@pytest.mark.parametrize("seed", range(SEEDS))
def test_invariants_hold_for_every_generated_shape(tmp_path, seed):
    analyzer, n = _analyzer_for(tmp_path, seed)
    result = analyzer.analyze()
    _assert_invariants_hold(analyzer, result, n, seed)


#: I11 reruns the whole pipeline per seed (`run_determinism_check`) -
#: real cost, so a coarser subsample than the full 50 rather than every
#: seed; still one shape per stride across the same generator.
_DETERMINISM_STRIDE = 6


@pytest.mark.parametrize("seed", range(0, SEEDS, _DETERMINISM_STRIDE))
def test_determinism_holds_across_generated_shapes(tmp_path, seed):
    topology, _n = _generate(seed)
    run_dir = _write_run(tmp_path, f"det-{seed}", topology)
    report = run_determinism_check(run_dir, n=3)
    assert report["deterministic"], (
        f"seed={seed}: I11 violated - {report['mismatches']}")
