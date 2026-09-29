# UX-1101: the verification log is re-grounded at a shared merge

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1073, UX-1078 | **Found by:** round 150, the integrator's merge seam | **Serves:** whoever reads `architecture.md`'s Verification Log next | **Topic:** contracts | **Area:** bga | **Shape:** mechanical

## Motivation

UX-1073's own entry credited `d101955`, a commit that does not carry
UX-1078's `tail/v1` row: the two tracks merged into the same tree
(63 top-level `analyze/v6` properties, 26 emitted ids) but each track's
own entry could see only its own commit. Neither track's verifier could
see the other's contract change, so the log undercounted at the seam.

## Required Fix

`docs/design/architecture.md`'s Verification Log gains one entry dated
at round 150's merge, covering both `UX-1073`'s `fingerprint` addition
and `UX-1078`'s `tail/v1` row together, re-grounded on the merged
commit rather than either track's own.

## Out of Scope

Re-writing either track's own closed Outcome.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py`: the newest entry's
`analyze/v6` property count and emitted-id count match `bga analyze
--schema` and the registry, read at the entry's own commit.

## Outcome

Gap measured: the log's newest entry (`UX-1073`, pre-merge) named
`d101955`, which lacks `tail/v1`; reading the merged tree's schema
against that entry's own figures disagreed with what the merge
actually shipped.

Close measured: one entry added, dated 2026-09-28, anchored on
`f813b4b4` (the merge both tracks landed in) and covering both
contract changes: `analyze/v6` **63 top-level properties**
(`bga analyze --schema`), **26 emitted ids**
(`python3 -m pytest $(grep -ln "architecture.md" tests/unit/*.py) -q`
at that commit). `test_the_verification_log_is_true.py` passes against
the new entry.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| the new entry's property count reverted to 62 | `test_the_verification_log_is_true.py` | 1 failed / 1 |

Deviation: none from the Required Fix.
