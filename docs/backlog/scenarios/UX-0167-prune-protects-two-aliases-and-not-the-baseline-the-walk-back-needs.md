# UX-167: prune protects two aliases, and not the baseline the walk-back needs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-159 (prune), UX-156 (the walk-back whose input this guards)

## Motivation

`prune`'s protection is `list_runs()[-2:]` plus a config `baseline`
key (`tools/bga_snapshot.py:439-450`). Round 17 hit the seam live: in
a store whose two newest run-bearing snapshots were a failed run and
an interrupted run, `prune --keep 2 --dry-run` protected exactly those
two — and offered to delete the store's only *healthy* snapshot, the
one UX-156's walk-back would choose as the next comparison's baseline.
The two features contradict: the walk-back says "the newest runs are
not measurements", prune says "the newest runs are the ones worth
keeping".

Two adjacent seams from the same session and review:

- **The husk survives.** A snapshot with no run directory (an
  interrupted capture from before UX-157, or a `--no-inject` session)
  is not in `list_runs`, not aliased, not useful — and `--keep 2` left
  it standing while deleting three run-bearing snapshots.
- **The `baseline` config key has no producer.** No production code
  ever writes it; only prune's own test does. Either `bga baseline`
  (or a `bga snapshot baseline <ref>` gesture) records it, or the
  protection guards a phantom.

## Required Fix

Prune's keep-set becomes: `@last`, `@prev`, the newest *healthy* run
(the walk-back's target — one more directory, and only when the
aliased two are unhealthy), and any recorded baseline once something
records one. Husks (no run directory) are pruned first under any
criterion, counted separately in the report ("2 empty snapshots
removed"). Decide the `baseline` key: wire a producer or remove the
dead protection with a note.

## Out of Scope

- `--keep`/`--older-than` semantics (verified live, unchanged).
- Store size mechanics (UX-159's, working).

## Acceptance Test

Round 17's store shape: healthy, failed, husk, interrupted. `prune
--keep 2` keeps the failed+interrupted (aliased), *and* the healthy
snapshot, deletes the husk, and says so in three distinct lines. A
follow-up snapshot's auto-compare still finds its walk-back baseline.
Mutation: dropping the healthy-run clause reddens the walk-back
assertion.

## What was built

Prune's keep-set is now `@last`, `@prev`, and — only when both of those
are unhealthy — the newest healthy run, which is exactly what UX-156's
walk-back will pick as the next comparison's baseline. A store of
healthy runs prunes precisely as it did before; the contradiction the
review hit live (failed + interrupted as the two newest, and prune
offering to delete the only healthy snapshot) cannot recur.

Husks — snapshots with no run directory — are pruned first under any
criterion and counted separately in the report ("(1 of those held no
run directory)"), instead of surviving `--keep` while run-bearing
snapshots were deleted around them.

The `baseline` config key was removed rather than wired: nothing in
production ever wrote it, so the protection guarded a phantom, and
protecting the walk-back's real target covers what it was for.

Guards in `tests/unit/test_snapshot_store_management.py`; dropping the
healthy-run clause reddens the walk-back assertion, as the acceptance
test asked.
