# UX-617: the derived count cannot see an unstaged row

**Priority:** Low | **Status:** 🔴 Open | **Depends on:** UX-501 (the derived counts), UX-336 (the helper) | **Found by:** round 84, three times | **Serves:** the session filing a row | **Topic:** guards

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

It happened **three times in round 84**, and each time the cost was a
full-suite run — eight minutes — to learn something the helper had
just been asked and had answered "clean".

The helper is not wrong about the repository; it is wrong about the
question it was asked, which was "is the tree I am about to commit
consistent".

## Required Fix

`--check` counts what a commit from here would carry — the index plus
untracked, non-ignored scenario files — or, if it deliberately reads
only the index, it says so when an untracked scenario file is present
rather than reporting clean.

## Out of Scope

- The count itself and `UX-501`'s derivation — right, and unchanged.

## Acceptance Test

An unstaged new task file, and `--check` naming it instead of
reporting a clean tree.
