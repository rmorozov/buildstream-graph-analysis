# UX-186: comparing comparable — the host manifest

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-78 (the refusal grammar), UX-151 (the fingerprint precedent), UX-92 (which measured how much host noise matters)

## Motivation

Field feedback: *"generally we can compare builds only built on
current host — maybe we need some kind of sbom capture with
information to enable comparison of runs from different build hosts,
to compare comparable."* The tool's own history agrees twice over:
UX-92 measured 33% spread across nominally identical CI runners, and
`run-context.json` today records only `host_cpu_count` and
`host_memory_mb` — two numbers that call a laptop and a runner with
the same core count the same machine. Compare performs **no host
check at all**: a baseline captured on machine A gates a candidate
from machine B with no caveat, and the UX-78 refusal grammar — built
for exactly this class of not-a-measurement — never fires.

## Required Fix

1. **A host manifest in every capture** (the SBOM-shaped half,
   scoped): CPU model and count, memory, kernel release, distro id,
   and the toolchain the capture used — `bst`, `buildbox-run`/`bwrap`,
   `cc` versions (the UX-151 fingerprint already collects most of the
   toolchain; this joins it into `run-context.json` under one
   `host` key with a schema version). Cheap, offline, no new
   dependencies — `/proc/cpuinfo`, `os.uname`, `/etc/os-release`, and
   the version calls the fingerprint already makes.
2. **Compare classifies the pair**: same host (manifest equal on the
   fields that move durations — CPU model, count, memory) → today's
   behavior; different host → the comparison renders with a
   **cross-host caveat naming the differing fields**, the confidence
   is capped below "high", and the `--fail-on-*` gates refuse with
   exit 6 unless `--allow-cross-host` is passed (CI farms with
   uniform runners opt in once, deliberately). Missing manifest (old
   runs) → "host unknown", caveat only — old captures stay usable.
3. **`bga baseline` warns at assembly time** when the set mixes
   hosts, because a band built across machines answers a question
   nobody asked (UX-92's spread *is* this).

## Out of Scope

- Normalizing durations across hosts (a model; refusal and honesty
  first — the UX-129 lesson).
- Full SBOM of the built artifacts (this manifests the *measuring
  machine*, not the build's contents).

## Acceptance Test

A capture on this container records the manifest (fields asserted
present and plausible); two synthetic runs differing only in CPU model
compare with the caveat naming it, capped confidence, and gate exit 6
without the flag / today's exit with it; a manifest-less old run says
"host unknown" and still compares; `bga baseline` over mixed-host refs
prints the warning. The docs-commands test covers the new sentences in
`ci-comment.md` (the journey this most affects).
