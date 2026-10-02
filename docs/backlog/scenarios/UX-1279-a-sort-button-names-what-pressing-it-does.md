# UX-1279: a sort button's name says what pressing it does, not "sort: By binary"

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-165 walk (2026-10-02) | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Every sortable header's button reads `<Column>, sort: <table>` to a
screen reader (`structured.js`, `UX-1197`): on `#by_binary` each one is
"Blocked, sort: By binary", "CPU, sort: By binary". The sentence names the
table, not the action or the order a press gives; `aria-sort` on the `th`
carries the state, but the button's own name never says which way it will
sort. Present at `53d5d364b`, before round 165.

## Decomposition

Input classes: `macro_micro`'s `by_binary` and `element_durations` tables,
each column unsorted, ascending and descending.

## Required Fix

The button's accessible name says the column and what a press does
("Sort by Blocked, descending"), the table's name once, where `UX-1197`
needed it.

## Out of Scope

The visible header text; `aria-sort` on the `th`.

## Acceptance Test

On `macro_micro`, every sort button's `aria-label` names its column and
the order its next press applies, and changes after a press. Mutation:
restore the `${column}, sort: ${table}` template and the guard reds.
