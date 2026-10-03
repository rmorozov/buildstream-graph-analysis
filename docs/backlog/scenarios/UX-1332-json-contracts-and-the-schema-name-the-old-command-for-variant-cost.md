# UX-1332: `json-contracts.md` and the `junction-cost/v1` schema still name `bga junction-cost` as the emitter

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 37, checklist items 2 and 3 (2026-10-03) | **Serves:** R2 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1327` renamed the command to `variant-cost` and kept `junction-cost` as an unlisted alias; it moved `architecture.md`'s emitter column and `cli.md`, and not the contract's own prose:

```text
$ git grep -n "bga junction-cost" -- docs/guides/json-contracts.md bga/schemas.py
docs/guides/json-contracts.md:23     | `junction-cost/v1` | `bga junction-cost RUN RUN --format json` ...
docs/guides/json-contracts.md:717    `bga junction-cost` prices N separate builds of one type under
docs/guides/json-contracts.md:722    bga junction-cost RUN-x86/ RUN-arm/ --format json
bga/schemas.py:7041                  "bga junction-cost RUN RUN [RUN...] --format json",
$ bga --help | grep -c junction-cost      1     # "(was junction-cost)", the alias is not listed
```

`bga variant-cost --schema` therefore prints the old name as the emitter (`schemas.py:7041` is the published `emitted_by`), and `architecture.md:` reads `bga variant-cost --format json` for the same id.

## Required Fix

Name `bga variant-cost` in the three places, with the alias once where the section opens. The id `junction-cost/v1` does not move.

## Out of Scope

Renaming the schema id (a version bump, `rules.md`'s schema rows).

## Acceptance Test

`git grep -n "bga junction-cost" -- docs/guides/json-contracts.md bga/schemas.py` returns only the alias sentence; a guard reads every contract's `emitted_by` command against `bga --help`'s listed commands and the aliases `cli.py` registers.

## Outcome

Not yet worked.
