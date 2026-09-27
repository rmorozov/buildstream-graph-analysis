# UX-1062: a bundle exports anonymized, and refuses a leftover name

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1060, UX-1061 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), sections 1, 6 and 7 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

A capture of a private project cannot leave the company today: every
member names elements, paths and the host.

## Required Fix

`bga/bundle.py` gains an anonymized export: the structured members
transformed by their `disclosure` class, hashes re-keyed, time shifted
to epoch 0, secrets dropped, `plane2.log.gz`, `build.log` and
`capture-context.txt` dropped; a dictionary pass over every string
(longest match first, normalized variants, word boundaries); a residue
scan that refuses the export when any original token of four or more
characters remains; a one-screen review before writing.

## Out of Scope

Raw logs (UX-1066); public names (UX-1065).

## Acceptance Test

`tests/unit/test_an_anonymized_bundle_carries_no_original_name.py` on
the golden fixtures: no element uid, hostname or source path survives
anywhere in the archive, and the bundle loads. Mutation: plant a uid in
a finding's prose past the dictionary pass, and the residue scan
refuses.

## Outcome
