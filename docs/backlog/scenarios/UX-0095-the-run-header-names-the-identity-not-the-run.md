# UX-95: the report's `Run:` header names the identity, not the run

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-07 (done)

## Motivation

`bga analyze` and `bga compare` label runs with the run-identity hash —
which is *deliberately* stable across captures of the same project,
targets and graph, because its job is comparability (UX-07). But it is
the only identifier the reports print, so two different fdsdk captures
— taken 100 minutes apart, 3434s vs 3406s, different workflow runs —
both display `Run: f12a845e2327de7a…` (observed on the round-11 per-run
refs). In a directory of accumulated baseline captures, or a CI comment
trail, the one printed identifier cannot tell any two same-config runs
apart, which is precisely the situation the UX-81 baseline history now
creates routinely.

The instance-level facts exist in every run directory (`run-context`'s
capture timestamp; in CI, the workflow run id is even in the ref name)
— they are just not surfaced next to the identity.

## Required Fix

Print both, labeled for what they are: keep the identity hash (it says
"these are comparable"), add a run-instance line (capture start
timestamp from run-context, plus the log/source path or CI run id when
known) in `analyze`'s header and in `compare`'s Baseline/Candidate
lines. JSON gains the same fields additively.

## Out of Scope

- Changing the identity hash's definition or any comparability logic.

## Acceptance Test

`bga compare` over two same-config fdsdk captures from the per-run
refs shows identical identity hashes *and* two distinct, human-readable
instance lines (timestamps differing by the real 100 minutes). Golden
tests updated; JSON adds fields without renaming existing ones.
