# UX-754: the derived-figure exclusion cannot read a merge

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-652 (the log's unit), UX-669 (the exclusion) | **Serves:** every round that merges a track and closes a row | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`test_nothing_landed_after_the_commit_the_entry_credits` excuses a
commit that only moved a derived figure in `architecture.md` — the
backlog file counts `dev_close_task.py --write` maintains. That
exclusion is `_only_a_derived_figure_moved`, and it reads:

```python
["git", "show", "--format=", "--unified=0", sha, "--", str(DOC)]
```

`git show` on a **merge commit** emits a *combined* diff, whose prefix
is one column per parent — two, not one. The code strips `ln[1:]`, so
a merge's identical-but-for-a-count line arrives as:

```console
removed[0][:20] = ' **Start here to ori'
added[0][:20]   = '+**Start here to ori'
only_the_count_moved -> False
```

They differ by the surviving prefix character, so the exclusion
returns `False` and the guard reds. Every round that merges a track
and lets the close step bump `751` to `752` hits this.

It is not hypothetical: it reddened CI on `20615ea` (this round's
UX-674 merge) on both 3.11 and 3.12, and it is the *second* cause of
the same red on `UX-748` — recorded there as the oldest-commit anchor
alone, which was incomplete.

## Required Fix

1. Take a first-parent diff so the shape is the two-column one the
   parser assumes: `--first-parent -m` on the `git show`, which
   behaves unchanged for an ordinary commit.
2. **The inverse check:** removing the flags again must redden
   `test_nothing_landed_after_the_commit_the_entry_credits` on a merge
   commit that moved only the count. If it does not, the fix is
   reading something else.

## Out of Scope

- The anchor rule (`closing_commit` taking the oldest match). That is
  deliberate and documented, and it is a separate reason a merge can
  red this guard; `UX-748` squashed to satisfy it. Whether a round
  should merge or squash is a process question, not this defect.
- The other `git show` callers in the suite. None was measured here,
  and a sweep without a measurement is the thing this repository
  files rows about.

## Acceptance Test

`_only_a_derived_figure_moved` returns `True` for a merge commit whose
only change to `architecture.md` is the derived count, and the guard
is green on that merge; the mutation above reddens it.

## Outcome

The gap, reproduced against the guard's own helpers on the merge
commit `20615ea`, whose only change to `architecture.md` was the
derived count `751 -> 752`:

```console
removed[0][:20] = ' **Start here to ori'
added[0][:20]   = '+**Start here to ori'
only_the_count_moved -> False
_only_a_derived_figure_moved -> False
```

Identical lines; they differ only by the prefix column a combined diff
adds and `ln[1:]` fails to strip. The close: `--first-parent -m` on
the `git show`, which yields the two-column shape the parser assumes
and is unchanged for an ordinary commit.

```console
merge commit 20615ea excused -> True
$ python3 -m pytest tests/unit/test_the_verification_log_is_true.py -q
31 passed in 2.83s
```

| mutation | reddened |
|---|---|
| the two flags removed again | `test_nothing_landed_after_the_commit_the_entry_credits`, `stale(['20615ea...'])` |

Reverted from a pristine scratchpad copy, 31 passed again.

**Deviation.** This is the second cause of the same red on `UX-748`,
where it was recorded as the oldest-commit anchor rule alone. That
reading was incomplete: squashing satisfied the anchor and happened to
remove the merge, so the parsing bug went unseen. `UX-748`'s Outcome
keeps its own account; this row carries the correction.
