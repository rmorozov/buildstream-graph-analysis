# UX-116: the tool's founding question is now answerable, and unanswered

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-83 (Plane 2 into capacity advice), UX-104 (memory envelope), UX-14 (the contention caveat), UX-31 (pinning detection)

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

## Fix Implemented

`compute_capacity_recommendation` (`bga/correlate.py`) and the
`capacity-recommendation` finding (`bga/findings.py`), emitted by
`bga analyze --plane2`. Four already-measured constraints, intersected,
with the binding one named:

```text
Capacity: builders 4 x max-jobs unrecorded on 4 core(s): graph binds first, at 6 -
nothing measured here rules out 2 more builder(s), which is a hypothesis to time
rather than a setting to apply
  graph allows 6: the sweep's knee is at 6 builder(s)
  CPU allows 7: 2.11 of 4 core(s) busy at builders=4, i.e. 0.53 core(s) per concurrent element
  memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peak(s),
      so it says nothing above 9)
  Free capacity you already have: core.bst asked its native build for -j1 - a builder
      slot drawing one core. Fix that before raising anything, then re-measure.
  Time it before keeping it: the knee is a scheduling answer and cores-busy is a
      whole-run average, so both overstate what a contended window can absorb.
```

**The CPU ceiling is derived, not chosen.** At the observed `builders`
the run drew `cores_busy` cores, so one concurrently-building element
drew `cores_busy / builders` — measured. The host can feed
`host_cores * builders / cores_busy` of those, floored. On UX-116's own
worked example (3.4 busy of 4, builders 4, knee 5, memory 11) that is
exactly 4: CPU binds, no fifth builder, which is the answer the task
predicted.

**A constraint nothing measured is omitted, never treated as
unbounded.** No memory envelope means memory is absent from the list
rather than infinite; no `cores_busy` or no host core count means no
block at all — the same bar `UX-83` uses.

**The sweep is bounded** to `max(builders, host_cores) * 2`, capped at
32, because the default is one configuration per task and a
1200-element project should not pay 1200 replays to answer a question
about a 4-core host. A knee at the top of that range says so rather
than pretending to be the answer.

Item 3 is done by naming the clause: `analyzer.UNMODELED_AXIS_CLAUSE`
is substituted for `MODELLED_AXIS_CLAUSE` **only** in captures where the
block ran. Two constants rather than two re-typed sentences, so the
retirement cannot drift onto a clause it was not meant to touch.

## Verification Log

Done 2026-08-19.

### On the fdsdk spine capture

```text
Capacity: builders 4 x max-jobs 4 on 4 core(s): graph binds at 2, below the 4
configured - more builders contend rather than overlap here
  graph allows 2: the sweep's knee is at 2 builder(s)
  CPU allows 4: 3.27 of 4 core(s) busy at builders=4, i.e. 0.82 core(s) per concurrent element
  memory allows 11: the 11-builder envelope fits in 15.6 GB
```

Consistent with the acceptance: no more builders, and memory not
binding. The acceptance quoted 3.4 cores busy from an earlier capture;
this one measures **3.27 of 4**, the same compute-bound profile.

### On a Plane 2-less run

No block (`grep -c "Capacity: builders"` → 0) and
`currently unmodeled axis (see UX-09/UX-15)` still present. Both halves
of item 3, on the same run directory.

### On the round-10 macro-fixed capture — and the wording it changed

The round-10 captures were not retained, so the state was reconstructed:
`examples/06/optimized` with `notparallel: True` put back on `core.bst`
— macro fixes in, micro fix not. The block named `core.bst`'s pinning as
free capacity, which is the acceptance's third clause, and said "graph
binds at 6 — room for 2 more builder(s)".

Then the real timing table, four `--builders` values × three cold builds
each at `--max-jobs 4` on this 4-core host:

| builders | run A | run B | run C | median |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 21.5s | 21.6s | 23.1s | 21.6s |
| 4 | 24.2s | 21.8s | 24.3s | 24.2s |
| 6 | 23.5s | 21.3s | 24.0s | 23.5s |
| 8 | 21.7s | 23.3s | 24.0s | 23.3s |

Flat. The within-setting spread reaches 2.7s (builders 6: 21.3–24.0) and
the largest between-setting difference is 2.6s, so there is no ordering
to read. **"Room for 2 more builders" was not realizable**, and that is
a defect in the claim rather than in the arithmetic: the knee is a
scheduling answer, and `cores_busy` is an average over the whole run, so
during the parallel stretch each element draws more than 0.53 cores and
the CPU ceiling of 7 is optimistic.

So the headroom case was reworded rather than left standing: the block
names the binding constraint and calls the headroom *a hypothesis to
time*, with the reason both ceilings are optimistic printed beside it.
No new heuristic was invented to close the gap — a threshold with no
measurement behind it is what this codebase refuses to add, and the
honest fix for an over-claim is to stop making it.

### Deviations from the Required Fix, recorded

1. **Pinning is named whichever constraint binds**, not only when CPU
   does. Written the narrow way first; the reconstructed macro-fixed
   capture disproved it — `core.bst` is pinned there, the *graph* binds,
   and suppressing the line hid the one fix actually available. A pinned
   element holds a builder slot while drawing one core: the slot is the
   waste when CPU binds, the element's own length is the waste when the
   graph does.
2. **The headroom wording is weaker than the task's example.** UX-116
   sketched *"builders 4 x max-jobs 4 … CPU binds"* — the no-headroom
   case, which the block reproduces exactly. The headroom case had no
   worked example in the task, and the timing table above is why it now
   ships hedged.
3. **`--max-jobs` is named, not tuned.** The block reports the joint
   setting and prints `max-jobs unrecorded` when `UX-29` could not
   recover it, but every ceiling it computes is a `--builders` ceiling.
   Recommending a `--max-jobs` value needs per-element CPU curves at
   more than one `-j`, which is a build-and-measure search and is
   explicitly out of scope here.

Tests: 22 in `tests/unit/test_capacity_recommendation.py`.
