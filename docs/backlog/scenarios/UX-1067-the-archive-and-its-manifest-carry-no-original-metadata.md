# UX-1067: the archive and its manifest carry no original metadata

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1061 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 6.9; the owner's review on #298, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

## Motivation

`bga/bundle.py`'s `export()` calls `tarfile.add()` on source files, so
each header carries the original mtime, uid, gid, user and group name;
`bundle.json` carries the snapshot's `stamp` and `packed_at`; and the
default file name is `<stamp>.bga-bundle.tar.gz`. Anonymizing the
contents leaves all of that behind.

## Required Fix

The anonymized path in `bga/bundle.py` builds every `TarInfo` explicitly
(mtime 0, uid and gid 0, empty `uname` and `gname`, normalized mode),
writes a manifest with the stamp pseudonymized and `packed_at` dropped,
names the file without the stamp, and hands the decoded final archive,
headers and manifest included, to the residue scan before publishing.

## Out of Scope

The plain `bga bundle --export`, which keeps its headers.

## Acceptance Test

`tests/unit/test_an_anonymized_archive_carries_no_original_metadata.py`
packs a fixture owned by a named user and reads every header and the
manifest back: no original mtime, id, name or stamp. Mutation: switch
one member back to `archive.add()`, and it reds on that member's header.

## Outcome
