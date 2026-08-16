# UX-40: real captures land at ~0.69 confidence because BuildStream's own startup counts against `attribution_score`, and the CI gate fails open below 0.8

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-03 (the gate), UX-10 (which introduced the real wall-clock horizon this interacts with)

## Motivation

`bga compare --fail-on-regression` fails **open** when either run's confidence is below `_CONFIDENCE_HIGH = 0.8` (`bga/compare.py` → `low_confidence`, `bga/cli.py::_compare_exit_code`). That is a defensible design: do not fail a pipeline on data you do not trust.

The problem is what real data scores. Real capture, `examples/05-cmake-cpp-toolchain`, `bst --builders 4 --max-jobs 4 build all.bst`, produced by the exact pipeline `README.md` documents:

```
Confidence:
  Overall: 0.69 (medium)

  "provenance_score": 1.0,
  "coverage_score": 1.0,
  "model_score": 1.0,
  "attribution_score": 0.694058856191005,
  hard_gates: all true, ordering_violations: 0
```

Every hard gate passes. Provenance, coverage and model are perfect. The single input dragging the score to "medium" is `attribution_score`, which is `1 - (untracked + ambiguous + violations) / full_horizon`. On this run `untracked_head_us` is 3.17s of a 10.8s build - 29.3% - and it is not a data-quality problem at all. It is BuildStream starting up: loading and resolving elements, querying the cache, staging the sandbox. `UX-10` deliberately made `total_duration_us` prefer real wall-clock precisely so this time would stop being invisible, and the side effect is that measuring it now penalizes the run's own confidence.

The interaction is systematic, not incidental: **the shorter the build, the larger BuildStream's fixed startup is as a fraction of it, and the lower the confidence.** Small and medium projects - the ones most likely to be in a fast CI loop - are the ones most likely to fall below 0.8 and silently have their regression gate disabled. On the larger `examples/06-macro-micro-optimization` runs the same startup is 7.7% of a 39.6s build and confidence is 0.92, so the gate works there. A CI owner who validated the gate on a big project and then applied it repo-wide would get silent pass-through on the small ones.

Nothing in `bga compare`'s text output states that the gate was disabled. `low_confidence` is in the JSON; the human-readable comparison prints the two confidence numbers and no consequence.

## Required Fix

Two independent changes, both probably wanted:

1. **Stop penalizing measured pipeline overhead as if it were unattributed time.** `untracked_head_us` that is fully explained by `run_context.pipeline_overhead` (which `bga` already parses and reports as its own section - `Loading elements`, `Resolving elements`, `Initializing remote caches`, `Query cache`) is *accounted-for* time, not ambiguous time. Subtracting the explained portion from `penalized_us` is faithful to what `attribution_score` is for (Part 33.4: untracked, ambiguous, violation time) - genuinely unexplained head/tail should still count. On the run above, `Resolving elements` alone accounts for 1.89s of the 3.17s head.
2. **Make the fail-open loud.** When `--fail-on-regression` declines to fail because of low confidence, say so on stdout, and give the pipeline a way to opt out of failing open (`--fail-on-low-confidence`, or a distinct exit code). A gate that silently stops gating is worse than no gate, because the pipeline reports green.

Worth deciding at the same time whether `_CONFIDENCE_HIGH = 0.8` is the right bar once (1) lands, or whether the gate should key on the hard gates plus specific sub-scores rather than on the single `min()`-derived primary.

## Out of Scope

- `UX-10`'s wall-clock horizon, which is correct and should not be reverted - measuring startup honestly is right; only its confidence treatment is wrong.
- Reducing BuildStream's actual startup cost, which is not `bga`'s to fix (though naming it is useful, and the Pipeline Overhead section already does).
- `UX-39`'s efficiency gate, which is blocked by this in practice: any new gate inherits the same fail-open rule.

## Acceptance Test

1. A real `examples/05-cmake-cpp-toolchain` capture whose entire untracked head is explained by `pipeline_overhead` scores "high" confidence, and its `--fail-on-regression` gate is live.
2. A capture with genuinely unexplained untracked time still scores lower, by the unexplained amount.
3. `bga compare --fail-on-regression` prints a visible line when it declines to fail due to low confidence.
4. Hard-gate failures still force low confidence regardless. Full suite green.

## Verification Log

Filed 2026-08-16. The confidence block is from a real `bga analyze -f json -d` against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host), extracted with the documented `tools/bst_run_wrapped` + `tools/bst_extract_run --format wrapped` pipeline; the 0.92 figure for `examples/06-macro-micro-optimization` is from the same session. `_CONFIDENCE_HIGH = 0.8`, the `low_confidence` rule and the `attribution_score` formula were read directly from `bga/report/text.py`, `bga/compare.py` and `bga/validation/invariants.py`.
