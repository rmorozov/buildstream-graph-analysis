# UX-26: `bga`'s batch/map-reduce opportunity report includes groups with zero real predicted savings

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — (independent, touches `UX-20`'s existing code)

## Motivation

Found in the same real walkthrough as `UX-25` (`bga analyze` against a fresh real `examples/05-cmake-cpp-toolchain` capture). Real output from `UX-20`'s batch/map-reduce reporting:

```
Batch Opportunities (independent elements, simulated combined effect):
    - lib-a.bst, lib-b.bst: fixing all together -> makespan 6.40s -> 6.40s (saves 0.00s combined, vs. lib-a.bst=0.00s, lib-b.bst=0.00s fixed alone)
```

A "batch opportunity" that saves `0.00s` both combined and individually isn't an opportunity - it's noise, and real: checked `bga/structural/batching.py:105-153`'s `compute_batch_opportunities` directly - any independent group with 2+ resolvable tasks gets a `BatchGroup` entry unconditionally (`groups.append(...)` at line 149, no threshold check anywhere in the function), regardless of whether eliminating those tasks' durations would actually change the replayed makespan at all (true here: `lib-a`/`lib-b` are both off the real bottleneck path - `core → lib-a → app` - so "fixing" them changes nothing).

## Required Fix

Filter (or at minimum flag) zero/negligible-savings groups before they reach the report - e.g. skip a `BatchGroup` whose `combined_savings_us` is `0` (or below some small real threshold), or keep them in the JSON for completeness but suppress them from the text report's own printed list, which is what a user actually scans during an optimization cycle. Real design choice to make when picked up: silently dropping vs. an explicit "N further groups had no measurable combined effect, omitted" summary line - the latter is likely more consistent with this codebase's own "no silent gaps" discipline (e.g. `UX-11`'s static-binary disclaimer, `UX-19`'s honest partial-classification fallbacks) - don't just delete the information, say why it's not shown.

## Out of Scope

- Changing `compute_batch_opportunities`'s own simulation logic (`ReplayScheduler.replay` + `duration_overrides`) - correct as-is; this is a report-filtering fix only.
- Tuning what threshold counts as "negligible" beyond the literal `0.00s` case demonstrated here - a real design question (is 1ms negligible? 1% of makespan?) to resolve when implemented, not decided in this filing.

## Acceptance Test

1. Re-running the exact real case in this doc's Motivation (`examples/05-cmake-cpp-toolchain`, `lib-a.bst`/`lib-b.bst`) no longer shows a `0.00s`-savings group in the default text report, and the JSON output either omits it or marks it explicitly as zero-effect (not silently indistinguishable from a real, negligible-but-nonzero result).
2. A real fixture with a genuine, nonzero-savings batch group still reports it correctly, unaffected.
3. Full suite green.

## Verification Log

Filed 2026-08-16, from the same real `bga analyze` walkthrough as `UX-25` - not implemented.
