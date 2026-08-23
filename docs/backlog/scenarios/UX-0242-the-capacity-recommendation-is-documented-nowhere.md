# UX-242: the capacity recommendation is documented nowhere

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R1 and R5 — the two who would act on a `--builders`/`--max-jobs` answer | **Topic:** docs

## Motivation

Filed by `UX-237`'s rule on its own first application: this is one of
the three round-28 instances that named the gap.

`bga analyze` computes `capacity_recommendation` (`bga/cli.py:183`,
`_capacity_recommendation` at `:197`) from Plane 2's achieved
parallelism and the host's cores, and publishes it. Measured across the
documentation tree:

```text
git grep -l capacity_recommendation docs/
  docs/backlog/scenarios/UX-0116-…md      (the filing that built it)
  docs/backlog/scenarios/UX-0229-…md      (a later filing quoting it)
  docs/backlog/scenarios/closed.md        (the closed rows)
```

Three backlog files and nothing else — no guide, no spec part, no line
in `architecture.md`. `UX-116` is the tool's founding question
("`--builders` × `--max-jobs`, jointly") and its answer is reachable
only by reading `cli.py` or by finding a closed backlog row.

## Required Fix

1. `docs/guides/cli.md` says what the recommendation is, what it is
   computed from, and — the part that matters — **when it declines to
   make one**, since a missing recommendation currently looks identical
   to an absent feature.
2. The spec names the field wherever `analyze/v1`'s keys are described,
   so a consumer meeting it in a payload can look it up.

## Out of Scope

- Changing the recommendation itself. `UX-116` and `UX-104` settled
  what it computes and this is about saying so.
- `memory_envelope` — its own filing (`UX-243`), because the two decline
  for different reasons and one paragraph covering both would explain
  neither.

## Acceptance Test

`git grep -l capacity_recommendation docs/` names at least one
instructional document; a reader who has the field in a payload and
neither the source nor the backlog can say what it means and why it
might be absent.
