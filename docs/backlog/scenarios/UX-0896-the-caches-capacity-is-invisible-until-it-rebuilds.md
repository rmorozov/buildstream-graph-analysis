# UX-896: the cache's capacity is invisible until it rebuilds

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-92 (the cache report card) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — a field case where the local cache could not hold the project's artifacts, so reaching for one triggered a rebuild | **Serves:** R5 (how large an agent's cache has to be), R2 (which element's artifacts are the expensive ones) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

`bga` reads the cache's *behaviour* — `bga/cache_effectiveness.py`
computes the hit ratio, the transfer share and the churn, and
`bga cache-trend` reads that as a series. It does not read the cache's
*capacity*, anywhere:

```text
$ grep -rln "artifact_size\|cache_quota\|cas_size\|disk_free" bga tools
(no matches)
```

So a build whose cache is too small looks like a build with poor cache
behaviour, and the advice that follows — "your keys are volatile" — is
wrong for a project whose keys are fine and whose disk is not. The field
case is the common one: an agent that holds most of a project's
artifacts evicts the rest, and the next build rebuilds them. Nothing in
the report can tell that apart from a cache-key problem, and the number
that would settle it — what this project's artifacts weigh against what
the agent's cache is configured to hold — is one BuildStream already
knows.

## Required Fix

Carry three facts across the ingest seam
([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md),
section 4) rather than teaching the analyzer about CAS:

| fact | where it comes from |
|---|---|
| per-element artifact size | BuildStream's own artifact metadata at extraction time |
| the configured quota | the project's or the user's BuildStream configuration |
| free space on the cache's filesystem at capture time | the host manifest, beside the fields `host/v2` already carries |

Absent means absent, never `0` — the repository's standing rule for a
fact a capture did not record. Then one finding for R5: what this
project's artifact set weighs, what the agent holds, and whether the two
imply eviction. Where the run also shows rebuilt elements that were
cached in a previous run of the same store, say so — that pair is the
evidence eviction happened rather than a key moving.

## Decomposition

surfaces: `tools/bst_extract_run.py` (the artifact facts), `bga/hostinfo.py` (free space, a `host/v2` additive key), `bga/cache_effectiveness.py` (the finding), the run-context and host contracts in `docs/spec/specification.md` Part 32
guards: a fixture whose artifact sizes exceed a declared quota and one where they do not; a third where the quota is unknown and every key is absent
gap: which BuildStream version exposes artifact sizes cheaply, and whether reading them costs a second pipeline pass — measure before choosing the source
track: bounded once the source of the sizes is settled; the settling is judgement
gate: with `UX-897`, which crosses the same extraction surface

## Out of Scope

Eviction policy advice, remote cache economics, and anything about what
storage costs in money — that is R8's axis and needs its own argument.
Changing how BuildStream is configured.

## Acceptance Test

On a fixture whose declared quota is smaller than its artifact set, the
report names the shortfall in bytes and the elements that make it up; on
one whose quota is larger, it says nothing. On a capture with no quota
recorded, every new key is absent and no finding fires. Mutations:
halve the quota (the finding appears), drop one element's size (the
total falls and the element list loses a row), set the quota absent (the
finding disappears rather than reading zero).

## Outcome (round 131, 2026-09-20) — 🟢 Done

**Premise:** held — nothing in `bga` read the cache's capacity, and the
field case rebuilt for want of disk while every signal named keys.

### The gap, measured

```text
$ git grep -lE "artifact_size|cache_quota|cas_size|quota_bytes|disk_free" main -- bga tools
(no matches)
```

A capture recorded what the cache *did* and never what it was allowed
to hold, so eviction and a moving key produced the same rebuild and only
the second had a name.

### After

`tools/bst_extract_run.py` records `cache_capacity` at extraction (the
`cache:` block of BuildStream's own user configuration, and
`shutil.disk_usage` on the cachedir); `--cache-usage` adds a walk of
`<cachedir>/cas`. `compute_cache_capacity` derives the ceiling, and
`cache-capacity` (R5) is the finding. On the committed capture that now
carries a full cache:

```text
$ python3 -m bga.cli analyze tests/fixtures/a_build_that_pulls/run
  Cache hit ratio: 75% (3 cached, 1 rebuilt) - the cache did most of the work
  25% of wall-clock was artifact transfer (download 3.0s) - ...
  The cache holds 62.0G of a 64G quota (97%, 2.0G from it) - past the 80%
  low watermark, so BuildStream is evicting, and an element that rebuilt
  here may have had its artifact removed rather than its cache key moved
```

### The gap the Decomposition asked to measure, measured

Which BuildStream version exposes artifact sizes cheaply, and whether
reading them costs a second pipeline pass. Read against BuildStream
2.8.0's own source (`pypi buildstream-2.8.0.tar.gz`):

| candidate | what it actually yields |
|---|---|
| `bst show --format %{artifact-cas-digest}` | `hash/size_bytes` of the **root `Directory` proto**, `_frontend/widget.py:462` calling `_casbaseddirectory.py:546` — the serialized listing, hundreds of bytes, not the artifact |
| `bst artifact list-contents --long` | every file, stat by stat (`widget.py:987`), deduplicated by nothing |
| the `Artifact` proto | digests only; no total (`_protos/.../artifact.proto`) |
| `GetLocalDiskUsage` on `buildbox-casd` | exact, host-level, needs casd running — and its display is the TTY status bar only (`_frontend/status.py:405`), never the log |

So there is **no cheap exact per-element artifact weight** in 2.8.0, and
the one key that looks like one is a proxy for something else. The
host-level fork ships here; the per-element fork is `UX-907`.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | absent quota read as `0` | 2 clauses |
| A2 | `at_low_watermark` always `True` | 2 clauses |
| A3 | CAS walk counts a hardlinked blob per link | 1 clause |
| A4 | budget-exceeded walk returns its partial sum | 1 clause |
| A5 | quota-over-volume ignores `reserved-disk-space` | 1 clause |

### Deviation from the Required Fix

Per-element artifact size is not carried, and the finding names the
shortfall in bytes without the elements that make it up: 2.8.0 has no
cheap exact source (table above), and `%{artifact-cas-digest}`'s
`size_bytes` is the wrong number under the right name. `UX-907` carries
it. The retention pair the Required Fix asks for is already computed by
`compute_cache_churn` (`rebuilt_in_both_*`) and is unchanged here; what
this row adds is the capacity fact that lets a reader choose eviction
from the three causes that line already lists.
