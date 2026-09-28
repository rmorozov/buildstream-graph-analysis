# UX-1069: the anonymized export runs in bounded memory

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the owner's implementation review on #298 (2026-09-28), finding 2 | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** judgement

## Motivation

`_read_documents()` parses each whole JSON member, the rewrite and
`_write_documents()` hold parsed and serialized copies, `_pack()` builds
the whole compressed archive in `BytesIO`, and `residue()` opens it
again before approval. A multi-GB `plane2.json` needs many times its
size in RAM and fails before the review screen appears.

## Required Fix

Transform, pack and scan with memory bounded independently of the
capture's size: members rewritten one at a time into a private
temporary archive beside the destination (mode 0600), the residue scan
streaming over that archive, and the archive published atomically
(rename) only after approval, removed otherwise. The architect decides
how a multi-GB JSON member is rewritten without holding it whole.

## Out of Scope

A CLI switch for the export; raw logs (UX-1066).

## Acceptance Test

`tests/unit/test_the_anonymized_export_runs_in_bounded_memory.py`: a
generated capture whose `plane2.json` is large enough that whole-file
handling would exceed a stated peak (tracemalloc), exported under that
peak; a refused approval leaves no archive and no temporary file.
Mutation: read the member whole, and the peak is exceeded.

## Outcome
