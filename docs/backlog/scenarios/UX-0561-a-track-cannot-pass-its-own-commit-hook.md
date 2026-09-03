# UX-561: a track that closes an item cannot pass its own pre-commit selector

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-501 (the index counts), the `decompose` skill (which owns the split) | **Found by:** round 81's two tracks, independently | **Serves:** every track that closes a row | **Topic:** guards

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

## Outcome (round 81, 2026-09-03) — 🟢 Done

### The gap, measured

Both of round 81's tracks reported the same three clauses red for one
fact, and both reached for the hook's escape to commit correct work:

```text
UX-558: table says 🔴, UX-0558-….md says 🟢
  test_the_table_status_matches_the_task_files
  test_check_reports_a_clean_tree_as_clean
  test_a_hand_edited_count_is_reported_and_then_restored
```

One track proved they were only the mandated split: setting the Status
line back to 🔴 turned all three green (`69 passed`), then restored 🟢.

### The decision

The row offered two routes and this takes the second: **the guard
learns the state.** A track moving its own row would reintroduce
exactly the `README.md`/`closed.md` merge conflicts the `decompose`
skill made the split to avoid — round 75 paid three cherry-picks, one
conflicted, for that shape.

Narrow on purpose, three ways:

- only in a **linked worktree** — `.git` is a file there, a directory
  in the shared checkout, so the test costs no subprocess and works
  with git absent;
- only in the direction **file 🟢, row 🔴** — the instructed state;
- and it **prints** the rows it is holding, so a track sees them and
  the orchestrator's `--move` is still what closes them.

`🟢` in the table over `🔴` in the file — the drift `UX-131` found in
three separate rounds — still fails everywhere, worktree or not.

### After

Measured in a real linked worktree, staged into the instructed state:

```text
$ git worktree add --detach /tmp/…/ux561-probe HEAD
$ test -f /tmp/…/ux561-probe/.git && echo "yes (linked)"
yes (linked)
$ cd /tmp/…/ux561-probe && pytest … -k table_status
1 passed, 38 deselected in 0.12s
```

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| M1 | the same 🟢/🔴 state in the **main** checkout | `test_the_table_status_matches_the_task_files` — 1 failed |
| M2 | the **opposite** direction (row 🟢, file 🔴) in the worktree | the same clause — 1 failed |

M1 is the one that matters: it proves the exemption is the worktree's
and not a hole in the guard. M2 proves `UX-131`'s original claim is
untouched.

### Deviation from the Required Fix

**None.** The row named two candidates and required only that a track
not have to disable a correctness hook to commit correct work; the
candidate taken is one it named, and the reason the other was rejected
is on file above.
