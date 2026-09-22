# UX-935: a conflicted path is counted once per stage, so --check --write bakes a wrong number and calls the tree clean

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-688, UX-501 | **Blocks:** — | **Found by:** round 136 — the merge that brought `#261` onto this branch; `--check --write` reported 0 problems over 10 properties and committed `architecture.md` saying 932 files where git has 930 | **Serves:** every catch-up merge, which is the step this repository already runs before every landing | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`architecture.md`'s opening counts the backlog directories, and the
count comes from `git ls-files`. During an unresolved merge **git lists
a conflicted path three times**, once per stage, so the count is the
number of files plus twice the number of conflicts. Replayed in a
detached worktree, merging `3fa407a0` into `2d9b8718`:

```text
$ git diff --diff-filter=U --name-only
docs/backlog/areas/tools.md
docs/backlog/scenarios/README.md
docs/design/architecture.md
$ git ls-files -s docs/backlog/scenarios/README.md
100644 138c000d ... 1  docs/backlog/scenarios/README.md
100644 d45ed5c9 ... 2  docs/backlog/scenarios/README.md
100644 f7fbc7ce ... 3  docs/backlog/scenarios/README.md
$ git ls-files docs/backlog/scenarios | wc -l
932
$ python3 tools/dev_close_task.py --check
  FAIL  architecture.md's opening counts the backlog directories - 2 problem(s)
          architecture.md says 929 ...; git has 932 - `--check --write` rewrites it
          architecture.md says 928 ...; git has 932 - `--check --write` rewrites it
```

The two `says` lines are the conflict markers: the tool is reading both
sides of the hunk as two sentences. That much is loud. **The quiet case
is the one that happened.** Resolve the text first — `git checkout
--ours` on the three, which leaves the index unmerged — and there is
one sentence again, one disagreement, and `--write` silently makes it
agree with 932:

```text
$ git show bf2b5eea:docs/design/architecture.md | grep -o 'the [0-9]* `docs/backlog/scenarios/` files'
the 932 `docs/backlog/scenarios/` files
$ git ls-files docs/backlog/scenarios | wc -l      # after `git add`
930
```

`0 problem(s) over 10 propert(y/ies)` was printed over a number that is
wrong by exactly twice the conflict count, and the merge commit carried
it. The derived-count discipline (`UX-501`, `UX-688`) exists so nobody
types these figures; a derivation that reads a conflicted index derives
a figure nobody typed and nobody can check either.

The repository merges the base branch into a branch before every
landing — that is the trial-merge step round 135 adopted — so this is
not a rare state. It is the state the tool is most likely to be run in
right after a conflict, because resolving the registers is *why* it is
run.

## Required Fix

`--check` establishes whether the index has unmerged paths (`git
ls-files -u`, empty or not) before it derives anything from
`git ls-files`, and refuses with one line naming the state rather than
reporting a count. `--write` must write nothing in that state: a wrong
number that is committed is worse than a run that declines.

The alternative — de-duplicating the stage list and carrying on — is
cheaper and wrong: the rows themselves are mid-resolution, so the
counts sentence and the topic table would be derived from a tree the
author has not finished writing.

## Out of Scope

The conflicts themselves, and which side to take: that is the author's
judgement and `UX-920`'s rule covers ids. `UX-932`'s sandbox escape,
which is a different writer in the same tool.

## Acceptance Test

With one unmerged path in the index, `--check` exits non-zero naming
the unmerged state and `--write` leaves `architecture.md`,
`scenarios/README.md` and every `areas/*.md` byte-identical; with the
index clean the same fixture derives as it does today. A mutation that
drops the unmerged-index question reddens it, and so does one that
de-duplicates the stages and derives anyway.

## Outcome
