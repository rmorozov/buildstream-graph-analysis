# UX-791: an orphan row in the architecture table is invisible

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-736 (the widened guard) | **Found by:** round 109, retro-verifying round 100 | **Serves:** the reader of a status row for a task that does not exist | **Topic:** docs | **Area:** unassigned | **Shape:** mechanical

## Motivation

`tests/unit/test_docs_links_and_commands.py`'s
`test_the_table_status_matches_the_task_files` iterates
`_file_statuses()` and looks each id up in the two tables. A row in
`docs/design/architecture.md`'s history table for `UX-999` — no
task file, no index row — is never visited:

```console
$ printf '| UX-999 | a row nobody filed | 🟢 Done |\n' >> (the table)
$ python -m pytest tests/unit/test_docs_links_and_commands.py -q
56 passed
```

Both directions of *disagreement* are caught (flip the table, flip
the file — each reds naming both); *absence* is not. `UX-736` widened
the population to the second table and kept the first table's
iteration order.

## Required Fix

`tests/unit/test_docs_links_and_commands.py`'s clause iterates the tables'
own rows too: an id with no task file reds naming the table.

## Out of Scope

- Rows in `closed.md` — `dev_close_task.py --check` owns that index.

## Acceptance Test

`tests/unit/test_docs_links_and_commands.py` reds on the fabricated
`UX-999` row above (the mutation); green with it removed.

## Outcome

_Not started._
