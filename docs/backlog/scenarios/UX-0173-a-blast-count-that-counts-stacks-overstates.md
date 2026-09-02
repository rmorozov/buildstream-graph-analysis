# UX-173: a blast count that counts stacks overstates

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-171 (shares the weighting), UX-156/UX-164 (the honest-counting precedent) | **Topic:** analysis

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

## What was built

The user's first sentence about blast analysis was that it ignores
element kind. Three places counted without it; all three now split
**kinds that build** from **kinds that assemble** (`stack`, `import`,
`filter`, `junction`, `compose`, `link`), with an unrecognised kind
counted as building - overstating what a change costs is the safe
direction for a number somebody uses to decide whether to make it, and
the report says so where it prints the split.

1. **The resource table and `bga blast`** print `7 element(s) (3 that
   build, 4 that assemble)`, and stay silent about the split when
   everything builds - `(7 that build)` after `7 elements` is noise.
2. **The diagnostics blast ranking is ordered by cost**: measured
   downstream rebuild time where the run has durations, element count
   where it does not, and the report *names which* rather than leaving
   it to be inferred. `blast_radius_ranked_by` is published in the JSON
   for the same reason.
3. **The invalidation note** in `bga compare` adopts the same split, so
   "invalidated 7 element(s) (3 that build, 4 that assemble) below it"
   replaces a 7 that treated a stack and a compiler as the same event.

Measured live, `bga analyze @last --diagnostics` on
`examples/01-resource-contention`:

```text
  Max Blast Radius: 9 downstream elements
  Widest blast radius, by measured rebuild time:
    runtime.bst (import): 9 downstream, 22.0s of rebuilding below it - assembles, does not build
    work-h.bst (manual): 1 downstream
```

The widest blast in that project is an element that runs no build
commands at all, which is exactly the distinction the count could not
draw.

One guard needed a second attempt: the ranking tests fed the renderer a
dict they had built, so mutating the *sorter* reddened nothing. The
end-to-end assertion over the golden run - `blast_radius_ranked_by`,
and the weights in the published order actually descending - is what
catches it.
