# UX-1066: raw logs travel tokenized

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 7 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

Stage one drops `plane2.log.gz`, `build.log` and `capture-context.txt`.
Not to be scheduled until a real diagnosis needs a raw log.

## Required Fix

`bga/anonymize.py` tokenizes the three raw members: allowlisted
`argv[0]` basenames, flag names and public macro names kept;
path and identifier values, private macros and private tool names
pseudonymized; the residue scan covers them.

## Out of Scope

Keeping a log verbatim.

## Acceptance Test

`tests/unit/test_a_raw_log_travels_tokenized.py` on the `with_timeline`
fixture: the timeline renders from the anonymized bundle and no original
token remains. Mutation: skip tokenizing `cmd=`, and the scan refuses.

## Outcome
