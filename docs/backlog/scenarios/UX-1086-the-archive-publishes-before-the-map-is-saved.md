# UX-1086: the archive publishes before the map is saved

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1069 | **Found by:** the owner's #298 re-review at 156d7436, finding 3 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** test_the_pseudonym_map_saves_before_the_archive_publishes.py

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

Gap measured: `os.replace(archive, destination)` ran before `pmap.save()`,
and `save()` used `os.open(O_TRUNC)` in place - both confirmed by reading
`bga/bundle.py:760-764` and `bga/anonymize.py:114-116` at `e5075375`.

Close measured: `bga/anonymize.py` gained `_write_0600_atomic` (temp file
in the map's own directory, write+`fsync` and the `os.replace` both under
one `try`/`except` that unlinks the temp file on any failure, then
directory `fsync`); `PseudonymMap.save()` now calls it. `bga/bundle.py`
moved `pmap.save()` (with its `os.makedirs`) before the archive's
`os.replace`, inside the `try` so a map-write failure propagates and the
archive is never published; `scratch` removal still runs in `finally`.
`tests/unit/test_the_pseudonym_map_saves_before_the_archive_publishes.py`
(4 tests: order, a write-failure temp-file leak, an existing destination
left untouched, and a normal export) passes: `python3 -m pytest
tests/unit/test_the_pseudonym_map_saves_before_the_archive_publishes.py -q`
→ `4 passed in 0.53s`. `python3 tools/dev_touching.py --base e5075375` →
`48 file(s) selected (33 census + 15 naming the change) · 1951 passed, 3
skipped in 176.11s`.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| swap `os.replace` order back (archive before map) | both order tests | `2 failed in 0.46s` |
| `save()` reverted to `_write_0600` (O_TRUNC, non-atomic) | both order tests (`DID NOT RAISE`, `StopIteration`) | `2 failed in 0.51s` |
| drop the `unlink` on write/fsync failure (temp file leak) | the leak test | `1 failed in 0.76s` (stray `map.json.tmp-<pid>`) |
