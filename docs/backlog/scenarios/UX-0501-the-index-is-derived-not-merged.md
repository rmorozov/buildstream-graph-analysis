# UX-501: the index is derived, not merged

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-336 (`dev_close_task`, which edits the counts today) | **Serves:** two sessions on one slate; the orchestrator who merges them | **Topic:** docs | **Area:** tools

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

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

Two branches of a throwaway repository, each closing one item, with
`--move` writing the counts as it did:

```text
CONFLICT (content): Merge conflict in scenarios/README.md
<<<<<<< HEAD  | docs | 7 | 46 |  | guards | 7 | 65 |
=======       | docs | 8 | 46 |  | guards | 6 | 65 |
506 scenarios: **16 open**, 490 closed.     <- 14 rows, no conflict
```

Both failure modes at once. The topic table **conflicted** — adjacent
rows, one hunk. The counts sentence did *not*: both sides wrote the same
decrement from the same base, so git took it silently and the index
claimed 16 open over 14 rows with nothing checking it. That is the worse
one. And the table was already wrong: its Total column summed to **495**
over 504 rows, nine items in no topic and nothing saying which.

### After

`move` writes only its own rows; `--check --write` derives the header
from them. The same two branches:

```text
Auto-merging scenarios/README.md          <- no conflict
--check:  the counts sentence says '504 scenarios: **15 open**, 489
closed.'; the rows say '506 scenarios: **15 open**, 491 closed.'
          the topic table disagrees with the rows
          2 problem(s) over 4 propert(y/ies), 506 backlog row(s)
--check --write:  0 problem(s), 506 backlog row(s)
```

`closed.md` still conflicts — both branches inserted a row at the same
place. A *row* conflict, "keep both"; rows are this item's Out of
Scope, and the aggregate is what stopped colliding.

### Where the topic comes from, and the bucket

The task file's `**Topic:**` header, else the open table's Topic column,
else `unclassified`. `closed.md` has no Topic column and **223 of the
489** closed rows predate the header, so no topic can be derived for them
— not from the file, not from any of the 171 historical revisions of the
index. Naming the bucket makes the table sum to the row count and the debt
visible; distributing them by guesswork would not. `--move` now copies the
topic into the task file, so the loss does not recur. Filed as `UX-507`,
**which classified all 223 on 2026-08-31: the bucket has held 0 rows
since** (`UX-517`).

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| N1 | one cell of the table hand-edited | 2 clauses |
| N2 | `move` writes the header again | 1: `..._no_longer_writes_the_aggregates` |
| N3 | `--check` repairs instead of reporting | 1: `..._reported_and_then_restored` |
| N4 | `topics()` sends the unknowns to `viewer` | 2 clauses |
| N5 | `index_header()` drops the `unclassified` row | 2 clauses |

N2 is the one that matters: every other clause still passes with `move`
writing the header, because a single close computes the right number.
Only the two-branch merge tells them apart, so that clause reads the
source; the merge is in this Outcome, not in the fast tier.

```text
make test-touching   60 passed in 9.24s;  make lint clean
make test          5749 passed, 27 skipped in 316.49s
```

### Deviation from the Required Fix

The filing says "from the rows in `README.md` and `closed.md`". The closed
rows carry no topic, so the derivation reads the task file's header
instead and says `unclassified` where there is none — **no longer true
since `UX-507` (2026-08-31)**. Nothing else. §3.10 fixed here:
`CLAUDE.md`'s command table and status rule, the `verify` skill's step 4,
and the `decompose` skill's shared-files list, which now carries the merge
recipe.
