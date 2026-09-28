# UX-1088: cut release 0.5.0 once the next features are in

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1078 | **Found by:** round 147, UX-1078's new `tail/v1` contract (2026-09-28) | **Serves:** R8 | **Topic:** contracts | **Area:** bga | **Shape:** judgement

## Motivation

The newest release row is 0.4.1 (2026-09-12, 813 closed rows). Since
then the tree has grown new contracts and flags. The round-147 rows
alone add `tail/v1` (UX-1078), and `--reanalyse` on `bga compare` and
`bga view` (UX-1073). Per the release guide's table, that makes the
next release `extending` (MINOR, 0.5.0). Ruslan wants more features in
before the cut (2026-09-28), so this row carries the cut, not the
round.

What the cut needs, as read on `6faf61bb` in round 147:

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
