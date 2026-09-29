# UX-1123: the verification log re-grounds at round 151's merge

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1120 | **Found by:** round 151 | **Serves:** whoever reads `architecture.md`'s Verification Log next | **Topic:** contracts | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** test_the_verification_log_is_true.py

## Motivation

`UX-1120` moved the closed index from `closed.md` to `closed/` and
edited `architecture.md`'s prose to say so; `f1e95129` is not reachable
from `1142839`, the commit the `UX-1103` entry credits, so the merged
tree's `make test` failed one test out of the whole suite.

## Required Fix

`docs/design/architecture.md`'s Verification Log gains one entry
credited to `UX-1123`, re-grounded at round 151's merged tree.

## Out of Scope

`UX-1120`'s own Outcome.

## Acceptance Test

`tests/unit/test_the_verification_log_is_true.py` passes on the merged
tree.

## Outcome

Gap measured: `test_nothing_landed_after_the_commit_the_entry_credits`
failed, "credits UX-1103 (1142839); 1 substantive commit(s) have
changed architecture.md since" (`make test`, rc 2, 9m56s).

Close measured: one entry, dated 2026-09-29, credited to `UX-1123`:
`analyze/v6` **63 top-level properties** (`bga analyze --schema`),
**26 emitted ids**; `python3 -m pytest $(grep -ln "architecture.md"
tests/unit/*.py) -q`: 404 passed.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| the new entry credits `UX-1120` (anchor `f1e95129`) | `test_the_verification_log_is_true.py` | 1 failed / 31 |

Deviation: crediting `UX-1120` itself fails, since its oldest commit
predates the entry; the entry needs its own row, as `UX-1103` did.
