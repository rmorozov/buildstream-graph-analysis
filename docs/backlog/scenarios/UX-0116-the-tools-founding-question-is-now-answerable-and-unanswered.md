# UX-116: the tool's founding question is now answerable, and unanswered

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-83 (Plane 2 into capacity advice), UX-104 (memory envelope), UX-14 (the contention caveat), UX-31 (pinning detection)

## Motivation

UX-09 — the question `examples/05` was built for, in the first week of
this backlog: *do `--builders` and `--max-jobs` compete for the same
cores, and what should I set them to?* It was answered descriptively
(yes, they compete; a 6-configuration timing table) and then every
subsequent round added one more input without ever assembling the
answer: sweep's knee (Part 19), measured cores-busy per element
(UX-45), pinning detection (UX-31/83), the memory envelope per
builders value (UX-104), and the CPU-axis caveat (UX-09/15) that
still, on every report, tells the user this axis is "currently
unmodeled".

Every constraint of the joint (builders × max-jobs) choice is now a
measured number in one capture. What is missing is the paragraph that
intersects them — the difference between four blocks a user must
reconcile and the one recommendation they came for.

## Required Fix

A capacity-recommendation block in `analyze --plane2` (the UX-83
channel, which already arbitrates one direction of this):

1. Intersect the constraints the run measured: sweep's scheduling knee
   (how many builders the *graph* can use), Plane 2's aggregate
   cores-busy (how much CPU the elements actually draw at their
   current `-j`), the UX-104 memory ceiling per builders value, and
   host cores. Emit the binding constraint by name and the implied
   setting: *"builders 4 x max-jobs 4 on 4 cores: the graph could use
   5 builders (knee), but CPU already runs at 3.4 cores busy and
   memory allows 11 - CPU binds; more builders would contend, not
   overlap. Fix core.bst's -j1 first (free capacity), then re-measure."*
2. Honesty inherited, not re-invented: the recommendation carries
   UX-14's standing caveat (the sweep replays observed durations and
   does not model contention), states it is derived from *this run's
   shape*, and never fires when Plane 2 coverage is below the same bar
   UX-83 uses.
3. Retire the "currently unmodeled axis" note **only** in captures
   where this block runs — elsewhere it stays, because there it is
   still true.

## Out of Scope

- Trying configurations (no build-and-measure search; one capture in,
  one recommendation out — UX-09's timing table remains the ground
  truth this is checked against).
- Per-element `max-jobs` overrides beyond naming pinned elements
  (UX-31 already names them).

## Acceptance Test

On the round-10 macro-fixed capture (the knee-5-on-4-cores case): the
block names CPU as binding, does not recommend a fifth builder, and
names `core.bst`'s pinning as the free capacity — the same answer
UX-09's real timing table measured (4x4 fastest). On the fdsdk spine
capture: the block's recommendation is consistent with the measured
3.4-cores-busy compute-bound profile (no more builders) and the UX-104
envelope (memory not binding). On a Plane 2-less run: no block, and
the unmodeled-axis note still present.
