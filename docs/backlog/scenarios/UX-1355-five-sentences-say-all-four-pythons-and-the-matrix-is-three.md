# UX-1355: five sentences say push to main runs "all four" Pythons, and the matrix is three

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 38 | **Serves:** R2 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1348` dropped 3.9 to 3.11, leaving `["3.12","3.13","3.14"]` on push
(`.github/workflows/ci.yml:105`). Five sentences written under `UX-995`
still say push to main runs "all four": `CLAUDE.md:16`,
`docs/contributing/fixing-guide.md:144` and `:673`,
`.claude/skills/decompose/SKILL.md:172`, `.claude/skills/verify/SKILL.md:62`.
No guard reads the number against the matrix.

## Required Fix

Say "all three" in the five sentences, or derive the count from the
`ci.yml` matrix line. File a guard row if the count is not derived.

## Out of Scope

`pyproject.toml:191` `target-version = "py39"`, which `UX-1348` dated
as deferred. The `all four` in `CLAUDE.md:17`, which counts push-check's gates.

## Acceptance Test

`git grep -n "all four" -- CLAUDE.md .claude docs/contributing` names
no Python count, and the number matches `ci.yml:105`.

## Outcome
