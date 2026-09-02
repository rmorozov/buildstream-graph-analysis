# UX-79: the efficiency gate is a whole-build average, so a bad diff dilutes with project size

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-39, UX-74 (both done) | **Topic:** analysis

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
under `docs/audits/round-10.md`'s protocol — two elements added well vs
badly to `examples/06/optimized`):

1. compare JSON lists exactly `lib-g.bst`/`lib-h.bst` as new in both
   pairs, with per-element critical-path delta;
2. the marginal gate passes grow-good and fails grow-bad;
3. **scale invariance**: synthesize the same two additions onto the
   1202-element scale fixture (`tools.gen_synthetic_scale_run` + two
   appended elements) and show the marginal gate still fails the bad
   add there, where the whole-build occupancy delta is <1pp and the
   existing gate provably passes it.

## Fix Implemented

A marginal gate, and the per-element diff underneath it.

**`element_diff`** — `new` / `removed` / `moved_onto_critical_path`, each
with the element's measured duration and whether it is on the candidate's
critical path, published in `bga compare --format json`.

**`marginal_efficiency`** — `stretch = added_critical_path_us /
added_work_us`, over the added elements only:

- **0.0** — the additions were fully absorbed by existing parallelism.
- **1.0** — every second of added work extended the chain.

**`--fail-on-inefficient-additions`** (exit 5, with
`--max-addition-stretch`, default 0.5).

### The scale-invariance measurement, which is the whole point

The same two maximally-mis-added elements, at two project sizes:

| project size | whole-build occupancy | `--fail-on-efficiency-regression` | marginal stretch |
|---|---|---|---|
| 11 elements | −14.6pp | **fails (5)** | 1.00 |
| 1201 elements | **−0.5pp** | **passes (0)** | **1.00** |

Both rows are asserted in
`tests/unit/test_marginal_efficiency_gate.py::test_the_marginal_gate_is_scale_invariant`
and, at the CLI level, in
`test_the_gate_still_fails_the_bad_add_where_the_whole_build_gate_goes_blind` —
so the claim that the old gate goes blind is not an argument in a
document, it is a test that fails if it stops being true.

The default threshold comes from that gap: a well-added pair scores 0.00
and a serialized pair 1.00, at *both* scales, so 0.5 is a wide margin
either side rather than a number tuned to one project.

### One thing this needed that did not exist

`critical_path_detail` covers the path and `wall_clock_share` is
amortized, so nothing published "how long did this element take" for an
element *off* the path — and a well-added element is off the path by
construction, which would have scored every good addition as zero added
work. `signals.element_durations` now publishes every element's measured
duration; the compare side falls back to the old path-only view for an
analysis produced before this, which makes the metric decline to judge
rather than judge wrongly.

### Deliberate limits

- **A change that adds no elements is an empty check and says so**
  rather than reporting green — `UX-87`'s lesson applied before that task
  is fixed. The whole-build gate remains the one that catches an
  *existing* element getting worse, which is why it stays.
- `moved_onto_critical_path` is computed and published but does not gate.
  It is the other way a change makes a build worse, and it needs its own
  threshold argument rather than being folded into this one.
- The successor metric named in Out of Scope — Plane 2 CPU-vs-wall
  stretch — is still the better measure, and still needs Plane 2 in CI.

Tests: 9 new in `tests/unit/test_marginal_efficiency_gate.py`. Golden
snapshot regenerated (additive `element_durations` only). Suite:
1127 → 1136.

## Verification Log

Fixed 2026-08-18. The two-scale table was measured with the fixtures now
in `tests/unit/test_marginal_efficiency_gate.py`, at 11 and 1201
elements, through `compare_runs` and through the CLI's real exit codes.
