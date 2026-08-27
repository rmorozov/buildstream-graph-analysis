# UX-336: the loop that got slow, measured and re-tooled

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-238 (the tiers this extends), the verify/falsify/measure skills | **Serves:** the maintainers — every future round's throughput | **Topic:** guards

## Motivation

The user's observation: the implementing session slows down as the
code and suite grow — and the numbers agree. The suite is 4,000+
tests at ~6 minutes single-process; each task's ritual (guards,
mutation records, row moves, log writing) has fixed costs that
were designed at half this size; and the two largest viewer
modules are long enough that every edit pays a long read. Round 46
measured the levers — and the trial already ran: `pytest-xdist -n auto` on this
4-core container takes the full suite from **~375 s to 148.7 s
(2.5×), 4,014 passed, zero failures, zero races** — every server
already binds ephemeral ports, so the adoption cost measured
*zero* (one caveat: the 94-skip census should be diffed against a
single-process run once). Meanwhile the "fast" tier is not:
small+medium is 3,849 tests at **335 s wall** — five and a half
minutes is nobody's inner loop. The browser walks are already
frugal (three files, one shared Chromium each, ~20 % of
single-process time); the slow tail is the scale files
(`test_the_page_has_geometry` 61.7 s, the spine pair 62.7 s
together, memory-shape 24.6 s).

## Required Fix

Five levers, each cheap and additive:

1. **The suite runs in parallel.** `pytest-xdist` joins the dev
   extras with the measured result above; the one adoption step
   left is diffing the skip census against a single-process run.
   The tiers stay; `-n auto` becomes how every tier runs — the
   full suite lands at ~2.5 minutes.
2. **A change-scoped inner loop.** `make test-touching` maps the
   working diff to the test files that import or name the touched
   modules (grep-derived, no new machinery) — the inner loop runs
   seconds of tests, the full suite runs once before commit, as
   the verify skill already prescribes.
3. **The fast tier becomes fast again.** small+medium at 335 s is
   a mis-tiering, not a law: re-tier by the fresh measurement (the
   UX-238 method, re-run), with the scale files and browser walks
   in the once-per-close tier — under xdist the inner tier should
   sit near 30 s.
4. **The close ritual is scaffolded.** A `close-task` helper
   generates the Outcome skeleton, the mutation-record table, and
   the row move — the mechanical tail of every task stops being
   hand-typed (the verify skill documents what it generates).
5. **The two largest viewer modules split along chapter seams** —
   page-cost neutral (the export inlines either way), edit-cost
   real: smaller files, fewer collisions, shorter reads. The
   module-map guard (UX-294) keeps the map true.

## Out of Scope

- Deleting or weakening any guard — the loop gets faster around
  the discipline, never through it.
- CI restructuring beyond adopting the same parallelism — CI is
  not the slow loop; the local iteration is.

## Acceptance Test

Full suite under `-n auto` green with wall time recorded here
(target: the measured trial's number, held by a soft ceiling in
the docs not a guard); `make test-touching` on a one-module diff
selects and passes its file set in under 30 s (measured);
the browser tier runs Chromium once per session (instance count
asserted in the harness); the close-task helper's output matches
the verify skill's checklist (skill text cites the helper).
