# UX-232: a backlog you can navigate at 234 items

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-231 (the Serves lines it indexes) | **Serves:** the maintainers — every role, indirectly | **Topic:** docs

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
- Converting to an external tracker — the backlog's value here is that
  it is diffable, reviewable in the same commit as the change it
  describes, and guarded by tests that read it; a tracker keeps none
  of that.

## Acceptance Test

Row count before equals rows(README) + rows(closed) after, asserted
in the migration commit; every task file has exactly one row across
the two files and markers agree (existing guards, retargeted);
every open row carries a topic from the closed set (guard); the
out-of-scope guard reddens on a new filing whose Out of Scope entry
neither references a task nor states a decline; all links resolve
(existing link guard, both files).

## Outcome (round 28)

All five clauses landed. The split conserves exactly:

```text
BEFORE (one file)          936 lines   234 rows   848 mean chars/row
                           225 🟢   2 🟡   7 🔴

AFTER  README.md           192 lines     9 rows   142 mean chars/row
       closed.md           776 lines   225 rows   856 mean chars/row
       union == before?  True     overlap: set()
```

The comparison is by `{id: status cell}`, not by line count: the two
maps merged are the before map, and no id appears in both files. Closed
rows kept their 856 characters because the clause says *verbatim* —
history is not the thing that needed shrinking. What shrank is the
document you read to ask *what is open*: 936 lines down to 192, and the
answer is now the first table rather than a scroll through five months.

The index states `9 open, 225 closed` and a per-topic table, and a guard
counts both against the rows they index.

### The old guard read a column number

`_table_statuses()` found the marker at a fixed column index. That was
safe while there was one table; the split makes two of deliberately
different shape — the open one is an index (id, title, topic, priority,
serves, status), the closed one keeps its narrative — so the retargeted
version scans the row for the cell that *starts with a marker*, which is
the only thing both tables promise. `test_every_task_file_has_a_row_in_the_table`
and `test_the_table_status_matches_the_task_files` now read both files;
had they kept reading one, they would have gone quiet for 225 of 234
rows on the day the split landed, still green.

The seam-5 UX-192 guard in `test_six_seams_round_21_found.py` follows
its row across both files for the same reason.

### A claim of mine that was false

Working out the cell splitter I reported that five rows carried an
unescaped `|`. They did not: those rows escape it as `\|`, and it was my
naive `line.split("|")` that broke them. The splitter is
`re.split(r"(?<!\\)\|", ...)` and the rows were always fine. Recorded
because "we measured and found five defects" and "our instrument had
one" are not the same sentence, and only one of them was true.

### Out-of-scope mining

Twenty `Out of Scope` entries across the nine filings from UX-227 up.
Seventeen already named a task or gave a reason. Three were bare and got
one: UX-230's "don't just add the savings" (UX-219 measured that
`makespan_after_us` differs from `total - cumulative_saving_us` at every
step of the golden fixture), UX-232's tracker decline (the backlog's
value is being diffable in the same commit as the change it describes),
UX-233's rewrite decline (most chapters are still true and a rewrite
loses their review history). Style guide rules 11 and 12 carry the split
and the out-of-scope rule forward; the guard holds it from UX-227 on.

**Mutations verified red and reverted:** a row copied into both files;
an open row moved into `closed.md`; a topic outside the closed set
(`visualisation`); one per-topic index count drifted by one; a bare
`Out of Scope` bullet added to UX-234. Each reddened its own guard and
nothing else.

**Deviation from the Required Fix:** none. Clause 5's split-table and
cell-count guards needed no change — they glob `docs/**/*.md`, so
`closed.md` was covered the moment it existed; verified by mutation
rather than assumed.

Full suite: `3002 passed, 3 skipped in 306.54s`.
