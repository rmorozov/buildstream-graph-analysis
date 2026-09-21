# UX-907: an artifact's weight has no cheap source, so R2 cannot rank on it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-896 | **Found by:** `UX-896`, which measured the gap its own Decomposition asked about and closed the host-level half without it | **Serves:** R2 (which element's artifacts are the expensive ones), R5 (how much of an agent's cache one project needs) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

`UX-896` carries the cache's ceiling and what the volume under it can
give, so an evicting agent is no longer a cache-key problem. It does not
carry what a *single element's* artifact weighs, and that is the other
half Ruslan asked for: both resource forks, host-level and per-element.

The reason is measured rather than assumed. Against BuildStream 2.8.0's
own source:

| candidate | what it actually yields |
|---|---|
| `bst show --format %{artifact-cas-digest}` | `hash/size_bytes` of the root `Directory` proto (`_frontend/widget.py:462` → `_casbaseddirectory.py:546`) — the serialized listing, not the artifact |
| `bst artifact list-contents --long` | every file, stat by stat; no deduplication across elements |
| the `Artifact` proto | digests only, no total |
| `GetLocalDiskUsage` on `buildbox-casd` | exact but host-level, and displayed only on the TTY status bar |

The trap is the first row: it is free, it is in the same `bst show` the
extractor already runs, and its number is wrong by three orders of
magnitude under a name that reads right. Fixing guide §5.

## Required Fix

Decide, with a number behind the decision, which of these the tool
takes:

1. **Walk the CAS per element** from the artifact ref's root digest.
   Exact and deduplicated if the walk shares a seen-set across elements.
   Cost unmeasured; measure it on a real cache before choosing.
2. **Ask BuildStream for it** — a `size_bytes` on the `Artifact` proto,
   or a `%{artifact-size}` format key, upstream. Cheapest at capture
   time and the longest lead time.
3. **Publish nothing per element** and say so in the report, so a reader
   asking "which artifacts are big" gets a refusal rather than the
   proxy.

## Decomposition

surfaces: `bga/cache_capacity.py` (the reader), `tools/bst_extract_run.py` (the extraction pass), the `capacity` block in `bga/schemas.py`
guards: `test_the_cache_has_a_ceiling.py::test_the_capacity_block_claims_no_artifact_weight` is the current guard and has to move when this lands — it exists so the proxy cannot arrive quietly
gap: the per-element walk's cost on a real cache, which needs one of Ruslan's agents
track: judgement until option 1's cost is measured
gate: on its own

## Out of Scope

Remote cache economics and what storage costs in money (R8's axis).
Anything about the cache's *behaviour*, which `UX-92` already owns.

## Acceptance Test

Whichever option wins, the report never publishes a number that is not
the artifact's weight under a name that says it is. If option 3 wins,
the refusal is a published sentence and a guard reads it.

## Outcome

**Option 1, and the filed pricing was wrong about why.** The walk costs
one blob read per *directory*, not per file - a `FileNode` already
carries its blob's `size_bytes` (`cascache.py:586` does exactly this
walk), so nothing is stat-ed and no `bst` runs. The same correction
retires this row's own third line: `bst artifact list-contents --long`
does not stat either (`_casbaseddirectory.py:232` reads the proto
index), so its defect is the missing deduplication and the text
output, not the syscalls.

**The gap, closed.** The row said measuring option 1 needed one of
Ruslan's agents. It did not: `pip install buildstream==2.8.0` brings
`buildbox-casd` in the wheel, so a real CAS was built here.
8 artifacts, 1,838 directories, 957 MB, page cache dropped between
reps:

```text
$ sync && echo 3 > /proc/sys/vm/drop_caches && python3 -c '...weigh_elements...'
rep0:   251.7ms  1838 dirs  136.9us/dir      # cold
rep1:    66.6ms  1838 dirs   36.3us/dir      # warm
rep2:    64.8ms  1838 dirs   35.2us/dir
```

For comparison, `cache_capacity.cas_size_bytes` - the whole-cache walk
this repository already ships opt-in - is 157.7ms cold / 46.4ms warm on
the same cache. Per-element costs ~1.6x a reading already judged
affordable, so it lands behind its own flag on the same terms.

**The proxy, measured rather than asserted.** `%{artifact-cas-digest}`
on the same 8 artifacts:

| element | proxy | walked | ratio |
|---|---|---|---|
| usr-share-doc | 56,406 | 9,290,658 | 165x |
| usr-include | 16,819 | 44,069,278 | 2,620x |
| usr-lib-python3.11 | 17,402 | 53,977,496 | 3,102x |
| usr-lib-x86_64-linux-gnu | 76,881 | 743,172,001 | 9,667x |
| usr-local-lib | 252 | 16,745,955 | 66,452x |
| usr-share-perl | 97 | 18,814,508 | 193,964x |
| usr-lib-gcc | 90 | 26,663,364 | 296,260x |
| usr-lib-python3 | 88 | 46,699,979 | 530,682x |

Not monotonic: the proxy ranks the 9 MB artifact first and the 26 MB
one last. R2 asks for a ranking, so the error is not a scale factor.

**Exactness.** Against an independent filesystem sum of the same tree
(unique file contents by sha256, symlinks excluded), delta **0 bytes**:
53,849,542 both ways, plus 127,954 of `Directory` protos the walk also
counts.

**Mutations.** 12 applied to the walk, the block and the sentence; 12
redden `test_an_artifact_has_a_weight.py`. The first attempt at "count
file nodes, not distinct blobs" was a no-op (`setdefault` to `[]=` on
the same key) and survived - the mutation was wrong, not the guard;
keying each node uniquely reddens 5.

**Deviations from the Decomposition.** The reader is a new module,
`bga/artifact_weight.py`, not `bga/cache_capacity.py`: ~150 lines of
protobuf wire reading beside host-level disk arithmetic is two modules
in one, and that module's docstring already says the per-element half
is elsewhere. `test_the_capacity_block_claims_no_artifact_weight` was
narrowed rather than moved - the proxy must still never land among
host-level numbers - and renamed `..._still_claims_...`.

One defect fell out of the fixture rather than the feature:
`dev_close_task.py --move` crashed on a `UnicodeDecodeError`, because
`working_diff()` decoded `git diff HEAD` strictly and this is the
tree's first binary fixture. Decoded with `errors="replace"` now - the
only reader is a grep for figures.

**Not closed.** No committed capture produces `artifact-weight`: the
block is walked from the capture host's own cache, and every fixture
predates the flag, so it is a declared row in `dev_finding_coverage`
rather than a covered one. `tests/fixtures/cas_artifact` is a real
BuildStream CAS and guards the walk, but it is not a capture. The
scaling to a 1,202-element run is arithmetic on 137us/dir, not a
reading: nothing here measured a real project's directory count.
`UX-919` was filed along the way - `main` was red at `70765b09` on an
unfiled flake excursion, which blocked this row's push gate.
