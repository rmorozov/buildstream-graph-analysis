# UX-896: the cache's capacity is invisible until it rebuilds

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-92 (the cache report card) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — a field case where the local cache could not hold the project's artifacts, so reaching for one triggered a rebuild | **Serves:** R5 (how large an agent's cache has to be), R2 (which element's artifacts are the expensive ones) | **Topic:** capture | **Area:** tools | **Shape:** judgement

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

## Outcome
