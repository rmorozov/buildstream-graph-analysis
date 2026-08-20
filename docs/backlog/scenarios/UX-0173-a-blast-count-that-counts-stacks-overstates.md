# UX-173: a blast count that counts stacks overstates

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (shares the weighting), UX-156/UX-164 (the honest-counting precedent)

## Motivation

The user's first sentence, taken literally: *blast analysis doesn't
take element kind into consideration.* `compute_downstream_count`
counts elements; the diagnostics ranking and the Key Findings block
rank by that count; and `graph.json` has carried `element_kind` all
along. A blast of 84 where 39 are `stack`s and 4 `import`s (no build
commands — their "rebuild" is a cache-key recomputation and an
assemble) is not a blast of 84 in any currency the user spends. The
compare-time invalidation note has the same blindness in its cost
line: "invalidated 3 element(s) below it, 11.3s of rebuilding" sums
whatever rebuilt, but the *count* it leads with treats a stack like a
cmake element. This is the counting class UX-164 just fixed for
cache hits ("0 of 7 scheduled") — same fix, one analysis over.

## Required Fix

1. Blast counts everywhere split into **building kinds vs assembling
   kinds** (kinds with build commands vs `stack`/`import`/`filter`/
   `junction`-like; the split derived from the graph's own
   `element_kind`, with unknown kinds counted as building — fail
   toward overstating, stated once in the report legend).
2. The diagnostics blast ranking gains a **cost-weighted order**:
   measured durations from the run when present (the ranking already
   has the run), count-based otherwise, and says which it used.
3. The compare invalidation note's count adopts the same split:
   "invalidated 7 elements below it (3 that build, 4 stacks),
   11.3s of rebuilding".

## Out of Scope

- The resource dimension (UX-171/172) — this item is the existing
  element-blast surfaces only.
- Per-kind cost *models* (measured durations suffice; a model without
  a measurement is what UX-129 taught against).

## Acceptance Test

On `examples/06` (whose graph has cmake, stack and import kinds): the
diagnostics ranking shows the split counts and, with a run present,
the cost-weighted order; a synthetic graph where a stack-heavy blast
outnumbers a cmake-heavy one ranks *below* it by cost while the raw
count says otherwise (the discriminating case, asserted). The compare
note renders the split on the round-16 sabotage fixture. Mutation:
treating stacks as building kinds reddens the discriminating case.
