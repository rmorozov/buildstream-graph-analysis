# UX-446: a third ceiling, and no reader-facing document has it

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** review 8, checklist item 3 — `UX-430`'s own §3.10 debt, one round later | **Serves:** anyone whose export drops the timeline and goes looking for the reason | **Topic:** docs

## Motivation

`UX-430` added `TRACE_TRACK_BUDGET`, a second bound on the Perfetto
handoff in the unit Perfetto actually spends. Two documents still say
there is one.

`docs/guides/cli.md` publishes the ceilings as a table of exactly two
rows, and the second says the trace's byte figure is

> the **gzipped trace** before it is base64-encoded — one part of the
> data half, and the only part either ceiling singles out

`docs/design/styleguide.md` §3g opens:

> `tools/bga_view.py:601` carries **the only bound** the Perfetto
> handoff has

Both were true when written and neither is now. A reader whose export
refuses for **16,832 tracks** reads a table of byte ceilings, finds the
trace comfortably under the one it names, and has nowhere to go.

`git grep TRACE_TRACK_BUDGET -- docs` returns nothing: the number the
refusal quotes is stated in one docstring and in no document.

## Required Fix

- **The ceilings table carries all three**, each in its own unit and
  each saying what to do when it is the one that bit — for tracks that
  is `--planes 1` or `--only-element`, which `cli.md` already documents
  a section earlier and does not connect to the refusal.
- **§3g's opening sentence closes**, the way §4e's did in round 70:
  the section is a rule with a worked example, and the example's "only
  bound" is now the thing the rule fixed.
- Check the same sentence has not been copied elsewhere —
  `docs/guides/what-the-viewer-answers.md` states the 4 MiB transport
  change and may or may not imply exclusivity.

## Out of Scope

- **The bound's value** — one sample, and `UX-445` holds it.
- **The narrowing flags themselves**: documented by `UX-430` in
  `cli.md`'s `bga timeline` section. This item connects them to the
  refusal rather than describing them again.

## Acceptance Test

`git grep -c TRACE_TRACK_BUDGET -- docs` is non-zero; the ceilings
table has a tracks row naming the flags; and §3g no longer opens on a
claim `UX-430` falsified. A mutation adding a fourth bound in a fourth
unit and leaving the table at three must redden a guard — which means
this item ends with the table derived from the constants rather than
written beside them, or with a guard that compares the two.

## Outcome

_Not started._
