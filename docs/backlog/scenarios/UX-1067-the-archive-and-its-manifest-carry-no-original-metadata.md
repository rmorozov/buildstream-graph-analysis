# UX-1067: the archive and its manifest carry no original metadata

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1061 | **Found by:** the 2026-09-27 brainstorm with the owner ([`anonymized-bundle.md`](../../design/anonymized-bundle.md)), section 6.9; the owner's review on #298, finding 2 | **Serves:** anyone sharing a private capture with an outside reader | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** test_an_anonymized_archive_carries_no_original_metadata.py

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

**Gap measured:** `bundle.export()` calls `archive.add()` per member, so
each header carries the source's real mtime/uid/gid/uname/gname; the
manifest keeps `stamp` and `packed_at`; the default name is
`<stamp>.bga-bundle.tar.gz` - none of the six facts are neutral.

**Close measured:** added `bundle.neutral_tarinfo`,
`bundle.anonymized_manifest`, `bundle.anonymized_output` and
`bundle.export_anonymized` (metadata only; member content untouched,
`UX-1062`'s job). The verifier also found `gzip.GzipFile(..., mtime=0)`
still stamping the *output path's* basename into the gzip header's
FNAME, unguarded by any tar-level fix; closed with `filename=""`.
`pytest tests/unit/test_an_anonymized_archive_carries_no_original_metadata.py -q`:
`3 passed in 0.75s` - every header's mtime/uid/gid/uname/gname is neutral,
the manifest's `stamp` differs from the real one and carries no
`packed_at`, the output name carries no stamp, and the gzip header
itself carries neither a name nor a non-zero mtime.

The manifest's `stamp` is pseudonymized in class `"directory"`: it is
the name of `.bga/runs/<stamp>/`, the same class every other directory
segment in a `.bst` path gets (`bga/anonymize.py`'s `CLASS_PREFIXES`),
not a new class of its own.

**Mutation table:**

| Mutation | Reddened | Count |
|---|---|---|
| One member's `neutral_tarinfo`+`addfile` swapped for `archive.add()` | `test_the_anonymized_archive_and_manifest_carry_no_original_metadata`: `info.mtime == 0` fails (`1700000000 == 0`) | 1 failed, 1 passed |
| Dropped `filename=""` from `gzip.GzipFile(...)` | `test_the_gzip_header_carries_no_file_name`: `not flags & _FNAME_BIT` fails (`8 & 8`) | 1 failed, 2 passed |

Both reverted from a copy saved before mutating, not `git checkout --`,
since the mutation and this task's uncommitted work share the file.
