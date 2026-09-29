# UX-1100: cut release 0.5.0 once the next features are in

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1078 | **Found by:** round 150, UX-1078's new `tail/v1` contract (2026-09-28) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** test_a_release_records_a_contract_state.py

## Motivation

The newest release row is 0.4.1 (2026-09-12, 813 closed rows). Since
then the tree has grown new contracts and flags. The round-147 rows
alone add `tail/v1` (UX-1078), and `--reanalyse` on `bga compare` and
`bga view` (UX-1073). Per the release guide's table, that makes the
next release `extending` (MINOR, 0.5.0). Ruslan wants more features in
before the cut (2026-09-28), so this row carries the cut, not the
round.

What the cut needs, as read on `6faf61bb` in round 150:

- **The walk gate is not met** (guide step 1). The newest walk report
  is `walk-seed-3.md`, 2026-09-12. A walk dated on or after the
  candidate commit must run first, in its own session. No guard reads
  this for the real row.
- **The review gate is met.** Review 28 carries marker 982, which is at
  or after 0.4.1's 813.
- **0.4.1 gains a `digest:` line** (step 3, `UX-550`). That is the
  freeze, not an edit to its state.
- **The body is generated.** In that tree, `bga release-notes --from 813`
  gave 185 closed rows, markers 813 to 998. Regenerate it at the cut.
- The state block lists `contracts:` and `commands:` only. Flags such
  as `--reanalyse` belong in the head's prose, not the block.

## Required Fix

Following `docs/contributing/release-guide.md` §"Cutting one", rename
`CHANGELOG.md`'s `Unreleased` row (UX-1078 adds it; Ruslan's call,
2026-09-28) to 0.5.0 `extending`. Give it its generated body, freeze
0.4.1 with its digest, and bump `bga/__init__.py` and `pyproject.toml`
together. The tag `v0.5.0` is Ruslan's, at merge.

## Out of Scope

The features that go into 0.5.0 are their own rows.

## Acceptance Test

`tests/unit/test_a_release_records_a_contract_state.py` passes with
0.5.0 as the newest row, and derives `extending` from the 0.4.1 to
0.5.0 pair. The walk report is linked from the Outcome.

## Outcome

**Gap measured.** `PYTHONPATH=. python3 -m bga.cli release-notes --from 813`
on the release commit, after `UX-1135` closed: `270 scenarios closed (closed-row markers 813 → 1083)`
(round 150's 185 rows to 998 grew with the tree). Newest row before the
cut: `0.4.1`, 813, `patch`, with `Unreleased` above it.

**Close measured.** `CHANGELOG.md`: `Unreleased` renamed `0.5.0`,
`extending`, 2026-09-29, closed rows 1083; `0.4.1` frozen with
`digest: 32a915ff3719` (`state_digest(_states()['0.4.1'])`); body
regenerated for `813→1083`; `bga/__init__.py` and `pyproject.toml` at
`0.5.0`; `test_a_shadowed_checkout_warns_at_startup.py` pins the
version string, moved with it. `requirements.lock` does not move (its
`0.4.1` is `dill`).

Version-derived kind, `derive(_states()['0.4.1'], _states()['0.5.0'])`:
`extending` (adds `junction-cost/v1`, `tail/v1`, command `junction-cost`).

Guard run, `python3 -m pytest -n 2 -q`, the two release guards plus
seven others that read `CHANGELOG.md`, the version or the guide: 3
failed, 54 passed on the two release guards; the three failures are the
`TestEveryVersionedReleaseIsTagged` clauses that need `v0.5.0`, red
until Ruslan's tag, not written here. Every other clause is green,
including `test_the_increment_matches_the_kind`. The selector names 718
files on this diff (the version moves the tree), so it was not run whole.

walk: [`walk-seed-4.md`](../../audits/walk-seed-4.md) on `74aa14f2`, 2 match and 1 partial of 3; its one blocking finding filed and closed as `UX-1135` before the cut. The three `TestEveryVersionedReleaseIsTagged` clauses red until `v0.5.0` is tagged on this commit (Ruslan's, release guide step 8).
