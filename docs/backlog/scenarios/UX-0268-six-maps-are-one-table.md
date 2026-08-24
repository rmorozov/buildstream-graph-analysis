# UX-268: six of the wide maps are one table rendered six times

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-267 | **Serves:** R1 and R3 | **Topic:** viewer

## Motivation

Nobody asked for this one; it came out of measuring the report to
answer the questions that were asked, and it is the largest single
readability win available.

`signals` carries seven maps that scale with the run. Six of them are
**the same element list**, keyed by element UID:

```text
blast_radius              44 keys   (values are records of 6 fields)
criticality_probability   44 keys
downstream_count          44 keys
element_durations         44 keys
slack                     44 keys
unweighted_depth          44 keys
```

They are one table with six columns, and the page renders them as six
separate opaque blobs — so a reader who wants "the slowest element with
the widest blast radius" has to open two of them and join by hand.

The seventh is worse than redundant. `wall_clock_share` is keyed by
**task**, not element:

```text
element-keyed : app.bst
wall_clock_share : app.bst|BUILD|BUILD|0

union 88 keys, intersection 0
```

It shares **no keys at all** with the other six, and nothing on the
page says so. A reader comparing them is comparing different
populations, and the page presents the two identically.

## Required Fix

1. One element table, with a column per element-keyed signal, replacing
   six sections. `UX-216` already made every element one object with
   one anchor; this is that object's row.
2. `wall_clock_share` stays its own table and **says what its key is**,
   because it is not the same population.
3. The per-element sections `UX-216` renders link into the row rather
   than repeating it.

## Out of Scope

- Changing what the analysis publishes. `analyze/v1` is unchanged; this
  is how a page draws it.
- The generic renderer. `UX-267` handles every *other* object; this
  handles the specific redundancy the schema knows about.

## Acceptance Test

The 1,202-element run renders one element table rather than six maps,
sortable by any column, and the task-keyed share is separately labelled
as task-keyed — with a guard that fails if a seventh element-keyed
signal is added and does not join the table.
