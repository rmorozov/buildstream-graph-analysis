# UX-309: the arrows that answer "why did this start now"

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-298 (the emitter), UX-308 (the vocabulary beside it) | **Serves:** R1, R3 | **Topic:** capture

## Motivation

The dependency question is the one a timeline is *for* — an element
ends, another begins, and whether that adjacency is causation is
exactly what `graph.json` knows and the trace does not say.
Perfetto has the vocabulary: **flows** connect slices across
tracks and the UI draws them as arrows. Two relations bga already
holds qualify:

- **Plane 1:** the dependency edge — a flow from the end of a
  dependency's task slice to the start of its dependent's. On the
  critical path this is the spine of the build made visible; the
  wait-gap questions (`stalls`, `dependency-wait` in the library)
  become something the reader can *see* before they query.
- **Plane 2:** the exec chain — `exec_chain`/`ppid` link a parent
  exec to its child; a flow makes a build system's process tree
  followable instead of inferred from lane adjacency.

## Required Fix

Flow support in the emitter (field numbers from the protos, the
UX-298 procedure); the timeline emits dependency flows for
Plane 1 — bounded and argued: all edges at synthetic scale is a
measured decision, not a default; at minimum every critical-path
edge and the direct edges of path elements — and exec-chain flows
for Plane 2 within each element's lane. One flow id per relation,
stable per trace. The bound and its measurement (packet and byte
cost per thousand edges) are recorded in the log.

## Out of Scope

- Cross-element Plane 2 flows (no captured relation exists between
  one element's process and another's — a flow must never invent
  causation).
- Any new UI — the arrows are Perfetto's.

## Acceptance Test

On the golden capture with a known chain: `trace_processor`'s flow
table contains exactly the emitted relations (count and endpoints
asserted against `graph.json` for the sampled edges); the
critical-path chain is fully connected end to end; no flow
connects two elements Plane 2 cannot relate; digest stable; the
cost measurement is in the log with the chosen bound.
