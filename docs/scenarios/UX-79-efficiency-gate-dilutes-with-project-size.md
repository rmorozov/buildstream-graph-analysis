# UX-79: the efficiency gate is a whole-build average, so a bad diff dilutes with project size

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-39, UX-74 (both done)

## Motivation

The build owner's CI requirement, in their own words: *adding new
elements and making the build slower is fine; adding them in an
unoptimized way is not — there is a level of inefficiency the owner
considers normal, and a big regression past it must be spotted and
stopped.* `--fail-on-efficiency-regression` was built for exactly this,
and on a small project it works. Measured in this round, on real builds
of `examples/06/optimized` (11 elements, 4-core host):

| change (2 elements added) | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| fan-out off `core.bst`, `-j4` | +4.7% | fails (exit 4) | 61.2% → 72.3% | **passes** |
| chained after everything, `notparallel` | +19.0% | fails (exit 4) | 61.2% → 55.1% | **fails (exit 5)** |

That is the right discrimination — and the margin is the warning. The bad
add moved global occupancy by **6.1pp against the 5.0pp default**: two
maximally-mis-added elements in an *eleven*-element project barely
tripped the gate. Occupancy is a whole-build average, so the same two
elements added to the 90-element `freedesktop-sdk` closure would move it
by well under 1pp and pass. The gate's sensitivity is inversely
proportional to project size, which means it is weakest exactly where a
CI gate matters most — and a growing project *approaches* the blind spot
with every element added.

## Required Fix

A **marginal** gate: judge the efficiency of the change, not the
repository. `bga compare` already knows both graphs; the pieces are:

1. **Per-element diff** (the `design-directions.md` 2b item): classify
   elements as new / removed / changed-duration / changed-position
   relative to the critical path, published in compare's JSON.
2. **A marginal efficiency verdict for the new/changed set**: for each
   new element, its own occupancy contribution and critical-path delta —
   "`lib-h.bst` added 4.1s of critical path and ran serialized behind
   `lib-g.bst`" — and a gate flag (`--fail-on-inefficient-additions`)
   that fires on the *new elements'* aggregate stretch (e.g. added
   critical-path time / added work time above a configurable ratio),
   independent of project size.
3. The existing whole-build gate stays; it catches global serialization
   regressions the marginal gate cannot (a changed old element).

The CI-comment sketch at the end of `design-directions.md` ("New elements
this change: … `lib-h.bst` 4.1s serialized behind `lib-g.bst`") is the
target rendering; this task makes it computable.

## Out of Scope

- Plane 2-based per-element CPU stretch (real CPU vs wall) as the
  marginal metric — better, but needs Plane 2 in CI; note it as the
  successor metric.
- Multi-run baseline banding (exists; composes with this).

## Acceptance Test

Re-run this round's grow-good / grow-bad experiment (captures preserved
under `docs/audit-round-10.md`'s protocol — two elements added well vs
badly to `examples/06/optimized`):

1. compare JSON lists exactly `lib-g.bst`/`lib-h.bst` as new in both
   pairs, with per-element critical-path delta;
2. the marginal gate passes grow-good and fails grow-bad;
3. **scale invariance**: synthesize the same two additions onto the
   1202-element scale fixture (`tools.gen_synthetic_scale_run` + two
   appended elements) and show the marginal gate still fails the bad
   add there, where the whole-build occupancy delta is <1pp and the
   existing gate provably passes it.
