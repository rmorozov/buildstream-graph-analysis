# UX-1395: a tag on a reverted cut passes the tag clauses

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan, review of #353 (2026-11-27) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_release_records_a_contract_state.py::TestEveryVersionedReleaseIsTagged::test_no_later_commit_sets_a_tagged_version_again`

## Motivation

0.6.3 was cut twice and reverted twice on #353 (`2b37fbb0`, `0066be7b`), and
`v0.6.3` was tagged on `0066be7b`. The three `TestEveryVersionedReleaseIsTagged`
clauses ask only that the tag exist, that its `pyproject.toml` say `0.6.3`, and
that it be an ancestor: `git merge-base 0066be7b 5d22a2c1` is `0066be7b`, so all
three hold for the wrong cut, and a green CI would publish code the re-cut replaced.

## Required Fix

A clause that reds when a later commit moves the version up to a tagged
version again — the re-cut the tag should name.

## Out of Scope

Moving the tag; that is the owner's.

## Acceptance Test

With `v0.6.3` on `0066be7b` and the re-cut on this branch, the clause reds
naming the re-cut; on every other tag it passes, a revert (version moving down)
included.

## Outcome (round 176, 2026-11-27) — 🟢 Done

**Gap measured.** `v0.6.3` -> `0066be7b`, HEAD carries the re-cut: the three
existing tag clauses read the same on `0066be7b` as on the re-cut.

**Close measured.** `pytest tests/unit/test_a_release_records_a_contract_state.py -k no_later_commit`:

```text
AssertionError: release tag(s) on a cut a later commit re-made: ['v0.6.3 -> 0066be7b, re-cut at 5d22a2c1']
```

The seven other tags pass, `v0.6.2` across the two reverts that move the
version back down to it.

| mutation | reddened | count |
|---|---|---|
| drop `_version_tuple(before) < _version_tuple(now)` | `v0.6.2` flagged at both reverts (`183f496a`, `7e7b5db3`) | 1 failed |
| `now == row["version"]` -> `False` | nothing flagged: `v0.6.3` on the reverted cut passes | 1 passed |

Deviation: the green half on the right cut waits for the owner moving `v0.6.3`.
