# UX-506: the Outcome skeleton fits the register

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-497 (the cap), UX-336 (`dev_close_task --outcome`) | **Serves:** the session closing a task, and the round that reads it later | **Topic:** docs

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
