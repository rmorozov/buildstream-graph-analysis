# UX-553: the resource-holder set is spec-mandated and reaches no reader

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-541` (the measurement that found it) | **Found by:** `UX-541`, answering its own reader question | **Serves:** anyone who has to price a spec clause | **Topic:** contracts

## Motivation

Spec Part 8.2 requires `blocking_tasks` — the time-weighted set of
tasks holding the resource — for every resource-wait interval, and
`_build_holder_info` produces it. Nothing reads it.

```text
grep -rn blocking_tasks bga/     -> bga/attribution/blame_chain.py only (its own producer)
bga/validation/invariants.py:327 -> reads 'ambiguous', not the set
bga/schemas.py                   -> no contract carries it
```

Emptying the field leaves the published document **byte-identical** at
1,202 / 2,402 / 4,002 elements — measured in `UX-541`'s Outcome — and
costs 7.8% of `analyze` at 4,002 to compute.

This is `UX-243`'s shape (a published quantity with no consumer) with
one difference that makes it harder: the field is not bga's own
invention, it is ground truth asking for it. So the question is not
"delete it" but "who was Part 8.2 written for, and does that reader
exist yet".

## Required Fix

Decide, and write the decision down rather than leaving it implicit:

- if the holder set has an intended reader that has not been built —
  the "which tasks were holding the resource" question a page could
  answer — name it and file that, and the cost stops being waste;
- if it has none, it is a spec clause bga satisfies for nobody. Say so
  here. Editing Part 8.2 is out of scope for this row; naming the gap
  is not.

## Out of Scope

- Editing `docs/spec/specification.md` — ground truth, and Part 8.2 is
  outside the Part 32 registry this repository may touch.
- Re-doing `UX-541`'s cut, which is already taken.

## Acceptance Test

The decision written above, with the reader named or its absence
stated, and — if a reader is named — a row filed for it.
