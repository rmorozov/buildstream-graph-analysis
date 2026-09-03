# UX-580: the roles table says nothing aggregates across builds

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-231 (the same-commit rule for this table), UX-234, UX-339 | **Serves:** R5 and R7, whose rows are wrong about them | **Topic:** docs

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
