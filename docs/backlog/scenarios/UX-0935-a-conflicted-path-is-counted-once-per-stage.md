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
it. **What clears the inflation is `git add`, not the text
edit**, measured on the same replay:

```text
$ git ls-files docs/backlog/scenarios | wc -l   # conflicted
932
$ git checkout --ours <the three>; git ls-files docs/backlog/scenarios | wc -l
932
$ git add <the three>;             git ls-files docs/backlog/scenarios | wc -l
930                                             # MERGE_HEAD still present
```

So the protecting habit is not "re-derive after the merge" — it is
re-derive once the resolution is **staged**, with `git status --short`
showing no `UU`; a merge commit implies that and is the simplest form
of it. `#263`'s thread ran its derive after committing its merge and
read 930 against 930 on the same base, which is the control.
 The derived-count discipline (`UX-501`, `UX-688`) exists so nobody
types these figures; a derivation that reads a conflicted index derives
a figure nobody typed and nobody can check either.

Three of this afternoon's four findings are one shape, and it is a
shape the fixing guide already names: **the wrong artifact or
population** (§5's proxy rule, `UX-359`'s row). The quantity read is
right; the tree it is read from is not the tree the name claims.
`UX-930`'s fixture cloned one level under its own basename, `UX-932`'s
guard writes the live tree from a tmp copy, and this row derives from
an index mid-merge. `UX-934` is the odd one out and worth keeping
separate: there the record is fine and **no instrument reads it at
all**. The family is worth stating because the proxy rule is written
about measurements, and all three of these read a *tree* — the same
question ("what is actually being read?") asked of an input nobody
thinks of as an instrument's input.

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

**Round 138, 2026-09-23**

**Premise:** held — the quiet case reproduces on a three-file fixture.

### The gap, measured

`tests/unit/test_an_unmerged_index_derives_nothing.py`'s fixture: one
task file changed on both sides of a merge, then `git checkout --ours`.
Run in-process with the refusal removed (the tool as it was):

```text
$ git ls-files -u | wc -l                        -> 3
$ git ls-files docs/backlog/scenarios | wc -l    -> 5     (3 files)
$ dev_close_task.main(["--check", "--write"])
0 problem(s) over 10 propert(y/ies), 1 backlog row(s)
--write changed 3 file(s) - stage them:
    docs/backlog/scenarios/README.md
    docs/design/architecture.md
    docs/backlog/areas/tools.md
exit 0
architecture.md now: It counts 5 `docs/backlog/scenarios/` files ...
```

Clean report, and a count wrong by twice the one conflict, written.

### After

`--check` asks `index_is_merged()` (`git ls-files -u`, in `tools/_close_task_checks.py`) first, on the real
index only, and refuses before any derive or write:

```text
refused: the git index is unmerged (1 path(s) mid-merge:
docs/backlog/scenarios/UX-0001-a-row.md) - stage the resolution with
`git add`, then derive; nothing was checked or written        exit 2
```

One line on stderr; `architecture.md`, `README.md` and `areas/tools.md`
are byte-identical. After `git add` the same fixture derives `1
scenarios: **1 open**, 0 closed.`, keeps `architecture.md` at 3 and
writes `areas/tools.md` - as before. On this tree `--check` still reads
`0 problem(s) over 10 propert(y/ies), 940 backlog row(s)`.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | the unmerged question dropped (`unmerged = []`) | 1 of 3: `test_check_refuses_and_write_writes_nothing` - exit 0, 3 files written |
| A2 | A1 plus `_ls_files` de-duplicating stages (`sorted(set(...))`) | 1 of 3: the same clause - `architecture.md` right at 3, but `README.md` and `areas/tools.md` written mid-merge, exit 0 |

A2 is why the byte-identical clause covers the index and area pages and
not only `architecture.md`: de-duplication fixes the one count and still
writes the rest from rows the author has not finished resolving.

### Deviation from the Required Fix

A `--scenarios` sandbox run does not ask: it reads no `git ls-files`,
and a suite run while the real checkout is mid-merge would otherwise red
every sandboxed guard for a state they do not read.

```text
$ make test-touching     # before the spread figure was re-derived
2 failed, 2035 passed, 4 skipped in 96.45s   # both the spread figure; --spread --write fixed it
```

`make test` runs once on the track's final HEAD (four rows, one box).
