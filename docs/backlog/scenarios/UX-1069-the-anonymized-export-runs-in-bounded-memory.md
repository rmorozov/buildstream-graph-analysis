# UX-1069: the anonymized export runs in bounded memory

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1062 | **Found by:** the owner's implementation review on #298 (2026-09-28), finding 2 | **Serves:** anyone sharing a large private capture | **Topic:** store | **Area:** bga | **Shape:** mechanical

**Guard:** test_the_anonymized_export_runs_in_bounded_memory.py

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

**Gap measured** at `ade24f32`, the acceptance test's own capture
(`_capture`: 8 elements, `binary_cost.{A}.by_cpu[]` plus host-samples
lines) exported under `tracemalloc` at N and 4N records
(`/tmp/<track>/measure.py`, run against that base's `bga/`):

```text
N=1000:  bytes 90477 -> 362292 (+271815); peak 1093878 -> 4129569 (+3035691); ratio 11.17
N=10000: bytes 906154 -> 3708306 (+2802152); peak 9712977 -> 32628761 (+22915784); ratio 8.18
legacy processes[], N=1000: peak 463115 -> 1863612 (+1400497); ratio 5.25 (refused)
```

**Close measured.** New `bga/jsonstream.py` walks a member under its
policy trie, token by token through literal keys, and decodes whole only
a value whose subtrie repeats nowhere below (a `[]` item, a `{A}` entry
is itself walked when it holds a list); an unnamed value is skipped one
child at a time. `disclosure.step(node, key, path)` is shared by
`_walk_map` and the reader. Pass 1 (`bundle._scan`) runs `disclosure.walk`
and `collect` per record; `_Anonymizer.times` is a running minimum per
clock. Pass 2 (`bundle._stream`) writes `json.dumps`'s bytes record by
record into 0600 files in `mkdtemp(dir=dirname(abspath(destination)))`;
`_pack` builds the tar.gz there from file handles, removing each member
file once packed; `residue()` reads it back through `gzip.open` + `r|`
in `RESIDUE_CHUNK` (1 MiB) blocks, the longest variant plus one carried;
`os.replace` publishes after approval, a `finally` removes the scratch
directory. Same script, this branch, default chunks:

```text
N=1000:  peak 1419324 -> 1546725 (+127401); ratio 0.47   (1 MiB residue block not yet full at N)
N=10000: peak 2234794 -> 3843040 (+1608246); ratio 0.57  (the same fill, 0.9 -> 3.7 MB)
N=40000: bytes 3708306 -> 14823952 (+11115646); peak 4001869 -> 4335931 (+334062); ratio 0.03
chunks 4 KiB, N=1000: peak 362792 -> 383864 (+21072); ratio 0.08; legacy -1120, ratio -0.00
```

The bound is one record plus the distinct identifiers' map, originals
and residue index, not a fixed byte figure: about 4 MB *here*, at
`ELEMENTS = 8` and the 1 MiB residue block (as bytes, text and its
lowercase) - UX-1087 measures identifiers scaling separately at
~1300 B/identifier. The guard shrinks both chunks to 4 KiB so N
stays in the unit tier. **The published archive is now mode 0600**
(`os.open(..., 0o600)` then `os.replace`), where it was the umask's.
**Disk:** every rewritten member exists uncompressed before packing,
then goes as it is packed: 4N=160000 records, capture 14823952 B,
members 14680830 B (largest 7411028 B), archive 1061939 B - about the
transformed capture once over plus the archive, 14x the output here.

Byte identity: the 14 fixture captures `test_an_anonymized_bundle_trips_on_a_leftover_name.py`
walks, exported by base and branch (`/tmp/<track>/compare.py`): 14 of
14 archive sha256 equal.
`pytest tests/unit/test_the_anonymized_export_runs_in_bounded_memory.py`
plus the four named files: `61 passed in 4.77s`.

**Mutations**, each on a copy-backed file (`/tmp/<track>/mutate.py`,
`PYTHONDONTWRITEBYTECODE=1`), restored from the copy, 18 green after:

| mutation | reddened | count |
|---|---|---|
| `_fill` reads the handle whole (`json.loads(handle.read())`) | (1) both | 2 failed, 16 passed |
| `_repeats` -> False: each document decoded whole | (1) both | 2 failed, 16 passed |
| `times` kept as a list, `min()` at rewrite | (1) by_cpu | 1 failed, 17 passed |
| `_skip` decodes an unnamed value whole | (1)/(2) legacy_processes | 1 failed, 17 passed |
| archive write delayed past approval (corrected at close: packing in memory alone reddens nothing) | (3) the timing test only | 1 failed, 17 passed |
| any decode accepted where it ends | (4) plane2, run-context at chunk 1 and 7 | 4 failed, 14 passed |
| `residue()` reads a member whole | (1) by_cpu | 1 failed, 17 passed |
| `residue()` through `tarfile` `r\|gz` | (1) by_cpu | 1 failed, 17 passed |
| the Decision's wait-only-at-the-buffer's-end rule | (4) plane2 at chunk 1 and 7 | 2 failed, 16 passed |

The Decision's accept rule is not enough: `raw_decode` of `1.` or `1e`
stops before the buffer's end, so a decode now waits unless the next
character is a delimiter (whitespace, `,:]}`) or the handle is spent.
`tarfile`'s own `r|gz` inflates a whole 10 KiB compressed block at once,
growing with compressibility: 512435 -> 576272 B for the N and 4N archives
against 119972 -> 122867 through `gzip.open`.

**State at close:** the published archive is mode 0600; scratch disk is
about the uncompressed members plus the archive; concurrent exports to
one path are last-`os.replace`-wins, as the spec states.
