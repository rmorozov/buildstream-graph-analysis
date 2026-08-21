# UX-186: comparing comparable — the host manifest

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-78 (the refusal grammar), UX-151 (the fingerprint precedent), UX-92 (which measured how much host noise matters)

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

## What was built

**1. The manifest.** `bga/hostinfo.py` collects it - CPU model and
count, memory, kernel release, distro id, and the `bst` / `bwrap` /
`buildbox-run` / `cc` version lines. Offline apart from the four
version calls, which are the same short probes `UX-151`'s fingerprint
already makes, each with a timeout and each degrading to `None`. On this
container:

```json
{
  "schema": "host/v1",
  "cpu_model": "Intel(R) Xeon(R) Processor @ 2.80GHz",
  "cpu_count": 4,
  "memory_mb": 16075,
  "kernel_release": "6.18.44-fc-v21",
  "distro_id": "ubuntu 24.04",
  "toolchain": {"bst": "2.7.0", "bwrap": "bubblewrap 0.9.0",
                "buildbox-run": null, "cc": "cc (Ubuntu 13.3.0-...) 13.3.0"}
}
```

`cpu_model` comes from `/proc/cpuinfo`, not `platform.processor()`,
which on Linux returns `x86_64` - true of every x86 machine ever built,
and so useless for telling two of them apart. Written by both
run-context producers (`UX-18`'s shared helper), so the two cannot
diverge again.

**2. Compare classifies the pair.** `host_comparison` on the result,
`{"status": same|different|unknown, "differing": [...]}`. Verified on
real runs:

```text
$ bga compare a b
  Warning: Cross-host comparison: these runs were measured on different
  machines (CPU model: Intel(R) Xeon(R) ... vs AMD Ryzen 9 7950X). ...
exit=0

$ bga compare a b --fail-on-regression
Cross-host gate FAILED: ... (cpu_model). ... Pass --allow-cross-host ...
exit=6

$ bga compare a b --fail-on-regression --allow-cross-host
exit=0

$ bga compare old a          # `old` predates the manifest
  Warning: Host unknown: the baseline carries no host manifest ...
exit=0
```

The refusal is on the **gates**, not on the comparison: looking at a
cross-host pair is fine and gating on it is not, so the numbers still
render with the caveat attached. It sits beside `UX-54`'s failed-build
gate - before the low-confidence fail-open, and failing *closed*,
because two machines' durations are not a noisy signal but a different
measurement. Confidence is capped below `high` at the same time.

Only `cpu_model`, `cpu_count` and `memory_mb` decide the classification.
Kernel, distro and toolchain are recorded because a human reading a
refusal wants them; refusing on a `bwrap` point release would make the
check noise, and noise gets switched off.

**3. `bga baseline` warns** when a set spans machines - `HOSTS: ...` in
the text summary, `host_drift` in the JSON. A warning, not a refusal: a
band across a fleet is a real object somebody may want to look at, it is
just not the object the band's arithmetic claims to be.

Tests: 25 new (`tests/unit/test_host_manifest_and_cross_host.py`),
including the three CLI exit codes driven through a real subprocess.
Six mutations, each red - including the two over-reach directions
(classifying a missing manifest as `different`, and comparing
`kernel_release`), because this feature's failure mode is refusing too
much.

Documented in `ci-comment.md` (the journey it most affects), with a
guard pinning `--allow-cross-host`, `host_manifest`, `exit 6` and the
host-unknown sentence.

## Deviation from the Required Fix

The item asked for the manifest under a **`host`** key.
`run-context.json` has published an operator-supplied *identifier*
there since `UX-12` (`--host ci-runner-1`), and taking that key would
silently redefine a field consumers already read - the exact drift
`UX-190` is filed against. The manifest is `host_manifest`; the two
coexist, `host` names the machine and `host_manifest` describes it.
There is a guard asserting `add_host_manifest` leaves `host` alone.

