# UX-1236: a bare `downstream > N` says what it read, and `downstream_count > N` is guarded

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-161 verification of UX-1228 (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_downstream_clause_follows_the_closure.py::test_a_downstream_comparison_reads_the_count_column_bare_or_named`

## Motivation

UX-1228 declared `downstream` as an undrawn column for the `downstream:<uid>` closure clause. A bare `downstream > 1000` no longer reads the Downstream count column: on the 1,202-element page it shows "25 of 1,202", unfiltered, where `downstream_count > 1000` gives "1 matched". The Outcome says it is said back unread; no guard covers either form.

## Decomposition

Input classes: the 1,202-element two-plane page, Elements table, at 1440.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     parseQuery's threshold branch (bga/viewer/tables.js:120-131): a clause naming a column with no quantity reads the one quantity column whose name carries that word (downstream -> downstream_count); none or several are said back unread with the candidates named.
Rejected:  only saying it back (the column is unambiguous); renaming UX-1228's undrawn downstream key (breaks the closure grammar).
Files:     bga/viewer/tables.js, tests/unit/test_a_downstream_clause_follows_the_closure.py
Guard:     the 1,202-element page: downstream > 1000 and downstream_count > 1000 both read 1 matched.
Mutation:  delete the fallback; make passes return true.
Class:     product
Split:     one track.
```

## Required Fix

A comparison on `downstream` either reads the Downstream count column or is said back as unread with the column it meant named; `downstream_count > N` is guarded.

## Out of Scope

The closure clause itself (UX-1228).

## Acceptance Test

`downstream > 1000` filters to 1 or names `downstream_count`; `downstream_count > 1000` reads "1 matched". Mutation: break the comparison path, and the guard reds.

## Outcome

**Gap measured** (1,202-element two-plane page, Elements table, 1440): before, `downstream > 1000` read "25 of 1,202" (unread, unfiltered); `downstream_count > 1000` "1 matched", unguarded.

**Close measured:** both forms read `matched` 1, badge "1 matched"; `pytest test_a_downstream_clause_follows_the_closure.py` -> 2 passed. A word with none or several quantity columns is said back unread, `column` = the typed name, the table's heads listed.

| Mutation | Reddened | Printed |
|---|---|---|
| fallback deleted (spec read as before) | bare form, `matched` -1 | 1 failed, 1 passed |
| `passes` returns true | bare form, `matched` 1202 | 1 failed, 1 passed |

**Deviation:** none. Candidates are named through the existing heads list, not a new message.
