# UX-311: a trace that knows whose build it was

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-298, UX-308 (the annotation vocabulary) | **Serves:** R1, R4 | **Topic:** capture

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

## Progress (2026-08-26)

🟢 **Done, with one recorded deviation.**

**The identity surface.** One process track, `bga: run`, ranked first,
with one annotated instant on it: the run stamp, project identity,
targets, manifest hash, project git commit, `bga` and `bst` versions,
the host manifest's CPU model/count/memory/kernel/distro, the
scheduler's builders, the plane anchor and the offset it applied, and
the lane-order rule. One track and one instant because that is
*portable* vocabulary - `trace_processor` selects it like any other
slice and the UI shows it without knowing anything about `bga`. The
keys joined `UX-308`'s contract as a third set, and
`ANNOTATION_CONTRACT` is now the one name the guard reads, because a
guard that checks only the sets it remembers is checking nothing about
the third.

**Incompleteness is in the name, not only in an annotation.** An
annotation is something a reader has to open a slice to see; the
honesty `UX-156` enforces in the report belongs where the first scroll
lands. So an unfinished run's track reads `bga: run (interrupted)` -
and all **three** ways of being unfinished are covered, because
`UX-156`/`UX-157`/`UX-185` were joined into one accessor precisely so a
consumer could not handle one and forget the others. This is a new
consumer, so it calls that accessor rather than re-deriving the rule.

**The ordering rule that had to be read.** `sibling_order_rank` is
**ignored on a process track** unless the *root* descriptor - `uuid =
0`, a track nobody writes events to - sets `process_ordering` to
`PROCESS_ORDERING_EXPLICIT`. A rank written without that one packet is
a hint no UI reads, and nothing about the trace would look wrong. Read
from `track_descriptor.proto`, whose sha256 matched what `UX-298`
already had:

```text
track_descriptor.proto   sibling_order_rank = 12, process_ordering = 19
                         ProcessOrdering.PROCESS_ORDERING_EXPLICIT = 1
```

Ranks: 0 the identity, 1 Plane 1, 2 upward the element lanes. Lane
labels carry the element's kind - `native: core.bst (cmake)` - from the
run's own graph.

**Deviation, recorded.** The acceptance test asks for the **critical
path** lanes first. The timeline has no critical path: it reads two
logs and a graph, not an analysis, and computing one here would be a
second copy of the analyzer's own rule - the duplication `UX-273` and
`UX-301` exist to prevent. No capture in this repository publishes an
`analyze.json` beside its run either, so a read-it-if-present path
would be a code path nothing exercises. Element lanes are ordered
**heaviest-traced-first**, and the trace states which rule it used in
`lane_order` rather than leaving a reader to assume the other one. The
guard's fixture runs its spans in the reverse of its names, so a rank
that merely agreed with the alphabetical lane assignment would be
caught ordering nothing.

**Also recorded.** `trace_processor` still does not run in CI
(`UX-298`'s open deviation, `UX-312`'s first clause), so the identity
track is read back by the in-repo protobuf decoder, extended here to
the descriptor's ordering fields.

**Falsification.** Recorded in the Verification Log with the rest of
round 43.
