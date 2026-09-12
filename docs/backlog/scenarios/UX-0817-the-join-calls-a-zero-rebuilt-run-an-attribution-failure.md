# UX-817: the join calls a zero-rebuilt run an attribution failure

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-388 (which absence it is), UX-724 (the text report's half) | **Found by:** round 114, walk seed 3 | **Serves:** R1 reading `bga correlate` after an incremental build | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

On seed 3's incremental capture (examples/08, everything cached, 0
rebuilt, 0 processes traced), `bga correlate` refuses — correctly —
but names the wrong absence:

```text
$ bga correlate <incremental run> <its plane2.json>
NO USABLE JOIN: Plane 2's element attribution is unreliable.
  no process carried an element tag at all
  Nothing is recommended from this pair of artifacts.
```

Nothing was built, so nothing could carry a tag; the sentence reads
as a hook defect (`UX-66`'s class) to a reader who has just watched a
100 % cache hit. `UX-388`'s rule — say which absence it is — reached
the page and, with `UX-724`, the analyze text; the join's refusal is
the surface it has not reached.

## Required Fix

When the Plane 1 run rebuilt nothing (`run_mode` incremental, 0 BUILD
tasks) and Plane 2 traced no process, the refusal says so first —
"nothing was rebuilt, so there is nothing to join" — and keeps the
unreliable-attribution sentence for the case where processes ran and
none carried a tag. Guard: the two refusals on two synthetic pairs.

## Decomposition

Input classes the guard covers: a run with 0 BUILD tasks and 0
processes (the empty rebuild), a run with BUILD tasks and processes
none of which carry a tag (`UX-66`'s class), and a joined run; the
journey it extends is `test_the_journey_has_an_answer_key.py`'s walk —
cold then warm — with the warm join's sentence as its new last step.

## Out of Scope

- The analyze text and the page, which already say which absence it
  is (`UX-388`, `UX-724`).

## Acceptance Test

`bga correlate` on the answer key's warm run says nothing was rebuilt;
on a synthetic untagged run it still says attribution is unreliable;
mutation: swap the two sentences — both guards red.
