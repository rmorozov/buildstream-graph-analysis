# UX-311: a trace that knows whose build it was

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-298, UX-308 (the annotation vocabulary) | **Serves:** R1, R4 | **Topic:** capture

## Motivation

A trace file leaves the machine that made it — attached, shared,
opened weeks later next to five others. Today it carries no
identity: not which run, not which host, not whether the capture
was complete, not how the two planes were aligned. The report
refuses to present an interrupted run's numbers as measurements;
the trace, opened directly in Perfetto, has no such honesty — it
looks like any other build. And the lane order is discovery order,
so the reader's first scroll is unguided.

## Required Fix

A run-identity surface inside the trace, in portable vocabulary
(a dedicated `bga: run` track whose annotated instant carries: run
id/stamp, host class from the manifest, bga version,
`incomplete_reason` where set, the plane-alignment anchor and
offset, capture mode) — so `trace_processor` can select it and the
UI shows it first. An incomplete run's marker is prominent (the
track name itself says `interrupted`, not only an annotation).
Lane organization: element lanes carry their kind in the process
label, and the critical-path lanes order first (the descriptor's
ordering fields, proto-read) — the trace opens where the report
would send you.

## Out of Scope

- Clock-domain machinery (the anchor+offset stays the alignment
  mechanism; this states it rather than re-engineering it).
- Any cross-run linkage inside one trace (one trace, one run).

## Acceptance Test

The golden trace's identity track resolves via `trace_processor`
with values equal to `run-context.json`'s (equality asserted); an
interrupted fixture's trace names it in the track name; path
lanes precede non-path lanes in the descriptor order; two runs'
traces opened together are distinguishable by their identity
tracks alone (the sharing scenario, asserted on both goldens).
