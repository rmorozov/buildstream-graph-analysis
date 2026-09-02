# UX-100: nothing answers whether the elements are the right size

**Priority:** Medium | **Status:** 🟢 Done (reopened by round 12, closed by UX-120) | **Depends on:** UX-99 (the toll measurement), UX-82 (the replay-projection pattern) | **Topic:** analysis

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

---

## Fix Implemented

`find_granularity_findings` in `bga/correlate.py`, reached by
`bga correlate --cache-logs PLANE3.json` — Planes 1+2 were already
there, and `--cache-logs` supplies Plane 3's per-element toll.

### The merge criterion, and why it is not a derived cut

The Required Fix asks for a threshold *"derived from the measured toll
distribution, not guessed"*. Deriving one was tried first, and the real
distribution refuses to supply it. On the freedesktop-sdk log tree, 23
elements:

```text
median toll share  0.000
MAD                0.000
maximum            0.167   (components/which.bst, 1.0s of 6.0s)
```

`median + k·MAD` collapses to the median, **every** element clears it,
and the derived threshold is decorative — `UX-28`'s lesson arriving
through the back door. The cause is not a defect: BuildStream times
these phases to the second and most stagings finish inside one, so the
distribution genuinely has no spread to describe.

So the criterion comes from the direction's own sentence instead —
elements *"each paying the `UX-99` toll to do less work than the toll
costs"*. That is `toll >= work`: a definition, with nothing to tune,
which lands on the same ~50% share the direction hypothesised without
anyone picking it. An absolute floor of one second sits beside it,
because a 91% toll share on a 0.44s element is arithmetic — `UX-99`
ranks toll payers by seconds for the same reason.

**Deviation 1, recorded:** the threshold is derived from the definition
rather than from the distribution, because the measured distribution
cannot produce one.

### What "no finding" says

```text
[info] merge-not-indicated: No element pays more sandbox toll than it spends
building. Across 23 measured element(s) the largest toll share is 17%
(components/which.bst, 1.0s of 6.0s), against the 50% that would make a merge
worth its cache cost
```

and on `examples/06`, whose elements do ~2s of work each — the
acceptance's own negative case:

```text
Across 27 measured element(s) the largest toll share is 0% (app.bst, 0.0s of
2.0s)
```

Both are the acceptance's *"produces no merge candidate"*, said in a
form that distinguishes it from a check that could not run.

### Split candidates

Three clauses were specified: a material share of the critical path,
internal parallelism Plane 2 can see, and a wide invalidation blast in
the run history. The first two are measured on the real capture:

```text
[info] split-candidate: components/_private/cmake-stage1.bst holds 44% of the
critical path and runs 7.50 concurrent work processes inside one element (4586
of them) - work BuildStream could have scheduled as separate cacheable
elements. Evidence, not a recommendation: a split's shape is a human decision,
and this run's history carries no invalidation blast for it (every capture is
the same commit), which is the third piece of evidence and the one that would
make the case
```

The acceptance predicted *"43% of path, internal parallelism 3.41
cores"*; this capture measures **44%** and **7.50**.

**Deviation 2, recorded:** the third clause cannot be evaluated. Every
published capture is of the same freedesktop-sdk commit, so no element's
cache key has ever changed and `UX-92` finds no invalidation roots at
all. The finding therefore requires the first two clauses and *states*
that the third is unavailable, rather than staying silent or pretending
to have it. The cost is visible and worth naming: with two clauses
instead of three, **four** elements qualify on this capture
(`cmake-stage1` 44%, `openssl` 18%, `python3` 17%, `doxygen` 14%) where
the acceptance expected *"and nothing else does"*. Captures at two
different commits are what closes it, and `UX-96`'s schedules now
accumulate them.

### The projection

Merging N siblings deletes N−1 stagings, and the saving is **replayed**,
not summed: the `UX-82` pattern applied to durations instead of edges,
through the replay scheduler's own `duration_overrides`. Deleting five
stagings frees capacity, and what happens next is decided by the
scheduler, which arithmetic does not know.

### One bug found while wiring it

`_merge_candidates` first read the parent map from
`analysis['graph']['dependencies']`. The analysis JSON has no `graph`
key, so the check could never fire — a gate that passes because it
cannot fail, which is the exact defect class `UX-84`, `UX-97` and
`UX-109` all are. Caught by printing the parent map while wiring it up;
the graph now comes from the caller's own graph object.

Tests: 8 new in `tests/unit/test_granularity.py`. Suite: 1327 → 1335.

## Verification Log

Done 2026-08-18. Every figure above is from the published
freedesktop-sdk capture or from a real `examples/06` dual capture; the
toll distribution that decided the criterion was computed from the
former, not assumed.

## Reopened by audit round 12 (2026-08-19)

The file records two deviations; there is a third, unrecorded: the
acceptance's *positive* merge case — the purpose-built fine-grained
fixture, the fired candidate, and the projection checked against a real
merged rebuild — was never run. The merge-candidate branch has fired
only on synthetic unit-test input; round 12 re-ran both real captures
live and confirmed the (correct) negative answers, which cannot
distinguish a working detector from an inert one. `UX-120` carries the
remaining work; this returns to 🟢 when its acceptance's clause 1 runs.

## Closed by UX-120 (2026-08-19)

The missing clause ran. `examples/09-fine-grained-siblings` was built,
captured, and the merge candidate fired on real data for the first time —
naming all eight siblings, 7.0s of deleted toll, a replayed 1.0s. The
group was then really merged and rebuilt: median 8.52s → 5.82s, a real
saving of **2.70s**.

Two things came out of it, both recorded in full in
[`UX-0120`](UX-0120-the-merge-candidate-has-never-fired-on-real-data.md):

- **Why the criterion had never fired on a real capture.** Not because
  no project is too fine-grained — because BuildStream stages by hardlink
  and times its phases to the second, so a normal 8k-file sysroot stages
  in `00:00:00` and the toll rounds to zero. The fixture needs 60,000
  files before the measurement can see the thing it measures.
- **The projection is a floor, not an estimate.** It under-predicts the
  real saving by 2.7× because the replay shortens N tasks and leaves them
  as N tasks, while a real merge collapses them into one. Re-hedged
  rather than re-modelled, and it now says so in its own title.

**Closed by round 13:** `UX-120` ran the positive merge case on a real
fixture (`examples/09-fine-grained-siblings`) with a real merged
rebuild; the projection missed (1.00s vs measured median 2.70s) and now
ships as an explicit floor rather than an estimate. The reopening above
stands as the history of why that work existed.
