# UX-13: `LB`/Certified Headroom report text doesn't say which capacity model it certifies against

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-09` | **Topic:** analysis

## Motivation

`bga/floors/capacity.py:54-77`'s `compute_capacity_lower_bound` computes `LB = max_p(work_us // capacity_p)` over each non-exclusive resource, where `capacity["PROCESS"]` comes from `resource_capacities.PROCESS` (`tools/bst_extract_run.py:325`, `= builders`). This is a correct, defensible implementation of spec Part 16's own LB definition - it's not a math bug. But `UX-09` proved that "PROCESS capacity" as `bga` models it (BuildStream's own element-dispatch limit) and "real host CPU capacity" (what actually gates a `make -jN` process's speed) are two different things that can diverge sharply - and the report never says which one `LB`/`Certified Headroom` is measured against.

Checked the actual rendered report text (`bga/report/text.py`, the `Certified Floors` block, `T∞`/`LB`/`Certified Headroom`/`Efficiency Score` lines) - zero qualifying language anywhere about what "capacity" means or what it doesn't account for. A user reading `Efficiency Score: 1.00 (very efficient...)` on a run where `builders × max-jobs` is wildly oversubscribed relative to host cores (a real, measurable condition per `UX-09`) has no way to know from the report itself that the "1.00" is scored against BuildStream's own dispatch-slot model, not real CPU-core availability - the exact kind of unqualified "certified" claim spec Part 43's avoid-list warns against for other metrics (`"cold floor as certified bound"` is the closest existing example of the same failure mode: a real, correctly-computed number that reads as a stronger claim than it actually is).

## Required Fix

Add one qualifying sentence to the Certified Floors report block (`bga/report/text.py`) and to `docs/guides/cli.md`'s description of `LB`/`Certified Headroom`: LB is certified against the run's *recorded* resource capacities (`builders`/`fetchers`/`pushers`), not real host CPU cores; a native build system's own internal parallelism (`max-jobs`) is a separate axis `bga` does not (yet) model - cross-reference `UX-09` for the evidence and `UX-12`/`UX-14` for the concrete instrumentation/modeling gaps this implies. Purely a documentation/report-text change - no math changes, keeps Part 16's LB semantics exactly as specified.

Natural follow-on once `UX-12` lands: when `native_max_jobs`/`host_cpu_count` are available and show real oversubscription, the caveat can cite the run's own actual numbers instead of a generic disclaimer.

## Fix Implemented

`BuildEfficiencyAnalyzer._build_capacity_model_note` (`bga/analyzer.py`) computes a single-source-of-truth note, stored as `result.floors['capacity_model_note']` right after `result.floors` is assembled - both `--format text` (`bga/report/text.py`'s `_format_capacity_model_note`, appended to the Certified Floors block) and `--format json` (`floors` is serialized as-is) read the same value, satisfying the acceptance test's "text and JSON" requirement without duplicating the logic.

Always present (not conditional on `UX-12`'s fields being available) - a generic disclaimer by default: *"LB/Efficiency Score certify against this run's recorded resource capacities (builders/fetchers/pushers), not real host CPU cores - native build-system parallelism (--max-jobs) is a separate, currently unmodeled axis (see UX-09)."* When `UX-12`'s `resource_oversubscription` violation fired for this run, the note is enriched with the run's own real numbers instead: *"This run shows real resource oversubscription (builders=8 x native max-jobs=8 = 64 processes on a 4-core host) - LB/Efficiency Score certify against recorded resource capacities, not real host CPU cores, so Efficiency Score may overstate real efficiency here (see UX-09)."* - exactly the "natural follow-on" this task's own doc anticipated once `UX-12` landed.

`docs/guides/cli.md`'s Certified Floors description updated with the same qualifying language and cross-references to `UX-09`/`UX-12`.

No changes to `LB`'s formula, `bga/floors/capacity.py`, or any numeric output - purely additive report text, matching Part 16's LB semantics exactly as specified.

## Out of Scope

- Changing `LB`'s formula or which resources it considers - `UX-14` is where a deeper contention-aware model would need to go, if ever attempted.

## Acceptance Test

1. `bga analyze`'s text and JSON output for the Certified Floors section includes the new qualifying language.
2. `docs/guides/cli.md`'s `LB`/`Certified Headroom` description updated to match.
3. Full suite green (report-text snapshot/golden tests updated if any assert exact text).

## Verification Log

Fixed and re-verified for real, 2026-08-15. New tests: `tests/unit/test_capacity_model_note.py` (6 tests - generic note present when `UX-12` fields are unavailable, enriched with real numbers when oversubscribed, stays generic when not, present in both `--format text`'s Certified Floors block and `--format json`'s `floors` section, and present in `bga floors`'s own narrower JSON output too). Golden fixture (`tests/fixtures/golden/mixed_task_kinds/expected_output.json`) updated with the new `capacity_model_note` field. Full suite green (`make lint`, `pytest` - 482 passed, same 7 pre-existing environment-only failures as `main`).

Real re-verification against the same `examples/05-cmake-cpp-toolchain` real build logs used for `UX-12`'s own verification (`/tmp/05-runs/build-b4j4.log`, `build-b8j8.log`, real 4-core host): the `4×4` run's Certified Floors block shows the generic note (`"LB/Efficiency Score certify against this run's recorded resource capacities..."`); the `8×8` run's Certified Floors block shows the enriched note naming the real numbers (`"This run shows real resource oversubscription (builders=8 x native max-jobs=8 = 64 processes on a 4-core host)..."`) - both directly under an unchanged `Efficiency Score: 1.00` line, exactly the "a high score doesn't rule out real contention" case this task exists to surface.
