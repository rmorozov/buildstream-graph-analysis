# UX-309: the arrows that answer "why did this start now"

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-298 (the emitter), UX-308 (the vocabulary beside it) | **Serves:** R1, R3 | **Topic:** capture

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

## Progress (2026-08-26)

🟢 **Done.**

**The field numbers, and the trap in them.** `flow_ids = 47` and
`terminating_flow_ids = 48`, read from `track_event.proto` - which was
fetched again and came back byte-identical to what `UX-298` pinned.
Both are `repeated **fixed64**`, eight raw bytes, and they replaced
deprecated *varint* fields at 36 and 42. A varint written into field 47
is a packet a reader drops without complaining, so the guard's decoder
asserts the wire type and not only the value.

**What is drawn, and what deliberately is not.** One flow per
dependency edge in `run/graph.json` whose two endpoints both produced a
Plane 1 task, and one per `ppid` link inside a sandbox. Nothing else:
pids are namespaced per sandbox, so the parent lookup is keyed on
`(invocation, element, ppid)` and never crosses two - the fixture uses
pids 2..5 in *both* sandboxes precisely so that a lookup which forgot
the invocation would connect one element's shell to another's compiler,
and the clause that catches it is written down.

**The one way this could say something false.** A flow is one id on two
slices, and upstream infers the direction from their timestamps - "the
earliest event with the same flow ID becomes the source". The ids ride
the **begin** events, so it is the begins that decide, and an edge whose
source does not begin strictly before its sink would be drawn backwards
or picked at random. Those are dropped and **counted**, and the count is
in the render result. On `examples/06` it is two: `toolchain.bst` is
instantaneous and both its dependents begin in the microsecond it does.

**The bound is no bound, and the measurement is the argument.** The
same snapshot rendered by this tree and by the commit before it:

```text
                       slices    flows      packets          raw       gzipped
examples/06               825      836   2,335 = 2,335   +16,930 B    +6,425 B
synthetic, 20k procs   20,801   20,058  62,804 = 62,804  +401,988 B  +172,696 B
```

**Zero extra packets** at both scales - a flow id rides the slice packet
that already exists - and 20.0 B per flow uncompressed, 8.6 B
compressed. So a cap would not buy size. What a cap would buy is a less
crowded picture, and that is Perfetto's own UI to decide; this item's
Out of Scope says no new UI, and inventing a bound with no measurement
behind it would be exactly the kind of threshold this repository does
not add.

**Deviation, recorded.** The acceptance test asks that
`trace_processor`'s flow table be queried. There is still no
`trace_processor` in CI - `UX-298`'s open deviation, which `UX-312`
absorbs - so the flow table is reconstructed by the in-repo protobuf
reader from the two id lists, which is what the flow table is built
from. That checks the bytes; it does not check Perfetto's own
reconstruction, and the gap is written here rather than left implied.

**Falsification.** Recorded in the Verification Log with the rest of
round 43.
