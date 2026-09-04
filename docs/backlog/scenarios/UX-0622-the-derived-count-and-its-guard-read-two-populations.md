# UX-622: the derived count and its guard read two populations

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-617 (the widening), UX-501 (the derivation) | **Found by:** round 85, in UX-617's own Deviation section | **Serves:** the session filing a row | **Topic:** guards

## Motivation

`UX-617` widened `dev_close_task.py`'s population to the index **plus**
`git ls-files --others --exclude-standard`, so `--check` sees a row
that is written but not staged. The guard that reads the figure it
writes did not move:

```text
tools/dev_close_task.py::_backlog_counts       index + untracked
tests/unit/test_a_counted_figure_is_derived.py::_backlog_files   index
```

So `--write` now writes a count the guard rejects until the new file
is staged. `UX-617` recorded this rather than fixing it, on the
argument that the red is the loud direction — which is true and is not
the same as the two agreeing.

The cost is a workflow with a trap in it: run `--check --write` before
staging and the suite goes red on a figure the helper just called
clean. That is the shape `UX-617` exists to remove, one level over.

## Required Fix

Decide which population is the contract and make both sides read it,
or state in one place why they differ and have a guard assert the
difference is the intended one.

`architecture.md`'s sentence is what a reader reads; whichever
population is chosen, the sentence must say which.

## Out of Scope

- `UX-617`'s widening itself — closed, and the direction is right.
- The count's arithmetic (`UX-501`).

## Acceptance Test

A written-but-unstaged task file, `--check --write`, then the guard —
green, or red with a sentence saying it is red on purpose.

## Outcome (round 85, 2026-09-04) — 🔴 Open

**Premise:** held, both halves, re-measured on `245dfed`.

### The gap, measured

`_backlog_counts` is `_backlog_paths` + `_untracked_backlog`;
`_backlog_files` was `_tracked()`, plain `git ls-files`. A row written
and left unstaged, end to end:

```text
$ python tools/dev_close_task.py --check --write
  ok    architecture.md's opening counts the backlog directories
0 problem(s) over 5 propert(y/ies), 624 backlog row(s)
--write changed 1 file(s) - stage them:
    docs/design/architecture.md              # it wrote 627
$ pytest tests/unit/test_a_counted_figure_is_derived.py
FAILED ...::test_the_count_is_the_directory[scenarios]
  should say '626 ...'; the index holds 626      1 failed, 30 passed
```

### Which population, and why

The guard read the **index**, not `HEAD`. With one row staged and not
committed:

```text
$ git ls-tree -r --name-only HEAD | grep -c docs/backlog/scenarios/  626
$ git ls-files                    | grep -c docs/backlog/scenarios/  627
$ pytest -k "the_count_is_the_directory and scenarios"
  should say '627 ...'; the index holds 627               1 failed
```

So it was never asking "what does a clone have" — a clone of `HEAD` has
626 and it demanded 627. `git ls-files` is `HEAD` plus staged changes:
both sides already asked *what a commit from here would carry*, and
differed only in stopping at the staging boundary. One question, so one
population — the widened one. Shape one, not shape two.

### After

```text
$ python tools/dev_close_task.py --check --write | tail -3
0 problem(s) over 5 propert(y/ies), 624 backlog row(s)
--write changed 1 file(s) - stage them:
    docs/design/architecture.md
$ pytest tests/unit/test_a_counted_figure_is_derived.py   36 passed
```

The sentence now names the population the number cannot ("...and the 75
`docs/backlog/tasks/` files this commit carries").

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| M1 | `_backlog_files` back to the index alone (the gap) | agreement / non-vacuity / carries, 3 failed 33 passed |
| M2 | `_backlog_counts` back to the index alone | **agreement alone**, 1 failed 35 passed |
| M3 | `--exclude-standard` dropped from `_backlog_files` | carries + agreement, 2 failed 34 passed |
| M4 | the `endswith("/")` filter dropped | nested-worktree alone, 1 failed 35 passed |
| M5 | fixture stages the second row | **non-vacuity alone**, 1 failed 35 passed |
| M6 | "this commit carries" dropped from the sentence | sentence-names-population alone, 1 failed 35 passed |

`M2` is the one that matters: drift reintroduced on the *tool's* side,
how this item arose, and only the agreement clause sees it.
`test_that_agreement_is_not_vacuous` does not discriminate under `M1` —
it reads `_backlog_files` too and co-reddens; `M5` is what it exists
for. The guard derives the population itself rather than importing
`_backlog_counts`: an instrument reading the tool's answer could not
redden under `M2` (the proxy shape, §5).

### Deviation from the Required Fix

None. `--write`'s output for `README.md` is unchanged — that sentence
derives from index *rows*, not the file population.

```text
$ make lint            All checks passed!
$ make test-touching   31 file(s) selected · 753 passed, 3 skipped
```
