# UX-1382: cut release 0.6.2, patch

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1379 | **Found by:** Ruslan, "make this support as 0.6.2" (2026-11-05) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_a_release_records_a_contract_state.py

## Motivation

The newest release is 0.6.1 (2026-11-03, closed-row marker 1311). The
contract set and command surface on `276b4df5` are 0.6.1's, so the cut is
`patch`; what it ships is `UX-1379`'s 3.11 floor. Gates:

- **Review**: review 39 carries marker 1311, at or after 1311.
- **Walk**: [`walk-seed-6.md`](../../audits/walk-seed-6.md), 2026-11-03, after
  the candidate (`2f17326c`, 2026-11-01); no candidate file moved since.

## Required Fix

Release guide §"Cutting one": a 0.6.2 row, `patch`; 0.6.1 frozen with its
digest; the body from `bga release-notes`; the version in
`bga/__init__.py` and `pyproject.toml`. The tag `v0.6.2` is Ruslan's.

## Out of Scope

The rows that go into 0.6.2 are their own.

## Acceptance Test

`tests/unit/test_a_release_records_a_contract_state.py` passes with 0.6.2
as the newest row and derives `patch`, apart from the tag clauses, which
wait for `v0.6.2`.

## Outcome (round 176, 2026-11-05) — 🟢 Done

**Gap measured.** On `5302eba2`: newest versioned row `0.6.1`, 1311,
`patch`; its state block is the tree's
(`test_the_recorded_state_is_the_real_one_for_the_newest_release` green),
so `derive(0.6.1, tree)` -> `patch`.

**Close measured.** `CHANGELOG.md`: a `0.6.2` row, `patch`, 2026-11-05,
closed rows 1313; `0.6.1` frozen with its digest; body from `bga
release-notes --from 1311 --to 1313`; `bga/__init__.py`, `pyproject.toml`
and `test_a_shadowed_checkout_warns_at_startup.py` at `0.6.2`.

review: review 39 at marker 1311, `UX-1380` and `UX-1381` carried in the head. walk: seed 6, 2026-11-03, still after the candidate. The `TestEveryVersionedReleaseIsTagged` clauses red until `v0.6.2` is tagged on this commit (Ruslan's, release guide step 8).

Mutation: none - the cut writes no guard; `test_the_increment_matches_the_kind` already reddens on a wrong kind.
