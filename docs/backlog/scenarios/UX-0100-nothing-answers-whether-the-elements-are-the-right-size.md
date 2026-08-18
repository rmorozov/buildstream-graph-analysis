# UX-100: nothing answers whether the elements are the right size

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-99 (the toll measurement), UX-82 (the replay-projection pattern)

Direction 3, item 1 (second half) — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Element granularity is BuildStream's oldest tuning question and every
answer today is folklore. Both failure directions are real and
opposite:

- **Too fine:** many small elements, each paying the UX-99 toll
  (staging, integration, caching) to do less work than the toll costs —
  plus a per-element cache key, artifact, and scheduler slot. The
  signature is measurable: toll share above ~50% of element time.
- **Too coarse:** one monolith holding a large share of the critical
  path, whose internal build (Plane 2 can see it) has independent
  targets that BuildStream could have scheduled as separate cacheable
  elements — the signature is a dominant element with high internal
  parallelism *and* high cache-invalidation cost (UX-92's roots: when
  it invalidates, everything it contains rebuilds).

The tool now measures every ingredient — toll (UX-99), durations and
critical-path share (Plane 1), internal parallelism (Plane 2),
invalidation blast (UX-92) — and draws no conclusion from them, which
is the same measure-but-don't-say gap UX-82 closed for graph shape.

## Required Fix

A granularity section (natural home: `bga correlate`, which already
holds Planes 1+2; Plane 3 input via the UX-99 JSON):

1. **Merge candidates:** groups of sibling elements (same parents in
   the graph) whose toll share exceeds a threshold *derived from the
   measured toll distribution, not guessed*. Projected saving = the
   tolls a merge would delete (N−1 stagings of the same dependency
   set), projected with the UX-82 replay pattern — a replay where the
   group is one element of summed work time. Standing hedges apply: a
   merge changes cache granularity, and the finding must say what it
   costs (one source change now rebuilds the group).
2. **Split candidates**, hedged harder: an element that (a) holds a
   material share of the critical path, (b) shows internal parallelism
   or separable phases in Plane 2, and (c) appears as an invalidation
   root with a wide blast in the run history. Name it and the evidence;
   do not project (a split's shape is a human decision).
3. Both render as evidence-ranked findings with ids, like everything
   else since UX-75.

## Out of Scope

- Generating the merged/split `.bst` files.
- Artifact-size evidence (needs CAS; strengthen later).
- Any threshold not derived from a measured distribution (UX-28's
  lesson).

## Acceptance Test

On a purpose-built fine-grained example (N trivial elements sharing one
heavy dependency — a variant of `examples/06` with sub-second libs):
the merge candidate names the group, the projected saving is within the
documented band of a real merged rebuild, and `examples/06/optimized`
as-is produces **no** merge candidate (its elements do ~2s of work
each). On the fdsdk capture: `cmake-stage1.bst` (43% of path, internal
parallelism 3.41 cores, bootstrap-wide invalidation root) appears as
the split candidate with all three evidence clauses, and nothing else
does.
