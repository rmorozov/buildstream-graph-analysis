# UX-232: a backlog you can navigate at 234 items

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-231 (the Serves lines it indexes) | **Serves:** the maintainers — every role, indirectly

## Motivation

The user's observation, measured: the scenarios README is ~890 lines
carrying 226 rows, each row a paragraph duplicating what the task
file's own log says; open items sit interleaved with five months of
closed history; and ideas parked in `Out of Scope` sections have
already been lost and re-dug-out at least once. The backlog's format
was designed at thirty items and is now the slowest document in the
repository to answer its own question: *what is open, on what topic,
for whom?*

## Required Fix

1. **Split by liveness.** `README.md` keeps: the index (per-topic
   counts and links), every **open** row, and the round sections for
   rounds still having open items. Closed rows move verbatim to
   `closed.md` (same table shape — history is preserved, not
   rewritten). A row moves in the same commit that flips its marker.
2. **Rows shrink to their index job:** id, title (linked), topic,
   priority, `Serves:`, status. The narrative each row currently
   carries lives where it always also lived — the task file's
   motivation and What-was-built log. No prose is deleted; the
   duplicate is.
3. **A topic taxonomy, one word per row:** `capture`, `analysis`,
   `contracts`, `viewer`, `cli`, `store`, `docs`, `guards`. Assigned
   mechanically from each task's subject; disputes resolved in the
   task file, not the row.
4. **Out-of-scope mining, once and then by rule.** Sweep every
   filing's `Out of Scope` section: each entry either references a
   task id (existing or newly stubbed) or states its decline reason
   inline. The style guide gains the rule; a guard holds it for
   files from UX-227 up.
5. **Guards move with the split:** the row-per-file and
   marker-agreement tests cover both files; a new one asserts every
   row is in exactly one of the two; the split-table blank-line
   guard covers both.

## Out of Scope

- Renumbering anything (UX ids are load-bearing everywhere).
- Rewriting history (closed rows move verbatim).
- Converting to an external tracker.

## Acceptance Test

Row count before equals rows(README) + rows(closed) after, asserted
in the migration commit; every task file has exactly one row across
the two files and markers agree (existing guards, retargeted);
every open row carries a topic from the closed set (guard); the
out-of-scope guard reddens on a new filing whose Out of Scope entry
neither references a task nor states a decline; all links resolve
(existing link guard, both files).
