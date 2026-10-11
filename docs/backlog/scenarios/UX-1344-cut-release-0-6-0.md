# UX-1344: cut release 0.6.0, breaking

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1340, UX-1341 | **Found by:** Ruslan, "let's issue a new release" (2026-10-07) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_a_release_records_a_contract_state.py

## Motivation

The newest release is 0.5.0 (2026-09-29, closed-row marker 1083). The
`Unreleased` row holds `analyze/v7` (`UX-1247`) and the `variant-cost`
command (`UX-1327`); a bumped contract makes the cut `breaking`, MINOR
pre-1.0. Gates, read on `3e3657a7`:

- **Review**: review 37 carries marker 1264, at or after 1083.
- **Walk**: [`walk-seed-5.md`](../../audits/walk-seed-5.md) on `3e3657a7`,
  dated 2026-10-07, the candidate's own date; no blocking finding.
- **Main**: `test (3.9)` red on every push since `057bc920` (`UX-1340`).

## Required Fix

Release guide §"Cutting one": `Unreleased` renamed `0.6.0`, `breaking`;
0.5.0 frozen with its digest; the body from `bga release-notes`; the
version in `bga/__init__.py` and `pyproject.toml`. The tag `v0.6.0` is
Ruslan's, on this commit after merge.

## Out of Scope

The rows that go into 0.6.0 are their own.

## Acceptance Test

`tests/unit/test_a_release_records_a_contract_state.py` passes with 0.6.0
as the newest row and derives `breaking` from the 0.5.0 to 0.6.0 pair,
apart from the tag clauses, which wait for `v0.6.0`.

## Outcome (round 172, 2026-10-07) — 🟢 Done

**Gap measured.** On `3e3657a7`: newest versioned row `0.5.0`, 1083,
`extending`, with `Unreleased` above it, kind `breaking`;
`derive(_states()['0.5.0'], _states()['Unreleased'])` -> `breaking`
(`analyze/v7` added, `analyze/v6` superseded; command `variant-cost` added).

**Close measured.** `CHANGELOG.md`: `Unreleased` renamed `0.6.0`,
`breaking`, 2026-10-07, closed rows 1280; `0.5.0` frozen with
`digest: 6157b7b8d5e4` (`state_digest(_states()['0.5.0'])`); body from
`bga release-notes --from 1083 --to 1280`, 197 rows; `bga/__init__.py`
and `pyproject.toml` at `0.6.0`, `test_a_shadowed_checkout_warns_at_startup.py`
with them. `requirements.lock` does not move.

walk: [`walk-seed-5.md`](../../audits/walk-seed-5.md) on `3e3657a7`, 2 match and 1 partial of 3, no blocking finding; `UX-1341` closed before the cut, `UX-1342` carried in the head. The `TestEveryVersionedReleaseIsTagged` clauses red until `v0.6.0` is tagged on this commit (Ruslan's, release guide step 8).

Mutation: none - the cut writes no guard; `test_the_increment_matches_the_kind` already reddens on a wrong kind.
