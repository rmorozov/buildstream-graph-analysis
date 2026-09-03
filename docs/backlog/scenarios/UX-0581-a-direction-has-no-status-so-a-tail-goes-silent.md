# UX-581: a direction has no status, so a tail goes silent

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-231 (the Serves line every direction carries) | **Serves:** the reader deciding what is still open at direction level | **Topic:** docs

## Motivation

Every direction's decomposition landed (every id 🟢), and the
declines that were stated are stated well. What the round found is
the tails that were neither landed nor declined and say nothing:

```text
D8  directions.md:976-978   "explain-path for compare"             git grep "evidence chain" scenarios → 0
D9  directions.md:1025-1031 queue seam · capacity model · cost translation    greps → 0 files (cost translation: UX-234 only)
D10 directions.md:1562      item 5 "a tag"                          git tag | wc -l → 0
D11 directions.md:1641-1645 four "yes" rows for bga:distribution    schemas.py: one site
D1  directions.md:188-206   "None of it is currently printed"       no Done callout; phrases absent from report/text.py
```

`test_every_direction_names_its_reader.py` walks the `## Direction`
headings for a Serves line; no line says whether a direction is
landed, partial or declined, so a partial one reads as landed.

## Required Fix

A `**Status:**` line per direction — `landed` / `partial — <what
remains, as a filed id or a stated decline>` / `declined — <why>` —
held by extending the Serves guard's section walk; the five above
resolved into that vocabulary (the D8/D9 tails filed or declined, the
tag either cut or the item retired, D11's table corrected).

## Out of Scope

- Re-arguing any direction — the status line records the state; the argument stays as written.

## Acceptance Test

Mutation: remove a direction's Status line — red; write `partial`
without an id or a decline — red.

## Outcome

**The gap, re-measured before building.** Four of the Motivation's five
premises hold; two of its figures do not.

```text
git grep -l "evidence chain" -- docs/backlog/scenarios   1 (this file)  → holds
git tag | wc -l                                          0              → holds
git grep -li "queue seam" -- docs/backlog/scenarios      1 (this file)  → holds
git grep -n "_distribution(" bga/schemas.py              2 analyze sites, not 1
git grep -n "Dispatch Occupancy" bga/report/text.py      text.py:652    → D1 is stale, not unprinted
```

- **D11 was wrong by one.** `analyze` publishes `bga:distribution`
  twice (`element_duration_distribution`, `blast_radius_distribution`),
  plus five store-aggregate sites. So two of the table's four `yes`
  rows are published and two are not — recorded as a dated note under
  the table rather than by editing the rule.
- **D1's "None of it is currently printed" is false, not silent.** All
  five lines of its illustrative block render from `report/text.py`:
  `Serialized (…)` with combined savings, `Dispatch Occupancy:`,
  `Critical Path Length:`, `Parallelism-Pinned Elements (UX-31 …)`, and
  `builders=N x native max-jobs=M = K potential concurrent processes`.
- **D8's tail is half landed.** `_why_block` in `ci_comment.py` quotes
  the chain; `compare.py` publishes the *candidate diagnosis*'s chain,
  not the regression verdict's.
- Every id every direction names is 🟢 except `UX-92` in D3 (⚪ Blocked
  by `UX-514`'s pinned ref), so D3 is a sixth `partial` the Motivation
  did not list.

**The close.** Sixteen `**Status:**` lines, one per direction, in the
`landed` / `partial — …` / `declined — …` vocabulary: 11 landed, 5
partial, 0 declined. Nine guards in
`test_every_direction_names_its_reader.py`; the section walk now bounds
at any `## `, because the old next-Direction bound gave D16 the whole
`## Round history` table.

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_every_direction_names_its_reader.py -q
22 passed in 0.19s
$ make test-touching
17 file(s) selected · 493 passed, 4 skipped in 36.90s
$ make test-small
3707 passed, 36 skipped, 1 warning in 179.05s (0:02:59)
```

| mutation | guard reddened | run |
|---|---|---|
| D8's Status line deleted | `..carries_a_status_line` (+ `..near_the_top`) | 2 failed, 20 passed |
| D9's `partial` stripped to "the rest still to come" | `..names_a_filed_id_or_states_a_decline` | 1 failed, 21 passed |
| D4 `landed` → `shipped` | `..uses_the_vocabulary` | 1 failed, 21 passed |
| D9's three ids → `UX-234` (closed) | `..not_wholly_made_of_closed_filings` | 1 failed, 21 passed |
| D12 `landed` also names `UX-92` (open) | `..names_only_closed_filings` | 1 failed, 21 passed |
| D10's Status pushed below line 10 | `..status_line_is_near_the_top` | 1 failed, 21 passed |
| D13 → `declined — nope.` | `..declined_status_says_why` | 1 failed, 21 passed |
| all 11 `landed` → `partial — declined…` | `..are_not_all_one_word` | 1 failed, 21 passed |
| walk regex → `^## Direction 1` | `..finds_every_direction` (+ pre-existing vacuity guard) | 2 failed, 20 passed |
| D12 `landed` also names `UX-9999` | `..names_only_closed_filings` (no-filing branch) | 1 failed, 21 passed |

**A guard that does not discriminate today.**
`test_a_declined_status_says_why` walks an empty set — no direction is
declined. It was falsified by planting `declined — nope.` (row 7), so it
discriminates when the population is not empty, but it guards nothing
until a direction is declined.

**Deviation from the Required Fix.** Two.

1. **The six tails are named, not filed.** This track may not edit
   `scenarios/README.md`, and a task file without an index row reddens
   `test_every_scenario_has_exactly_one_row_across_the_two_files`. The
   status lines cite `UX-593`..`UX-598` and are written as if filed; the
   orchestrator files them. Because of that ordering the guard asserts
   *existence* only for the ids a `landed` status names, and for a
   `partial` only that its remainder is not wholly closed — an id a
   `partial` invents cannot be caught until the row exists.
2. **D10's tag is recorded, not cut.** Cutting `v0.4.0` from a track
   branch would put a tag on a commit the merge discards. Filed as
   `UX-597` instead of retiring the item, because retiring it is the
   re-argument this task's Out of Scope forbids.
