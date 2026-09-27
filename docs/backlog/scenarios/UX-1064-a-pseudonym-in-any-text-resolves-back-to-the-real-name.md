# UX-1064: a pseudonym in any text resolves back to the real name

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1061 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 4 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** cli | **Area:** bga | **Shape:** mechanical

## Motivation

The owner asked to understand which internal elements a reader means
"without hand assignment".

## Required Fix

A resolve subcommand in `bga/cli.py` rewrites every pseudonym in stdin
or a file (a reply, a `.bst` patch) back to its original and lists
pseudonym-shaped tokens it cannot map. The viewer takes the map to
render real names locally. A map whose fingerprint differs from the
bundle's is refused.

## Out of Scope

Anything sent off the owner's machine.

## Acceptance Test

`tests/unit/test_a_pseudonym_resolves_back.py`: resolve(anon(text)) ==
text on the golden fixtures' uids; an unknown token is listed; a foreign
map is refused. Mutation: skip the fingerprint check, and the foreign
map resolves to wrong names.

## Outcome
