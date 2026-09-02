# UX-26: `bga`'s batch/map-reduce opportunity report includes groups with zero real predicted savings

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — (independent, touches `UX-20`'s existing code) | **Topic:** analysis

## Motivation

Found in the same real walkthrough as `UX-25` (`bga analyze` against a fresh real `examples/05-cmake-cpp-toolchain` capture). Real output from `UX-20`'s batch/map-reduce reporting:

```text
Batch Opportunities (independent elements, simulated combined effect):
    - lib-a.bst, lib-b.bst: fixing all together -> makespan 6.40s -> 6.40s (saves 0.00s combined, vs. lib-a.bst=0.00s, lib-b.bst=0.00s fixed alone)
```

A "batch opportunity" that saves `0.00s` both combined and individually isn't an opportunity - it's noise, and real: checked `bga/structural/batching.py:105-153`'s `compute_batch_opportunities` directly - any independent group with 2+ resolvable tasks gets a `BatchGroup` entry unconditionally (`groups.append(...)` at line 149, no threshold check anywhere in the function), regardless of whether eliminating those tasks' durations would actually change the replayed makespan at all (true here: `lib-a`/`lib-b` are both off the real bottleneck path - `core → lib-a → app` - so "fixing" them changes nothing).

## Required Fix

Filter (or at minimum flag) zero/negligible-savings groups before they reach the report - e.g. skip a `BatchGroup` whose `combined_savings_us` is `0` (or below some small real threshold), or keep them in the JSON for completeness but suppress them from the text report's own printed list, which is what a user actually scans during an optimization cycle. Real design choice to make when picked up: silently dropping vs. an explicit "N further groups had no measurable combined effect, omitted" summary line - the latter is likely more consistent with this codebase's own "no silent gaps" discipline (e.g. `UX-11`'s static-binary disclaimer, `UX-19`'s honest partial-classification fallbacks) - don't just delete the information, say why it's not shown.

## Out of Scope

- Changing `compute_batch_opportunities`'s own simulation logic (`ReplayScheduler.replay` + `duration_overrides`) - correct as-is; this is a report-filtering fix only.
- Tuning what threshold counts as "negligible" beyond the literal `0.00s` case demonstrated here - a real design question (is 1ms negligible? 1% of makespan?) to resolve when implemented, not decided in this filing.

## Fix Implemented

Went with the explicit-summary-line design flagged above, not a silent drop. `bga/structural/batching.py` gained `serialize_batch_opportunities(batch_result)`, a pure report-shape helper (extracted so it's directly unit-testable without a full analyzer run) that splits `compute_batch_opportunities`'s own unfiltered `groups` on `combined_savings_us == 0`: nonzero-savings groups stay in `groups` exactly as before; zero-savings ones move to a new `omitted_zero_savings_groups` list (just `{'elements': [...]}` - the group's own element list, still visible, just not mixed into the list a user actually scans). `compute_batch_opportunities` itself (the simulation logic) is untouched, per this doc's own Out of Scope. `bga/analyzer.py` now calls `serialize_batch_opportunities` instead of building the report dict inline. `bga/report/text.py` renders `groups` exactly as before (so a genuine zero-savings group never appears there) and, when `omitted_zero_savings_groups` is non-empty, appends one line: `(N further group(s) had no measurable combined effect, omitted)` - matching this codebase's "no silent gaps" discipline (say why it's not shown, don't just delete the information).

Threshold stayed exactly the literal `0.00s` case (`combined_savings_us == 0`), per this doc's own Out of Scope - no negligible-but-nonzero tuning attempted.

Tests: 6 new (`tests/unit/test_batch_zero_savings_filtering.py`) - direct unit tests of `serialize_batch_opportunities` (zero-savings group moved out, genuine group stays, a mixed case partitions correctly, the no-groups-at-all case produces empty lists rather than missing keys) and of the text-report rendering (zero-savings group omitted with the count line shown, a genuine group still renders with its real savings figure). The pre-existing `mixed_task_kinds` golden fixture (`tests/fixtures/golden/mixed_task_kinds/expected_output.json`) needed one line added (`"omitted_zero_savings_groups": []`) since its own real batch group has genuine nonzero savings and the schema gained a key - caught immediately by `tests/test_golden.py`'s own snapshot comparison, exactly the kind of regression that test exists to catch.

## Acceptance Test

1. Re-running the exact real case in this doc's Motivation (`examples/05-cmake-cpp-toolchain`, `lib-a.bst`/`lib-b.bst`) no longer shows a `0.00s`-savings group in the default text report, and the JSON output either omits it or marks it explicitly as zero-effect (not silently indistinguishable from a real, negligible-but-nonzero result).
2. A real fixture with a genuine, nonzero-savings batch group still reports it correctly, unaffected.
3. Full suite green.

## Verification Log

Filed 2026-08-16, from the same real `bga analyze` walkthrough as `UX-25`. Implemented for real the same day. 6 new tests, full suite green (658 passed, up from 652, same 7 pre-existing environment-only failures as `main`), `make lint` clean.

Real end-to-end re-verification against a freshly captured `examples/05-cmake-cpp-toolchain` run (`--builders 4 build all.bst`, artifact cache fully cleared first): this particular run's own top-5 sensitivity ranking (`toolchain.bst`, `all.bst`, `app.bst`, `core.bst`, `lib-a.bst`) happened to land entirely on one serialized chain, so the automatic batch-opportunity pass itself found no independent groups at all (zero or nonzero) - itself a legitimate, correctly-reported outcome (`groups: []`, `omitted_zero_savings_groups: []`, real `serialized_pairs` shown), not a gap in the fix. To exercise the fix against this doc's own exact repro pair with real data, `compute_batch_opportunities`/`serialize_batch_opportunities` were invoked directly against this run's real `graph`/`replay_scheduler` for `candidates=['lib-a.bst', 'lib-b.bst']`: reproduced the doc's exact real numbers (`baseline_makespan_us=6200000`, `combined_makespan_us=6200000`, `combined_savings_us=0`), and `serialize_batch_opportunities` correctly moved it out: `{'groups': [], 'omitted_zero_savings_groups': [{'elements': ['lib-a.bst', 'lib-b.bst']}], 'serialized_pairs': []}`. Acceptance Test item 1 confirmed with real data; item 2 confirmed both by the `mixed_task_kinds` golden fixture's own real `app.bst`/`extra.bst` group (`combined_savings_us: 3000`, still reported) and by the new unit tests.
