# UX-617: the derived count cannot see an unstaged row

**Priority:** Low | **Status:** 🟢 Done Open | **Depends on:** UX-501 (the derived counts), UX-336 (the helper) | **Found by:** round 84, three times | **Serves:** the session filing a row | **Topic:** guards

## Motivation

`dev_close_task.py --check --write` derives `architecture.md`'s file
count from `git ls-files`, which reads the **index**. A task file that
has been written but not staged is invisible to it, so the natural
order — write the row, derive the counts, stage, commit — leaves the
count one short and says nothing:

```text
$ python tools/dev_close_task.py --check --write
0 problem(s) over 5 propert(y/ies)
$ git add … && git commit && make test
FAILED test_a_counted_figure_is_derived.py::…test_the_count_is_the_directory[scenarios]
  architecture.md says 613 `docs/backlog/scenarios/` files; git has 615
```

It happened **four times in round 84**, and each time the cost was a
full-suite run — eight minutes — to learn something the helper had
just been asked and had answered "clean".

The fourth had a second shape, and it caught the row that filed this
one. `--check --write` also rewrites `README.md`'s counts sentence, so
staging that file *before* deriving leaves the rewrite unstaged and
ships a commit short. The safe order is stage, derive, stage again —
which is a workflow nobody will remember.

The helper is not wrong about the repository; it is wrong about the
question it was asked, which was "is the tree I am about to commit
consistent".

## Required Fix

`--check` counts what a commit from here would carry — the index plus
untracked, non-ignored scenario files — or, if it deliberately reads
only the index, it says so when an untracked scenario file is present
rather than reporting clean.

And `--write` reports the files it changed, so a caller who has
already staged them knows to stage again.

## Out of Scope

- The count itself and `UX-501`'s derivation — right, and unchanged.

## Acceptance Test

An unstaged new task file, and `--check` naming it instead of
reporting a clean tree.

## Outcome (round 85, 2026-09-04) — 🟢 Done

**Premise:** held, both shapes, re-measured on `5343bd6`.

### The gap, measured

```text
$ cp …UX-0617….md docs/backlog/scenarios/UX-0999-a-premise-measurement.md
$ git ls-files | grep -c '^docs/backlog/scenarios/'      619
$ ls docs/backlog/scenarios/*.md | wc -l                 620
$ python tools/dev_close_task.py --check
  ok    architecture.md's opening counts the backlog directories
0 problem(s) over 5 propert(y/ies), 617 backlog row(s)   exit=0
$ git add …UX-0999….md && python tools/dev_close_task.py --check
  FAIL  architecture.md says 619 …; git has 620          exit=1
```

Second shape, same run: `--check --write` after staging left
` M docs/design/architecture.md` in `git status` and printed nothing
about it — the rewrite ships unstaged, one commit short.

### After

```text
$ python tools/dev_close_task.py --check          # UX-0999 written, not staged
  FAIL  architecture.md's opening counts the backlog directories - 1 problem(s)
          architecture.md says 619 `docs/backlog/scenarios/` files; git has 620
          - `--check --write` rewrites it; not yet staged:
          docs/backlog/scenarios/UX-0999-a-premise-measurement.md
1 problem(s) over 5 propert(y/ies), 617 backlog row(s)   exit=1
$ python tools/dev_close_task.py --check --write | tail -3
0 problem(s) over 5 propert(y/ies), 617 backlog row(s)
--write changed 1 file(s) - stage them:
    docs/design/architecture.md
$ python tools/dev_close_task.py --check --write | tail -1   # nothing left to move
--write changed no file(s).
```

The population is the index **plus** `--others --exclude-standard`.
Measured that git does not descend into a nested worktree: it lists
`.claude/worktrees/agent-1/` as one entry, so `UX-577`'s exclusion
survives the widening.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | `_backlog_counts` back to the index alone | count / acceptance / boundary, 3 failed 2 passed |
| A2 | `; not yet staged: …` suffix dropped | acceptance only, 1 failed 4 passed |
| A3 | `--exclude-standard` dropped from the untracked half | boundary, `assert 3 == 2` |
| A4 | untracked half replaced by `REPO.rglob(…)` | boundary `assert 5 == 2` + count, 2 failed |
| A5 | `_write_if_changed` reports every call | "changed nothing", 1 failed 5 passed |
| A6 | `_write_if_changed` reports no call | "names the files", 1 failed 5 passed |

`test_a_nested_worktree_and_an_ignored_file_are_not_counted` does not
discriminate alone: it asserts `== 2` and so co-reddens with A1. A3 and
A4 are what it exists for; it is a boundary clause on the same count,
not a second reading of it.

### A fifth occurrence, adjacent and not fixed here

Round 85's closing commit for `UX-620` staged with a path-scoped
`git add -u docs/backlog/scenarios/`; the fix lived outside that path,
so the row moved to `closed.md` and the branch stayed red until
`471b53a`. Same family, not this item's shape — `--check` was never
asked.

### Deviation from the Required Fix

None. Both clauses implemented; the first branch of clause 1 (count the
untracked half) was taken over the second (report and stay index-only).
Consequence recorded rather than fixed: `--write` now writes a count
`test_a_counted_figure_is_derived.py` (index-only) rejects until the new
file is staged. Left alone to keep the surface at the two files the
Decomposition names; the red is the loud direction, not the silent one.

```text
$ make test-touching   16 file(s) selected · 544 passed, 3 skipped in 39.24s
$ make lint            All checks passed!
```
