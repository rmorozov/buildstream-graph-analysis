# UX-567: two invariants have no guard, and one has no code

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Serves:** anyone trusting the report's `I1..I13` line | **Topic:** guards

## Motivation

Part 34's thirteen invariants, mapped to the tests that name them:

```text
I1 I2 I3 I4 I5 I8 I9 I11 I12       named by a guard file (135 passed across the 15 adjacent files)
I6  occupancy never exceeds declared capacity      no guard · no code: grep capacity bga/occupancy/sweep.py → 0
I7  blame_chain_coverage                           invariants.py:125 defines it as attribution_sum/horizon — I4 restated; no test names it
I10 segments are adjacent and non-overlapping      no guard: grep "end_us == .*start_us" tests/unit → 0 (I4's exact sum implies coverage, not non-overlap)
I13 partial history unavailable unless allowed     held by behaviour (test_cold_floor.py:118), not by id
```

## Required Fix

- I6 computed in the occupancy sweep and gated (a hard gate under
  Part 33 — a run whose occupancy exceeds a declared capacity is a
  broken capture, not a finding).
- I10 asserted on the attribution segments of every fixture the I4
  guards already walk: sorted, `end_us == next.start_us`, no overlap.
- I7 either becomes a distinct quantity or Part 32 records it as I4's
  alias; I13's guard names it.
- An `I# → test file` map held as a guard, the `test_i3_and_span_status.py`
  style, with an explicit waiver list — so a fourteenth invariant
  cannot arrive unguarded.

## Out of Scope

- Re-deriving the nine that are held — their guards were run this round (135 passed) and discriminate.

## Acceptance Test

Mutation: plant an occupancy above capacity in a fixture — the I6
gate reds; overlap two segments — I10 reds; drop an entry from the
map — the map guard reds.

## Outcome

**The gap, re-measured at `5b4c05f`.** The Motivation's four holes all
stand; the counts around them had moved (21 files name an id, not 15):

```text
$ grep -c capacity bga/occupancy/sweep.py                 0
$ grep -rn "end_us == .*start_us" tests/unit | wc -l      0
$ for i in 1..13; grep -rlE "\bI$i\b" tests/unit/*.py | wc -l
I1 1  I2 1  I3 2  I4 9  I5 1  I6 0  I7 0  I8 1
I9 5  I10 0  I11 2  I12 1  I13 0
```

I13's behaviour guard is `test_cold_floor.py:119`, not `:118`.
`invariants.py:126` computes `blame_chain_coverage` from I4's own six
keys over I4's own H, so I7 is I4 as a ratio — recorded, not rebuilt.

I10 and I6 were both **true and unasserted** on every fixture the I4
guards walk (probe over the ten topologies, before any change):

```text
linear_chain     caps={'PROCESS': 1} peak={'PROCESS': 1} over={} gaps=0 overlaps=0
diamond          caps={'PROCESS': 2} peak={'PROCESS': 2} over={} gaps=0 overlaps=0
fan_in/fan_out   caps={'PROCESS': 4} peak={'PROCESS': 4} over={} gaps=0 overlaps=0
... 10 of 10: over={} gaps=0 overlaps=0 covers_horizon=True
```

and on all eleven committed run fixtures (`git ls-files
'tests/fixtures/**run-context.json'`): `over_declared={}` on every one,
so the new hard gate fires on nothing this repository ships.

**The close, measured.**

```text
$ python3 -m pytest tests/unit/test_occupancy_within_capacity.py \
    tests/unit/test_every_invariant_has_a_guard.py \
    tests/unit/test_attribution_identity_across_topologies.py \
    tests/unit/test_cold_floor.py -q
92 passed in 0.56s

$ make test-touching     87 file(s) selected · 1575 passed, 52 skipped in 63.63s
$ make test-small        3752 passed, 36 skipped in 28.07s
$ make test-medium       2289 passed, 53 skipped in 230.76s
```

I6's cost is one extra sweep, and it short-circuits where nothing is
declared. On the 1,202-element synthetic (`gen-synthetic --seed 1`):

```text
compute_capacity_excursions    min=3.83ms  median=3.88ms
compute_occupancy_segments     min=5.49ms  median=6.30ms
```

**Mutations.**

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | `'occupancy_within_capacity': not capacity_excursions` → `True` | the four `TestTheGateFires` cases | 4 failed, 8 passed |
| 2 | the gate reads `compute_default_capacities(run_context)` | both `TestTheGateDoesNotFireOnAGuess` cases naming an undeclared resource | 2 failed, 10 passed |
| 3 | `_build_flattened_timeline` shifts segment[1] back 1 µs — an overlap with a compensating gap, Σ unchanged | I10 on all ten topologies; **I4's 30 stayed green**, which is the item's premise measured | 10 failed, 30 passed |
| 4 | drop `"I6"` from `GUARDS` | `test_every_declared_invariant_is_guarded_or_waived` | 1 failed, 29 passed |
| 5 | remove `I13` from `test_cold_floor.py`'s docstring | `test_the_named_file_names_the_invariant[I13]` | 1 failed, 31 passed |
| 6 | renumber `### 32.7.4` to `32.7.5` | `test_the_waiver_names_a_registry_row_the_spec_carries[I7]` | 1 failed, 31 passed |

Mutation 3 is the one that matters: it is exactly the shape I4 cannot
see, and it reddened only the new guard.

**Guards that did not discriminate:** none withdrawn. I10's *overlap*
clause cannot fire alone on today's builder without a compensating gap —
the fill step turns a bare overlap into a Σ ≠ H that I4 already catches.
It is kept because a builder that stops filling would not be caught.

**Deviation from the Required Fix:** the excursion list is published as
the violation's `detail` only, not as a `confidence` key. A key that is
`[]` on every healthy run buys nothing the `hard_gates` bool and the
violation do not already carry. I7 took the alias branch, not the
distinct-quantity branch.

## Addendum (round 83, at the merge)

`UX-568`'s allowlist carried Part 29 as unguarded, written against a
base where `duration_variability` reached no consumer. `UX-565` landed
in the same round and made that false. The clause
`test_an_allowlisted_part_that_gained_a_guard_leaves_the_list` reddened
on the merge and named the file that had taken the Part:

```text
AssertionError: Part(s) [29] are allowlisted and also named by
[['test_part_29_reads_the_store_it_has.py']] - drop the row
```

The row is dropped. This is the guard doing the job it was built for
across two items of one round, which is the case a single track cannot
test for itself.
