# UX-501: the index is derived, not merged

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-336 (`dev_close_task`, which edits the counts today) | **Serves:** two sessions on one slate; the orchestrator who merges them | **Topic:** docs

## Motivation

Every track collides on the same lines: the `N scenarios: **M open**`
sentence and the per-topic table at the top of the backlog README, and
the open/closed row lists. They are hand-maintained *copies* of what
the row lists already say, so two branches that each close one task
conflict on the counts line even though neither touched the other's
row. `dev_close_task.py --check` reports the disagreement after the
fact; nothing derives the truth.

```text
files a parallel track must not touch (decompose §3)   4
of which are pure derivations of the rows                2  (counts sentence, topic table)
```

## Required Fix

- `dev_close_task.py --check --write` regenerates the counts sentence
  and the topic table from the rows in `README.md` and `closed.md`.
  The rows stay hand-edited (they carry judgement: title, Serves,
  priority); the aggregates do not.
- The index-count guard keeps asserting the two agree — the
  regeneration is what a session runs to make them agree, so the
  guard becomes a check that the derivation ran.
- A merge recipe in the `decompose` skill §3: merge tracks, run
  `--check --write`, commit; the counts line is never resolved by
  hand.

## Out of Scope

- Deriving the *rows* — the open table's one-line summaries are the
  filing's own sentence and belong to whoever filed it.
- `tests/tiers.py` and `tests/ci_reference.json`, the other two
  shared files — `UX-503` takes the reference; the tier lists are
  measured, not derived.

## Acceptance Test

Two worktrees each close one task; merging them conflicts on nothing;
`--check --write` leaves the guard green. Mutation: hand-edit the
count — `--check` reports it, `--write` restores it.
