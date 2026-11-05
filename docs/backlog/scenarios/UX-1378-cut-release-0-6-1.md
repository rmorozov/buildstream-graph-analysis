# UX-1378: cut release 0.6.1, patch

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan, "let's issue new small release 0.6.1" (2026-11-03) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_a_release_records_a_contract_state.py

## Motivation

The newest release is 0.6.0 (2026-10-07, closed-row marker 1280), and no
`Unreleased` row stands above it: the contract set and command surface on
`ffcb221f` are 0.6.0's (`test_a_release_records_a_contract_state.py`, 47
passed), so the cut is `patch`. Gates, read on `ffcb221f`:

- **Review**: review 38 carries marker 1292, at or after 1280.
- **Walk**: [`walk-seed-6.md`](../../audits/walk-seed-6.md) on `ffcb221f`,
  dated 2026-11-03, after the candidate (`2f17326c`, 2026-11-01); no
  blocking finding, `UX-1376` and `UX-1377` filed.

## Required Fix

Release guide §"Cutting one": a 0.6.1 row, `patch`; 0.6.0 frozen with its
digest; the body from `bga release-notes`; the version in
`bga/__init__.py` and `pyproject.toml`. The head names the Python floor
(`UX-1348`) and the prebuilt hook's glibc floor (`UX-1373`). The tag
`v0.6.1` is Ruslan's, on this commit after merge.

## Out of Scope

The rows that go into 0.6.1 are their own.

## Acceptance Test

`tests/unit/test_a_release_records_a_contract_state.py` passes with 0.6.1
as the newest row and derives `patch` from the 0.6.0 to 0.6.1 pair, apart
from the tag clauses, which wait for `v0.6.1`.

## Outcome (round 176, 2026-11-03) — 🟢 Done

**Gap measured.** On `ffcb221f`: newest versioned row `0.6.0`, 1280,
`breaking`, no `Unreleased` row; the 0.6.0 state block is the tree's
(`test_the_recorded_state_is_the_real_one_for_the_newest_release` green,
47 passed), so `derive(0.6.0, tree)` -> `patch`.

**Close measured.** `CHANGELOG.md`: a `0.6.1` row, `patch`, 2026-11-03,
closed rows 1311; `0.6.0` frozen with `digest: 482ae001b0f6`
(`state_digest(_states()['0.6.0'])`); body from `bga release-notes --from
1280 --to 1311`, 31 rows; `bga/__init__.py`, `pyproject.toml` and
`test_a_shadowed_checkout_warns_at_startup.py` at `0.6.1`.

walk: [`walk-seed-6.md`](../../audits/walk-seed-6.md) on `ffcb221f`, 2 match and 1 n/a of 3, no blocking finding; `UX-1376` and `UX-1377` carried in the head. The `TestEveryVersionedReleaseIsTagged` clauses red until `v0.6.1` is tagged on this commit (Ruslan's, release guide step 8).

Mutation: none - the cut writes no guard; `test_the_increment_matches_the_kind` already reddens on a wrong kind.
