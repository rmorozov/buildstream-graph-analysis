# UX-506: the Outcome skeleton fits the register

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-497 (the cap), UX-336 (`dev_close_task --outcome`) | **Serves:** the session closing a task, and the round that reads it later | **Topic:** docs

## Motivation

`dev_close_task.py --outcome` prints five headings and the sessions
fill them at a median 114 lines (round 74, `UX-0440..0496`; max 284).
The cap from `UX-497` is 80. The skeleton is not over the cap — the
prose under it is — but the skeleton invites it: a heading called
*"what the fix had to be, and why that shape"* asks for a narrative,
and the sessions write one.

## Required Fix

The skeleton names what a later round *reads*: the gap measured
(pasted), the close measured (pasted), the mutation table (one row
per mutation: what, reddened, count), the deviation from the Required
Fix (one line, "none" allowed). The *why that shape* heading goes;
rejected designs are one line each with the number that rejected
them, under the deviation. A line under the skeleton states the cap
and the guard that holds it.

`tools/dev_process_bands.py` reads the Outcome headings — it is
updated in the same commit so its count of mutation rows and
deviations still works, with a before/after on the committed record.

## Out of Scope

- Rewriting existing Outcomes — the cap applies from `UX-497` on and
  the record before it stays as written.
- Any change to what must be *measured* — the four measurements stay;
  only the room for narrative around them goes.

## Acceptance Test

`--outcome` prints the new headings; `dev_process_bands.py` reports
the same counts on the committed record before and after; the first
three Outcomes written under it fit the cap without editing.

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

```text
Outcomes in round 74's range (UX-440..UX-496)    56
  median length                                 117 lines
  longest                                       284
  over the 80-line cap                           45   (80 %)
skeleton printed                                 28 lines
```

The skeleton was never over the cap — the prose under it was — but it
invited the prose. A heading reading *"what the fix had to be, and why
that shape"* asks for a narrative, and four out of five sessions wrote
one long enough to breach the budget `UX-497` set.

### After

```text
skeleton printed                                 43 lines
  of an 80-line budget, stated in the skeleton itself
dev_process_bands.py, before and after           identical
```

The removed heading is gone and the four measurements are named as what
a later round *reads*: the gap pasted, the close pasted, the mutation
table, the deviation. Rejected designs are one line with the number
that rejected them, under the deviation — not a section of their own.
The skeleton now states the budget, so a session sees it while writing
rather than when the guard reds. This Outcome is the first written
under it.

`dev_process_bands.py` needed no change: it counts phrases, and the two
it counts — `Mutations verified red` and `Deviation from the Required
Fix` — are preserved deliberately. That is now a guard rather than an
accident.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| Q1 | the mutation heading reworded | 2 clauses |
| Q2 | the deviation heading dropped | 2 |
| Q3 | the skeleton stops naming the cap | 1: `..._states_the_cap_...` |
| Q4 | the "why that shape" heading comes back | 1: `..._asks_for_no_narrative` |
| Q5 | a measurement pre-filled in a fence | 1: `..._leaves_every_measurement_blank` |
| Q6 | twelve lines of filler added to the skeleton | 1: `..._leaves_room_under_the_cap` |

Q1 and Q2 are the census clause: `dev_process_bands.py` reads 288
closed Outcomes for exactly those phrases, and a reworded heading would
drop a row of it to 0 % with nothing else saying so.

**A guard of ours that had to be restated.** The existing
`test_the_outcome_skeleton_leaves_every_measurement_blank` asserted one
literal phrase from the old skeleton, so rewording the skeleton reddened
a guard about *measurement* for a reason that had nothing to do with
one. It now asserts the property: every fenced block is a placeholder.
Q5 is what proves the restatement still discriminates.

### Deviation from the Required Fix

The filing asks for `dev_process_bands.py` to be "updated in the same
commit"; it needed no update, and the before/after above is identical
rather than merely consistent. The reason is now pinned by a clause, so
the next skeleton edit cannot break it silently.

```text
make test-touching  74 passed in 5.25s;  make lint clean
make test           5758 passed, 27 skipped in 407.44s
```
