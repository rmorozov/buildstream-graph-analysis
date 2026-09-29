# UX-1129: a union merge reopens swept bookkeeping lines

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-998 | **Found by:** round 149's bookkeeping ledger, promoted at round 152's sweep | **Serves:** every round's sweep | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_union_merge_does_not_reopen_a_swept_line.py`

## Motivation

`.gitattributes` gives `docs/backlog/bookkeeping.md` `merge=union`, so
two branches that mark one line differently keep both copies after a
merge: the `open` copy and the `swept` copy. Round 149 reopened 12
lines across two merges that way:

```text
git log --merges -p -- docs/backlog/bookkeeping.md | grep -c '^+- r'
```

## Required Fix

`tools/dev_bookkeeping.py` reads a finding present both open and
resolved (same derived key) as resolved, and `--sweep` collapses the
pair to the resolved copy, so a union merge cannot reopen a line.

## Decision

- **Route:** `sweep()` skips an open line whose derived key also has a resolved line; a new `--collapse` verb drops the open copy. `validate()` still names the duplicate, so `--add`/`--mark` refuse until `--collapse` runs. Same commit fixes `with_shape` in `dev_close_task.py`: replace in place, else insert before Reading.
- **Rejected:** collapsing inside `--sweep` (a listing verb must not write); dropping `merge=union`.
- **Files:** `tools/dev_bookkeeping.py`, `tools/dev_close_task.py`, `tests/unit/test_a_union_merge_does_not_reopen_a_swept_line.py`.
- **Guard:** that test: an open+swept pair lists nothing in either order; `collapse` leaves the swept line only; `with_shape` lands before Reading.
- **Mutation:** drop the resolved-key filter in `sweep`; make `collapse` drop nothing; disable the before-Reading branch.
- **Class:** tools

## Out of Scope

Dropping `merge=union`, which is what lets parallel filers append
without colliding.

## Acceptance Test

A ledger holding one key twice, `open` and `swept r152 ...`, lists
nothing under `--sweep`, and `--sweep --write` (or the tool's collapse
verb) leaves one line. Mutation: prefer the open copy; the test reddens.

## Outcome

Gap measured: a temp ledger holding one key open and `swept r152` listed the open copy under `--sweep` (no filter existed); `with_shape` appended Shape after Reading.

Close measured: `python3 -m pytest -q -n 0` on the new guard, `test_a_bookkeeping_finding_is_one_line.py` and `test_a_task_declares_its_shape.py`: 34 passed.

| mutation | red | count |
|---|---|---|
| sweep: drop the resolved-key filter | test_the_open_copy_of_a_swept_key_is_not_listed | 1 failed, 3 passed |
| collapse drops nothing | test_collapse_leaves_the_resolved_line_only | 1 failed, 3 passed |
| with_shape: disable the before-Reading branch | test_shape_write_goes_before_reading_and_replaces_in_place | 1 failed, 3 passed |

