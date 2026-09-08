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

Gap measured (pre-fix, on this checkout):

```console
$ sed -i '699a | UX-999 | a row nobody filed | 🟢 Done |' docs/design/architecture.md
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
56 passed
```

Close measured (post-fix, same mutation):

```console
$ sed -i '699a | UX-999 | a row nobody filed | 🟢 Done |' docs/design/architecture.md
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py::test_the_table_status_matches_the_task_files -q
FAILED ... AssertionError: a status table and its task files disagree about status:
    UX-999 (docs/design/architecture.md): a row with no task file
$ git checkout -- docs/design/architecture.md   # restore
$ python3 -m pytest tests/unit/test_docs_links_and_commands.py -q
56 passed in 27.86s
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| append `\| UX-999 \| a row nobody filed \| 🟢 Done \|` to architecture.md's history table | `test_the_table_status_matches_the_task_files`, naming `docs/design/architecture.md` | 1 failed / 56 |
| remove it | — | 56 passed |
