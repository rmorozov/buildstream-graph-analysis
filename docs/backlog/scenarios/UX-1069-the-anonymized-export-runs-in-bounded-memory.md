# UX-1069: the anonymized export runs in bounded memory

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1062 | **Found by:** the owner's implementation review on #298 (2026-09-28), finding 2 | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** mechanical

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

## Decision

Route:     a stdlib reader in new `bga/jsonstream.py` walks the policy trie through literal keys, cuts a record wherever the trie repeats (`[]` items, `{placeholder}` entries) and decodes it whole with `json.JSONDecoder.raw_decode` from a 64 KiB sliding buffer, accepting a decode that ends at the buffer's end only at EOF. Pass 1 runs `disclosure` gaps and `collect` per record, skipping an unnamed value child by child; pass 2 runs `_rewrite` per record and writes the same bytes `_write_documents` writes today, into 0600 scratch files in `mkdtemp(dir=dirname(destination))`. The tar.gz is packed there from file handles; the residue scan reads it back in 1 MiB chunks with the longest variant plus one carried over; `os.replace` publishes after approval, a `finally` removes the directory otherwise. `_Anonymizer.times` becomes a running minimum per clock.
Rejected:  ijson (not locked, a new runtime dependency); a scalar-level stdlib tokenizer (same bound, Python work per token); refusing a plane2.json over VIEW_MAX_BYTES (a readable capture refused); BytesIO or rewriting the tar header (a gzip stream cannot seek).
Files:     bga/jsonstream.py · bga/bundle.py · bga/disclosure.py (one `step(node, key, path)` shared by `_walk_map` and the reader) · tests/unit/test_the_anonymized_export_runs_in_bounded_memory.py
Guard:     (1) tracemalloc peak at N and 4N records (plane2 `binary_cost.{A}.by_cpu[]` plus host-samples lines): peak(4N) - peak(N) < 0.25 x (bytes(4N) - bytes(N)); (2) a legacy monolith whose bulk is `processes[]` refuses on "processes: not named by the policy" under the same bound; (3) at approval exactly one temporary archive beside the destination, mode 0600; after a refusal, a gap or a residue hit the directory lists as before; (4) streamed bytes equal json.dumps of the tree rewrite at chunk sizes 1, 7 and 65536.
Mutation:  json.loads(handle.read()) reddens (1); keeping the times list reddens (1); decoding an unnamed value whole reddens (2); packing into BytesIO reddens (3); accepting a decode at the buffer's end reddens (4) at chunk 7; residue() reading a member whole reddens (1).
Class:     product
Split:     one track, opus (about 300 lines of code plus 150 of test, UX-1039).

## Outcome
