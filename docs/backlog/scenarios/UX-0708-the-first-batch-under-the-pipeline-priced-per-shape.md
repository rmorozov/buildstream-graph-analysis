# UX-708: the first batch under the pipeline, priced per shape

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-706 (the shape), UX-666 (a subagent's cost written down) | **Serves:** the advisory in `CLAUDE.md`, which today says `sonnet` for tracks on the strength of the reading rows alone | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The ledger holds 17 rows: researcher and general-purpose runs, none
for an `implementer` or a `verifier`. Round 94 put the implementer on
`sonnet` for mechanical and bounded shapes on the argument that a
track is reading with an edit attached; the number that confirms or
refutes it does not exist.

## Required Fix

One round runs one batch of bounded tracks — the eight open ones, or
the first mechanical filings — as `implementer` on `sonnet`, each
followed by the `verifier`; every run is a ledger row with the shape,
tokens, tool calls, wall, outcome (merged / reverted / re-run on the
session's model) and friction. The round document's table is the
measurement, and it decides one sentence in `CLAUDE.md`: which shapes
stay on `sonnet`.

## Out of Scope

- Judging a track's code — the suite, the mutation table and the
  verifier judge it; a track that needed judgement is a row that says
  so, and the shape rule learns from it.
- More than one batch — one is the measurement; the advisory is
  re-read every round after.

## Acceptance Test

`docs/audits/agent-runs.md` gains one row per track and per verifier
with a shape column; the round document pastes the per-shape median;
mutation: a track's outcome column left blank — the ledger guard
(`UX-666`) reddens.

## Outcome (round 103, 2026-09-07) — 🟢 Done

**Premise:** falsified — "the ledger holds 17 rows … none for an
`implementer` or a `verifier`" was true at filing and is not now. It
holds 39, of which **17 are implementer runs** and 4 verifier runs. The
gap was never the runs; it was that nothing joined a run to a shape.

### The gap, measured

```text
$ python3 tools/dev_process_bands.py --runs 12
error: unrecognized arguments: --runs 12   # before UX-666
$ grep -c "shape" docs/audits/agent-runs.md
0
```

No shape column, and adding one would have been a prose cell nothing
reads back. `UX-706` already derives the shape from the task file, and
every implementer row already names its id.

### After

```text
$ python3 tools/dev_process_bands.py --runs 12
17 implementer run(s), by the shape `dev_close_task.py --shape` derives:

shape        runs  median tokens  median wall  not merged
bounded        10           256k       31.1 m           0
judgement       7           189k       15.7 m           0

the row's own word differs on 2 of 17, each a batch of a larger row:
  `UX-705` burn-down batch 1 …: cell says bounded, file derives judgement
  `UX-705` burn-down batch 2 …: cell says bounded, file derives judgement
```

**Every one of the 17 merged.** None reverted, none re-run on the
session's model. Reading the two burn-down batches as the bounded
slices they were: bounded 12, median 239k, range 63-416k; judgement 5,
median 189k. By the cell's own word: judgement 4, median 144k.

**The advisory's sentence, decided.** A judgement shape stayed the
session's own — and the number says it still should, because **three
of the four judgement rows say the session took the judgement in the
brief**. The ledger cannot price a judgement a track was handed
undecided; none was. So `CLAUDE.md` widens by exactly what was
measured: the *judgement* is the session's, the work after it is not.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| N1 | `shape_of` reads the row's cell, not the file | the file-not-cell clause |
| N2 | an unknown id raises instead of returning None | the unknown-id clause |
| N3 | every agent shaped, not only `implementer` | 2 clauses |
| N4 | the cell/file disagreement dropped from the report | the disagreement clause |
| N5 | `CLAUDE.md`'s "4 of 17 runs" changed to 5 | the advisory clause |

### Deviation from the Required Fix

No new batch was run for this: 17 rows already existed, so running one
more to price a population that is already priced would have measured
nothing. The `shape` column the Required Fix names is a **join**, not
a column — a cell would drift and this cannot. One finding filed: a
track can force its own baseline growth past `make lint`, and one did
(`UX-745`).

```text
$ make test
7633 passed, 82 skipped, 1 warning in 448.33s (0:07:28)
$ make lint
All checks passed! / clean: 292 finding(s)
```

