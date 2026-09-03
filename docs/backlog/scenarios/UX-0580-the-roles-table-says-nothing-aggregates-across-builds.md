# UX-580: the roles table says nothing aggregates across builds

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-231 (the same-commit rule for this table), UX-234, UX-339 | **Serves:** R5 and R7, whose rows are wrong about them | **Topic:** docs

## Motivation

```text
roles.md:43   R5 "nothing aggregates across builds"       bga/store_aggregate.py:82-96: min/median/p95/max/MAD per host class (UX-234 🟢)
roles.md:45   R7 "nothing speaks about variance or worst-case"   the same document, and `bga sweep --format json` (UX-339, R5)
roles.md:90   rule 3: the table changes in the same commit as the service   six commits since round 27, none touched these rows
Serves counts   R1 75 · R2 15 · R3 7 · R4 5 · R5 12 · R6 0 · R7 21 · R8 23   (335 of 560 files carry a Serves line; 231 name no role id)
```

The gap-analysis sentence the round-27 history row still quotes —
"four served thoroughly, four barely" — is half true: R6 is still
unserved and the guard pins it, but R5 and R7 are served by exactly
the mechanisms their rows deny.

**Re-measured 2026-09-03, before implementing.** Two figures above
moved; both claims held.

```text
Serves counts   R1 75 · R2 15 · R3 7 · R4 5 · R5 13 · R6 0 · R7 22 · R8 23
                362 of 587 files carry a Serves line; 257 name no role id
  closed only:  R1 75 · R2 15 · R3 6 · R4 5 · R5 12 · R6 0 · R7 21 · R8 23
git log --oneline -- docs/design/roles.md | wc -l   ->  4, not six
  of those, one touched a role row: ddafaf1 (UX-478), R3's. None
  touched R5's or R7's, which is the claim the "six" was evidence for.
bga/store_aggregate.py:81-102 (the file cites 82-96)  distribution()
```

The all-status R5/R7 counts exceed the closed ones by exactly one:
this filing. The guard below therefore counts **closed** filings only.

## Required Fix

The R5 and R7 rows rewritten against `UX-234`/`UX-339`; the
gap-analysis paragraph dated; and the served/unserved guard extended
from "R6 is the unserved one" to "each row's *served-by* cell names
a closed item that carries that role in its Serves line" — derived
from the counts above, so the next mechanism that serves a role
cannot leave the row stale.

## Out of Scope

- The 231 Serves lines that name no role id — prose Serves were
  allowed from the start; a role id is required only for directions.

## Acceptance Test

Mutation: restore "nothing aggregates" — the served-by guard reds
naming `UX-234`.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — the two rows and the undated paragraph are
real, but "six commits" is 4 and the Serves counts had moved by a
round's filings; both corrected in the Motivation above.

### The gap, measured

```text
$ git log --oneline -- docs/design/roles.md | wc -l
4
$ git show --format= -U0 ddafaf1 -- docs/design/roles.md | grep -E '^[-+]\| R' | cut -c1-58
-| R3 | **The graph owner** — owns the project's dependency shape |
+| R3 | **The graph owner** — owns the project's dependency shape |
```

One of the four touched a role row, and it was R3's. R5's row said
"nothing aggregates across builds" while `bga/store_aggregate.py:81-102`
published `min/median/p95/max/MAD` per host class, and R7's said
"nothing speaks about variance or worst-case" of the same function.

```text
$ grep -n "def distribution" -A 2 bga/store_aggregate.py | head -3
81:def distribution(samples: List[float]) -> Optional[dict]:
82-    """`min/median/p95/max/MAD`, or `None` below the sample floor.
```

### The close

R5 → **Partial** naming `UX-234`/`UX-339`; R7 rewritten against
`UX-234`/`UX-303`; R1/R2/R4/R8 each gained the closed filing their
cell was implicitly claiming; the header cell renamed so the served-by
column has a name; the gap heading dated and given the re-measurement
with the command that produces it; rule 3 now names its guard.

The guard derives the population rather than restating it: closed
filings per role from `git ls-files` over the 587 scenario files. A
role the corpus serves whose last cell names no closed filing carrying
it is the defect; R6 (0 closed) must name none, so the day R6's first
filing closes this reddens.

```text
$ PYTHONDONTWRITEBYTECODE=1 python3 -m pytest \
    tests/unit/test_the_roles_table_names_who_serves_it.py \
    tests/unit/test_every_direction_names_its_reader.py -q | tail -3
tests/unit/test_the_roles_table_names_who_serves_it.py ........   [ 38%]
tests/unit/test_every_direction_names_its_reader.py .............  [100%]
21 passed in 0.19s
```

New file, single-process: **0.08s**, 8 tests — small tier by
inheritance, no `tiers.py` entry needed.

### Mutations verified red and reverted (5)

| mutation to `roles.md` | reddened | run |
|---|---|---|
| R5's cell restored to "**Gap.** … nothing aggregates across builds" | `test_a_role_the_corpus_serves_names_a_closed_filing_that_carries_it` — *"R5: the row's served-by cell names nobody … 12 filing(s) do, e.g. UX-234, UX-242, UX-243, UX-253"* | 1 failed, 7 passed |
| `` (`UX-339`) `` → `` (`UX-9999`) `` | `test_every_id_a_cell_names_is_a_filing_that_exists` — `[('R5', 9999)]` | 1 failed, 7 passed |
| R6's cell gains `` (`UX-234`) `` | `test_a_role_no_closed_filing_carries_names_nobody` — `[('R6', [234])]` | 1 failed, 7 passed |
| the gap heading's `(… round 83, 2026-09-03)` removed | `test_the_paragraph_says_when_it_was_last_measured` | 1 failed, 7 passed |
| a sixth cell appended to R6's row | `test_the_served_by_cell_is_the_column_the_header_names` — `assert 6 == 5` | 1 failed, 7 passed |

Each named the thing broken and nothing else; the first is this task's
Acceptance Test, run verbatim.

### Deviation

The Required Fix says "each row's *served-by* cell". The table had no
such column and gained none: a seventh column on an already-wide table
buys nothing the last cell does not, and R3's cell already worked this
way. The **header** was renamed to `bga today, and what served it`, and
a guard clause pins the served-by cell to the column the header names —
so an added column reddens rather than silently moving the subject.

One rule was relaxed against the Required Fix's wording: a cell must
name **at least one** closed filing carrying the role, not only such
filings. R3's cell cites `UX-478`, whose `Serves:` line is prose and
names no role id — which is this task's own Out of Scope. Requiring
every id to carry the role would have made that exclusion unenforceable.
