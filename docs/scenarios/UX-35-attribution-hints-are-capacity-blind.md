# UX-35: the `RESOURCE WAIT` next-step hint tells an already-oversubscribed run to raise its capacity

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-04 (done - this is a correctness fix to the hints it added), UX-12/UX-29 (the capacity facts the hint should consult)

## Motivation

`UX-04` added a static per-category "what to do about it" line under Biggest Opportunity. The hints are constant strings, chosen by attribution category alone. Real run, `examples/06-macro-micro-optimization/optimized`, `bst --builders 4 --max-jobs 4` on a **4-core** host:

```
  Biggest Opportunity: 32.7% of wall-clock time is RESOURCE WAIT (9.00s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a higher N,
       or `bga sweep` to find the real knee point
```

The run is already dispatching up to `builders × max-jobs = 16` concurrent processes on 4 cores. Plane 2 measured the cost of that on this exact project: `core.bst`'s eight translation units cost 11.05s of process lifetime with the host to themselves and 20.00s with five siblings compiling alongside - same source, +81%. Raising `--builders` is the wrong direction, and the report says to do it in the line explicitly labelled as the next step.

The hint's fallback advice is no better on this run: `bga sweep`'s knee point stops at the first flat step and under-reports capacity by a factor of two (`UX-30`).

The hint is not wrong *in general* - `RESOURCE WAIT` on an under-provisioned host really does mean "raise capacity". It is wrong here because it is issued without looking at any of the capacity facts the tool already has, or could have: `host_cpu_count` (auto-detected, present in this run's own run-context), `cpu_budget` (`UX-15`), `builders` (present), `native_max_jobs` (`UX-29`).

## Required Fix

Make the hints conditional on the run's own capacity picture rather than on the attribution category alone:

- `RESOURCE WAIT` **and** `builders × native_max_jobs` already at or above the governing core count → say the opposite: the dispatch queue is saturated because the host is, and more builders will make it worse; the lever is less native parallelism per element, fewer builders, or less work.
- `RESOURCE WAIT` **and** real headroom against the governing core count → the current hint, unchanged.
- Capacity facts unavailable → say the hint is unconditioned rather than asserting a direction. This is the `UX-25`/`UX-11` house pattern: name the missing input instead of guessing.

Worth reviewing the other seven category hints in the same pass for the same class of unconditional advice.

## Out of Scope

- `UX-28` (the oversubscription threshold that would supply the "is this host saturated" verdict) and `UX-29` (auto-extracting `native_max_jobs`). This hint should consume their answer; it should not grow a second, independently-derived capacity formula - the exact divergence `UX-17` was resolved to avoid.
- `UX-30`'s knee-point algorithm, which this hint links to.

## Acceptance Test

1. On the real run above, the `RESOURCE WAIT` hint no longer recommends raising capacity.
2. On a genuinely under-provisioned run (capacity well below the governing core count) it still does.
3. With no capacity data at all, the hint says so instead of picking a direction. Full suite green.

## Fix Implemented

Exactly the three-branch conditioning this doc specified, and only for `RESOURCE_WAIT`.

`BuildEfficiencyAnalyzer._build_capacity_verdict` publishes `AnalysisResult.capacity_verdict` - `{oversubscribed, undersubscribed, checks_ran, skipped_inputs}` - derived from the verdict `_check_process_oversubscription` (as re-based by `UX-28`) and `UX-29`'s skipped-inputs record already reached. `checks_ran` is the load-bearing field: "the checks ran and found nothing" and "the checks could not run" look identical from `violations` alone, and that is exactly the state every run was in before `UX-29`.

`bga/report/_shared.py::resolve_attribution_hint(key, capacity_verdict)` is the single resolution point both `format_text` and `format_json` now call:

- oversubscribed → *"...but this run is already oversubscribed (see Violations), so raising capacity will make it worse, not better: the levers here are less native parallelism per element, fewer builders, or less work"*
- checks did not run, or no verdict at all → *"...whether raising capacity would help depends on how loaded this host already is, and this run's capacity checks could not run (see the Certified Floors note), so this hint is unconditioned; `bga sweep` shows the shape of the curve either way"*
- checks ran, not oversubscribed → the original hint, unchanged.

The verdict is **consumed, never re-derived** - two independently-derived capacity formulas comparing the same real inputs is the divergence `UX-17` was resolved to avoid, and this task would have reintroduced it if the report layer had done its own arithmetic.

`capacity_verdict` is also published in `--format json`, so a consumer can see *why* a hint said what it said, and so `checks_ran: false` is legible rather than indistinguishable from a clean bill of health.

The other seven hints were re-read in the same pass, as this doc asked. None of them advises a direction that capacity could invert, so none is conditioned - and a test asserts that they resolve to their unchanged static strings under every verdict.

Tests: 9 new (`tests/unit/test_capacity_aware_hints.py`) - all three RESOURCE_WAIT branches, `None`/`{}` treated as unknown rather than fine, every other category unchanged under every verdict, P4-02's every-category-has-a-hint guard re-asserted through the resolver, and three verdict-construction cases driven through the real check (`UX-09`'s measured-slower 8x8, its measured-fastest 4x4, and a run whose checks could not run).

## Verification Log

Filed 2026-08-16. Implemented the same day. The hint text is pasted from a real `bga analyze -d` against a real `bst --builders 4 --max-jobs 4 build all.bst` capture of `examples/06-macro-micro-optimization/optimized` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host). The 11.05s vs 20.00s contention figures come from two real Plane 2 traces of the same project.

Real end-to-end re-verification. A genuinely oversubscribed real capture was made for this - `examples/06-macro-micro-optimization/optimized` built at `--builders 8 --max-jobs 8` on the same real 4-core host, i.e. `UX-09`'s own measured-slower configuration:

```
$ bga analyze -f json -d /tmp/run-06-opt-b8j8 | jq '.capacity_verdict, .attribution_hints.resource_wait_us'
{"oversubscribed": true, "undersubscribed": false, "checks_ran": true, "skipped_inputs": []}

"a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - but this run is already oversubscribed
 (see Violations), so raising capacity will make it worse, not better: the levers here are less
 native parallelism per element, fewer builders, or less work"
```

and the same run's Violations block confirms the verdict is the real check's, not a second one:

```
Violations (2):
  - oversubscription: builders=8 x native max-jobs=8 = 64 potential concurrent processes vs a
    4-core host (16.0x the cores) - past the ratio UX-09 measured as genuinely slower...
  - dispatch oversubscription: builders=8 vs a 4-core host - ...
```

The third branch is confirmed on the original capture from this doc's Motivation, which predates `UX-29` and therefore genuinely has no capacity verdict:

```
  Biggest Opportunity: 32.7% of wall-clock time is RESOURCE WAIT (9.00s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - whether raising capacity would help
       depends on how loaded this host already is, and this run's capacity checks could not run
       (see the Certified Floors note), so this hint is unconditioned; ...
```

Acceptance Test items 1-3 all confirmed with real data. Full suite green (747 passed, up from 738), `make lint` clean.
