# UX-1086: the archive publishes before the map is saved

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 3 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`export_anonymized()` runs `os.replace(archive, destination)` before
`pmap.save()`, and `pmap.save()` truncates the existing map in place
(`O_TRUNC`), not atomically. A failure or interruption between the two
can leave a published bundle with no resolvable names and a corrupted
map for earlier bundles at once.

## Required Fix

Reorder and harden the publish in `bga/bundle.py`: write the updated
pseudonym map to a temporary file beside the real map, `fsync` it,
`chmod 0600`, and `os.replace` it onto the map path - all before the
archive's own `os.replace` onto the destination. A map with extra,
unused entries left over from an aborted export is recoverable and is
accepted.

## Out of Scope

The residue scan's matching (UX-1085); the numeric-credential default
(UX-1084).

## Acceptance Test

`tests/unit/test_the_pseudonym_map_saves_before_the_archive_publishes.py`:
an injected failure during the map write leaves both the destination
path and the prior map's contents untouched, and no archive is
published; a normal export publishes the map (temp file, 0600) then
the archive, in that order. Mutation: swap the two `os.replace` calls
back to archive-then-map, and the injected-failure case leaves a
published archive with a corrupt map.

## Outcome
