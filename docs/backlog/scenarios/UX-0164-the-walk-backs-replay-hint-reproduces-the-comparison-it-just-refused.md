# UX-164: the walk-back's replay hint reproduces the comparison it just refused

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-156 (the refusal these words surround)

## Motivation

UX-156's mechanics hold — round 17 verified the refusal, the banner,
the walk-back and the gate's exit 6 live. The words around them have
three defects, two observed live in the same session:

1. **The replay hint is wrong after a walk-back.** `_compare` prints
   `$ bga compare @prev @last   # <paths>` unconditionally
   (`tools/bga_snapshot.py:398`). After "Comparing against
   \<healthy\> rather than the previous snapshot: \<failed\> record
   build(s) that did not finish", the printed command's `@prev`
   resolves to the *skipped* snapshot (it has a `run/`, so `list_runs`
   includes it) — typing the suggested command reproduces exactly the
   wreckage comparison the feature exists to prevent, and gets a
   refusal instead of the comparison shown above it. On long-running
   projects failed and interrupted runs are the store's common tenants,
   so the hint is wrong more often than right precisely where UX-156
   matters most.
2. **Number agreement**: "…: 20260820T144452Z record build(s) that did
   not finish" — one snapshot "record**s**"; the sentence is built for
   a plural list and reads broken for the common single-skip case.
3. **"0 of 7 scheduled elements built" counts cache hits as
   casualties.** The failing run's queue was processed 0, skipped 6,
   failed 1 — six elements were already cached, one failed, none
   needed building besides it. `scheduled_count` = processed + skipped
   + failed, so the sentence overstates the damage 7× and a user may
   go hunting for six lost builds. Say what happened: "1 element
   failed (lib-d.bst); 0 built, 6 were already cached."

## Required Fix

The hint prints `@prev @last` only when those aliases resolve to the
pair actually compared; otherwise it prints the real refs
(`bga compare @20260820T1444 @last` — the stamp-prefix grammar already
exists). Fix the sentence's number agreement. Split
`scheduled_count` into built/cached/failed in `build_outcome` and
have both the banner and the refusal reason use the three-way count.

## Out of Scope

- The refusal/walk-back mechanics (verified working).

## Acceptance Test

Round 17's store shape replayed: healthy → failed → healthy. The
third snapshot's hint names a command that, pasted verbatim, produces
the same comparison printed above it (asserted by running it in the
test). A single skipped snapshot reads grammatically. The failing
snapshot's banner says "0 built, 6 already cached" against a queue
summary of 0/6/1, with the docs-commands test covering the changed
wording's home.

## What was built

Three separate wrongnesses in the walk-back's own prose:

1. `_compare_refs` builds the hint from the pair actually chosen, so
   after a walk-back it prints `bga compare @prev-1 @last` (or the
   explicit stamps) rather than `@prev @last` — which resolved to the
   wreckage the walk-back had just refused. The hint is now
   byte-identical to what the snapshot command itself ran.
2. The skip sentence agrees in number: one skipped snapshot reads
   "records a build that did not finish", several read "all record
   builds that did not finish".
3. `_count_clause` in `bga/compare.py` stops counting cache hits as
   casualties: the queue that was 0 built / 6 cached / 1 failed now
   reads "0 built, 6 already cached", not "0 of 7 scheduled elements
   built". `built_count`/`scheduled_count`/`cached_count` are carried
   from `bst_extract_run.py` through the `build_failed` violation to
   both renderers rather than re-derived in either.

Six mutations falsified. Four UX-156 assertions that pinned the old
wording were updated with the reason recorded in the test.
