# UX-996: a derived figure is computed where it is read, never committed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-501, UX-688, UX-756 | **Blocks:** — | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 14:44, answering the workflow review ([doc](https://claude.ai/code/artifact/7f65768e-b4bb-405a-b3e1-90a672a249f5)) | **Serves:** every pair of branches that close rows in the same round | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

Re-running `git merge-tree --write-tree --name-only` on the 19 catch-up
merges since 2026-09-10: 12 conflicted, on 47 paths, and 40 of those
paths are registers or derived documents (`README.md` 11, `areas/tools.md`
9, `architecture.md` 7, `closed.md` 5, `quality_reference.json` 4,
the fixing guide 4). Only 3 of the 12 touched code. Each closing branch
re-derives only its own closure, so a clean merge is not a consistent
tree. The owner chose to stop committing them on 2026-09-23 14:44.

## Required Fix

The figures `dev_close_task.py --check --write` and `dev_touching.py
--spread --write` produce stop being committed: the counts sentence and
topic table, the area pages, and every document figure that counts rows,
files or modules. Where a reader needs the number, the document names
the command that prints it.

## Out of Scope

`closed.md` and the open index's rows, which carry a human note. The
records CI measures (`UX-997`).

## Acceptance Test

Two scratch branches off one base, each closing a different row, not
adjacent in the open table, with `--move`, merge with no conflict and a
green `--check`.

## Decision

The `architect`, round 139 (`UX-993`), at `0b9b72cd`.

```text
Route:     nothing writes or commits the five aggregate figures. `dev_close_task.py --check`
           becomes read-only (its --write goes; --shape --write stays); new `--counts` prints
           the counts sentence and topic table, new `--areas [NAME]` prints an area page;
           `dev_touching.py --spread` prints without --write. Each document names the command
           where it carried the figure. docs/backlog/areas/ (12 pages) is `git rm`ed.
           architecture.md:3 loses its two counts. `.gitattributes`:
           `docs/backlog/scenarios/closed.md merge=union`, because every pair of closes
           collides on closed.md's last row.
Rejected:  areas pages built by CI into an artifact - nobody reads them outside tests
           merge=union on README.md - resurrects adjacent deleted rows; its own row
           tests/quality_reference.json - a ratchet ceiling, not a derived figure (UX-997's kind)
           the ~60 KB size figure and product-population counts - 0 conflict hunks
           keep writing and re-derive after the merge (UX-501) - that produced the 40 of 47
Files:     tools/dev_close_task.py (the write_* functions, their CHECKS rows, --check --write;
           add --counts, --areas); tools/dev_touching.py (COST_SITES, the --spread write);
           README.md:18-30; architecture.md:3; docs/backlog/areas/*.md (rm); .gitattributes;
           fixing-guide.md:71,86,578-587; rules.md; CLAUDE.md; verify, decompose, implementer.md;
           the guards that compare committed with derived (retire or re-point, below)
Guard:     tests/unit/test_a_derived_figure_is_printed_not_committed.py: no tracked .md
           matches the counts sentence, topic table, backlog count or the spread figure;
           `git ls-files docs/backlog/areas` is empty; `--counts` prints index_header(); two
           branches in a temp repo each --move a non-adjacent row, merge with exit 0, --check green
Mutation:  put back README's counts sentence; fixing-guide's `32-165 of 590`; architecture's
           count; `git add -f` one areas page; --counts prints a constant; drop the union line -
           each reddens it
Class:     process
Split:     one bounded track. After #284 (it rewrites the same derived lines)
Question:  none
```

Guards that retire or re-point: `test_the_loop_stays_fast.py` (the committed-count clauses,
`TestTheDerivedCountSeesAnUnstagedRow`), `test_a_counted_figure_is_derived.py`
(`TestTheArchitectureCountsTheBacklogItSendsYouTo`, `TestBothSidesReadOneBacklogPopulation`),
`test_docs_links_and_commands.py:1247`, `test_every_task_names_its_area.py:113-150`,
`test_a_sandboxed_write_stays_in_the_sandbox.py` (now: `--check` writes no file),
`test_an_unmerged_index_derives_nothing.py` (the refusal stays),
`test_a_batch_closes_in_one_move.py:75`, `test_the_cost_row_is_derived_from_the_selector.py`.
Measured on 62 catch-up merges since 09-10: README 34, `areas/tools.md` 28, `architecture.md` 22,
`closed.md` 18, the fixing guide 14 conflicted paths; 44 of `architecture.md`'s 48 conflicted
lines are its `:3` count.
