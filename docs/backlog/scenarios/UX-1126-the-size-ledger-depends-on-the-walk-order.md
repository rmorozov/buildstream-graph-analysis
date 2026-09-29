# UX-1126: the size ledger's duplicate count depends on the filesystem's walk order

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-712 | **Found by:** round 151, PR #301's `sizes` check | **Serves:** anyone whose push-check reads green and whose CI `sizes` reads red | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** test_the_size_ledger_only_shrinks.py

## Motivation

PR #301's `sizes` job failed on `a49e34a3`, "grew: tools/bst_cache_logs.py
duplicate_blocks 0 -> 1", while `dev_sizes.py --check` passed on the same
commit here and in a clean worktree. `dev_sizes.py` handed pylint the
directories, which pylint walks in the filesystem's order, and R0801's
grouping follows file order: the same 30 messages over 5 orders of the
same files attributed the `bst_baseline_set`/`bst_cache_logs` `main()`
block in 3 and not in 2.

## Required Fix

`duplicate_blocks` hands pylint the measured files, sorted by relative
path, rather than the directories; the ledger is re-adopted in that order.

## Out of Scope

The duplicate itself (argparse boilerplate `UX-1118`'s format made
line-identical); pylint's order dependence.

## Acceptance Test

A fake pylint records its argv: the files arrive sorted, never a
directory. `dev_sizes.py --check` passes here and on CI's `sizes` job.

## Outcome

Gap measured: `sizes` on `a49e34a3` exit 1; here `--check` exit 0. The
order experiment: sorted 0, reversed 1, three seeded shuffles 0/1/1
messages naming `bst_cache_logs`, 30 messages each.

Close measured: `--adopt --force` changed 4 cells: `bst_extract_run.py`
duplicate_blocks 7 -> 8, `bst_run_context.py` 8 -> 7 (the total holds),
`dev_sizes.py` file_lines 244 -> 246 and longest_function 33 -> 35.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `*paths` handed to pylint again | `test_the_size_ledger_only_shrinks.py` | 1 failed / 11 |

Deviation: none from the Required Fix.
