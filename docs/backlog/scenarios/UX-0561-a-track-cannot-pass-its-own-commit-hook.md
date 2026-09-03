# UX-561: a track that closes an item cannot pass its own pre-commit selector

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-501 (the index counts), the `decompose` skill (which owns the split) | **Found by:** round 81's two tracks, independently | **Serves:** every track that closes a row | **Topic:** tooling

## Motivation

The `decompose` skill makes `docs/backlog/scenarios/README.md` and
`closed.md` merge hotspots a track never touches — the orchestrating
session moves the rows once, at the end. A track therefore finishes
with its task file at 🟢 and its index row still 🔴, which is exactly
what `test_the_table_status_matches_the_task_files` exists to catch:

```text
UX-558: table says 🔴, UX-0558-….md says 🟢
```

Round 81's tracks reported three clauses red for this one fact
(`test_the_table_status_matches_the_task_files`,
`test_check_reports_a_clean_tree_as_clean`,
`test_a_hand_edited_count_is_reported_and_then_restored`), and
`selector-before-commit.sh` blocks the commit on them. Both tracks
reached for `BGA_SKIP_SELECTOR=1`, the hook's documented escape.

So the split-ownership rule and the commit hook disagree, and the
resolution today is that every track disables the hook. A guard
everyone is told to bypass is not a guard, and the bypass is where a
real red would hide.

## Required Fix

Decide which half gives. Either the split is wrong and a track moves
its own row (accepting the merge conflicts the skill was avoiding), or
the guard learns the state "closed in a worktree, index not yet moved"
and reports it as pending rather than failing — a track's tree is not
the tree the rule is about.

The mechanical half is that a track must not have to disable a
correctness hook to commit correct work.

## Out of Scope

- Removing `BGA_SKIP_SELECTOR=1`. It exists for other reasons and this
  row is not about the escape hatch, it is about needing it routinely.
- The three clauses' own correctness: on the orchestrating session's
  tree they are right, and `dev_close_task.py --move` clears them.

## Acceptance Test

A track closes an item in a worktree, leaves the index alone as the
skill instructs, and commits without setting `BGA_SKIP_SELECTOR`.
