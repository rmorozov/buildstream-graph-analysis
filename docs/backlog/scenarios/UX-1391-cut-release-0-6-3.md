# UX-1391: cut release 0.6.3, patch

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan, "let's issue new 0.6.3 release" (2026-11-27) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_a_release_records_a_contract_state.py

## Motivation

The newest release is 0.6.2 (2026-11-05, closed-row marker 1313). The
contract set and command surface on `81f3512d` are 0.6.2's, so the cut is
`patch`; what it ships is the twelve rows closed since, and the four
findings the walk and review below filed, fixed ahead of the cut at
Ruslan's word ("let's fix found issues in scope of this PR"). Gates:

- **Review**: review 40 carries marker 1325, at or after 1313.
- **Walk**: [`walk-seed-7.md`](../../audits/walk-seed-7.md), 2026-11-27, after
  the candidate (`5b6c37ec`, `UX-1385`, 2026-11-26).

## Required Fix

Release guide §"Cutting one": a 0.6.3 row, `patch`; 0.6.2 frozen with its
digest; the body from `bga release-notes`; the version in
`bga/__init__.py` and `pyproject.toml`. The tag `v0.6.3` is Ruslan's.

## Out of Scope

The rows that go into 0.6.3 are their own.

## Acceptance Test

`tests/unit/test_a_release_records_a_contract_state.py` passes with 0.6.3
as the newest row and derives `patch`, apart from the tag clauses, which
wait for `v0.6.3`.

## Outcome (round 176, 2026-11-27) — 🟢 Done

**Gap measured.** On `81f3512d`: newest versioned row `0.6.2`, 1313,
`patch`; `test_a_release_records_a_contract_state.py` 47 passed, so the tree's
state is 0.6.2's and `derive(0.6.2, tree)` -> `patch`.

**Close measured.** `CHANGELOG.md`: a `0.6.3` row, `patch`, 2026-11-27,
closed rows 1330; `0.6.2` frozen with digest `482ae001b0f6`; body from `bga
release-notes --from 1313 --to 1330`; `bga/__init__.py`, `pyproject.toml`
and `test_a_shadowed_checkout_warns_at_startup.py` at `0.6.3`.

review: review 40 at marker 1325; its `UX-1392` and `UX-1393` closed ahead of the cut. walk: seed 7, 2026-11-27; its `UX-1389` and `UX-1390` closed ahead of the cut. The first cut, `2b37fbb0`, was reverted by `7e7b5db3` so the tag names a commit that carries them; walk seed 6's `UX-1376` ships open. The `TestEveryVersionedReleaseIsTagged` clauses red until `v0.6.3` is tagged on this commit (Ruslan's, release guide step 8).

Mutation: none - the cut writes no guard; `test_the_increment_matches_the_kind` already reddens on a wrong kind.
