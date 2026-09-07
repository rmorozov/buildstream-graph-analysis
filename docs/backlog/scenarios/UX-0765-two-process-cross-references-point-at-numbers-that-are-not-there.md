# UX-765: two process cross-references point at numbers that are not there

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-238 (the tiers), UX-584 (the remeasurement) | **Serves:** the session that follows a cross-reference and finds the other number | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

Two small instances of the shape `UX-750` fixed for figures, here in
the process documents.

**The tier timings disagree.** The same three targets carry different
measurements in two places, with no statement that one supersedes the
other:

```text
Makefile:30-32           small 18.2s   medium 184.0s   large 159.0s
fixing-guide.md:91-98    small 20.8s   medium 173s     large 126s
```

Up to 35% apart on `large`. The guide frames its own readings as *"the
machine's number and not the tier's"* (`:96`), which is honest but
does not reconcile them — a reader comparing the two sees two answers
and no rule for which to cite.

**A skill cites a line that does not carry what it claims.**
`.claude/skills/design-review/SKILL.md:20` says *"The orchestrator
passes the model choice on the launch (see `CLAUDE.md`'s agents
line)"*. `CLAUDE.md:30` pins `researcher` and `verifier` to `sonnet`
and names no model for `design-review` or `walk`. The reference points
at information the target does not contain, so the choice is inferred.

## Required Fix

1. Reconcile the tier figures: one owner, the other deferring, in
   `UX-756`'s pattern — or date both in `UX-511`'s, since both are
   machine-dependent readings rather than claims.
2. Either state the model for `design-review` and `walk` on
   `CLAUDE.md`'s agents line, or correct the skill to stop citing it.

## Out of Scope

- Re-measuring the tiers. Both readings are recorded with their
  provenance; this row is about which one a reader should cite, not
  about their values.
- The tier floors themselves (`tests/tiers.py`).

## Acceptance Test

A reader following either cross-reference arrives at the number it
promises. Mutation: change the owning figure and confirm the deferring
site carries no stale copy to contradict it.

## Outcome

_Not started._
