# UX-692: the invariants hold for any shape — a seeded sweep over generated projects

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-465 (a project from a topology spec), UX-567 (the invariant guards), UX-367 (the volume budget) | **Serves:** R8 trusting the report on a graph nobody fixtured | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

The suite has no randomized test: every guard runs on the committed
fixtures and the one seeded scale run. The tool already has two
generators — `bga gen-synthetic --seed` (schedules) and
`bga_gen_project.py` (a BuildStream project from a topology spec,
`UX-465`) — and thirteen invariants plus a determinism guard that
should hold for *any* input. A hand exploration on a shape nobody
fixtured is what finds problems; a seed sweep is that exploration,
mechanised.

## Required Fix

A weekly CI job (and `make test-seeds N=…` locally): N seeds over
topology shapes (layers, width, kinds mix, chain/mesh, structural
share) through `gen-synthetic`, asserting I1-I13, determinism, the
volume budget at the class, and that every finding's provenance
resolves; each failing seed is committed as a fixture with its
filing. Cheap by construction — no browser, no `bst` — and the
input space the unit files never reach.

## Out of Scope

- Generated *real* builds — `UX-465`'s projects run under the bst
  tier and stay there; this sweep is the analysis half.

## Acceptance Test

A run of 50 seeds green; a planted invariant violation in the
replay scheduler — the sweep reds on a seed and names it; the seed
reruns red alone.

## Outcome

**The gap, measured.** Every I1-I13 guard before this file ran on
committed fixtures (`grep -rlE "\bI[0-9]+\b" tests/unit | wc -l`, per
`UX-567`) or the one seeded 1,202-element scale run - never a shape
drawn per seed. `tests/unit/test_the_invariants_hold_for_any_shape.py`
generates one: layers 2-8, width 2-25, builders 1-12, chain or mesh
fan-in, a five-kind mix, up to 35% of elements structural (0-1us),
up to 15% runtime edges - a self-contained generator (see the file's
own docstring for why not `bga gen-synthetic` directly: no knob for
this mix, and adding one is a `tools/` change outside this row's
declared surfaces).

**The close, measured.**

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_invariants_hold_for_any_shape.py -q
59 passed in 4.93s / 5.17s / 5.12s   (three single-process runs, MEDIUM tier)
```

50 seeds assert I1, I2, I3, I4, I5, I6, I8, I10 (order/contiguity/
non-overlap - see the found defect below), every finding's provenance
(`FINDING_READERS`), and a report-JSON-size budget per element-count
class; a 9-seed stride reruns each shape through `run_determinism_check`
(I11, n=3).

**A real violation, found without a planted mutation.** Every
generated run - and `bga gen-synthetic --seed 1` itself, no sweep
needed - produces a zero-width `EXECUTION_ON_CHAIN` segment for any
element whose duration sits at/under `trace_epsilon_us`'s quantization
grid: `toolchain.bst`/`all.bst` (1us, by that generator's own
convention) collapse on every seed, and this sweep's `structural_share`
knob shows it is not just the two endpoints - an interior 1us element
collapses identically. `bga/normalize/timestamps.py::quantize_timestamp`
rounds both start and finish into the same bucket. Reported here, not
fixed (`bga/` out of scope for this row): I10's literal text ("ordered,
contiguous, non-overlapping") still holds through a zero-width segment,
so the sweep asserts exactly that and not the stricter "no empty
segment" `test_attribution_identity_across_topologies.py` layers onto
its own ten hand-built fixtures (which never use a sub-epsilon
duration). This is a candidate for its own item.

**Mutations verified red and reverted (5).**

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | `ReplayScheduler.replay`: `makespan = 0` | I2, every seed; seed 0 reruns identically alone | 50 failed, 9 deselected |
| 2 | `_compute_attribution`: `idle_us` +1 | I4, every seed | 50 failed, 9 deselected |
| 3 | drop `"confidence"` from `FINDING_READERS` | provenance-resolves, every seed | 50 failed, 9 deselected |
| 4 | `DATA_BUDGETS` large-class bound to 1,000 B | the volume budget, the seeds over ~60 elements | 23 failed, 27 passed |
| 5 | `format_json` appends a random `_probe` field | I11 (determinism), the sampled seed | 1 failed |

Each reverted from the untouched copy kept before mutating; `bga/`
carries no diff (`git diff --stat bga/` empty) after all five.
