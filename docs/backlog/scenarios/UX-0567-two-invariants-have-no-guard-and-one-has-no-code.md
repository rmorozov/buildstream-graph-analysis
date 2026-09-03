# UX-567: two invariants have no guard, and one has no code

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** anyone trusting the report's `I1..I13` line | **Topic:** guards

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
