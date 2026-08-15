# UX-13: `LB`/Certified Headroom report text doesn't say which capacity model it certifies against

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-09`

## Motivation

`bga/floors/capacity.py:54-77`'s `compute_capacity_lower_bound` computes `LB = max_p(work_us // capacity_p)` over each non-exclusive resource, where `capacity["PROCESS"]` comes from `resource_capacities.PROCESS` (`tools/bst_extract_run.py:325`, `= builders`). This is a correct, defensible implementation of spec Part 16's own LB definition - it's not a math bug. But `UX-09` proved that "PROCESS capacity" as `bga` models it (BuildStream's own element-dispatch limit) and "real host CPU capacity" (what actually gates a `make -jN` process's speed) are two different things that can diverge sharply - and the report never says which one `LB`/`Certified Headroom` is measured against.

Checked the actual rendered report text (`bga/report/text.py`, the `Certified Floors` block, `T∞`/`LB`/`Certified Headroom`/`Efficiency Score` lines) - zero qualifying language anywhere about what "capacity" means or what it doesn't account for. A user reading `Efficiency Score: 1.00 (very efficient...)` on a run where `builders × max-jobs` is wildly oversubscribed relative to host cores (a real, measurable condition per `UX-09`) has no way to know from the report itself that the "1.00" is scored against BuildStream's own dispatch-slot model, not real CPU-core availability - the exact kind of unqualified "certified" claim spec Part 43's avoid-list warns against for other metrics (`"cold floor as certified bound"` is the closest existing example of the same failure mode: a real, correctly-computed number that reads as a stronger claim than it actually is).

## Required Fix

Add one qualifying sentence to the Certified Floors report block (`bga/report/text.py`) and to `docs/cli.md`'s description of `LB`/`Certified Headroom`: LB is certified against the run's *recorded* resource capacities (`builders`/`fetchers`/`pushers`), not real host CPU cores; a native build system's own internal parallelism (`max-jobs`) is a separate axis `bga` does not (yet) model - cross-reference `UX-09` for the evidence and `UX-12`/`UX-14` for the concrete instrumentation/modeling gaps this implies. Purely a documentation/report-text change - no math changes, keeps Part 16's LB semantics exactly as specified.

Natural follow-on once `UX-12` lands: when `native_max_jobs`/`host_cpu_count` are available and show real oversubscription, the caveat can cite the run's own actual numbers instead of a generic disclaimer.

## Out of Scope

- Changing `LB`'s formula or which resources it considers - `UX-14` is where a deeper contention-aware model would need to go, if ever attempted.

## Acceptance Test

1. `bga analyze`'s text and JSON output for the Certified Floors section includes the new qualifying language.
2. `docs/cli.md`'s `LB`/`Certified Headroom` description updated to match.
3. Full suite green (report-text snapshot/golden tests updated if any assert exact text).

## Verification Log

Not started. Filed 2026-08-15 after directly grepping `bga/report/text.py`'s Certified Floors formatting code and confirming no capacity-model caveat exists there today.
