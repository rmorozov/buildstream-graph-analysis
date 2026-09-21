# UX-907: an artifact's weight has no cheap source, so R2 cannot rank on it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-896 | **Found by:** `UX-896`, which measured the gap its own Decomposition asked about and closed the host-level half without it | **Serves:** R2 (which element's artifacts are the expensive ones), R5 (how much of an agent's cache one project needs) | **Topic:** capture | **Area:** tools | **Shape:** judgement

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
