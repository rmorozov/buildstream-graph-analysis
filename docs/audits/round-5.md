# Audit round 5

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping. Rounds 7-10 were always separate files; rounds 2-6 had accumulated inside the design doc, which made it an argument about direction *and* a changelog. The text below is unedited apart from heading levels.

## What the fifth round found (2026-08-17)

The round pointed `bga` at a **real, well-maintained BuildStream project**
for the first time - `freedesktop-sdk`, 1089 elements - rather than a
purpose-built example. Deliberately in baby steps: shallow clone, `bst
show` a small closure, no attempt to build the distribution.

### What worked immediately

Real graph ingestion. `tools/bst_show_to_graph.py` handled
`components/zlib.bst`'s full closure without complaint: **85 elements,
502 dependencies, 9 distinct element kinds**. The graph-only signals then
read sensibly on it - 5 choke points out of 85 (`UX-43`'s definition
holding up on real structure), max depth 27, 7 stack-consolidation
candidates, and a parallelism profile of min 1.0x / avg 2.7x / max 15.0x.

### `UX-52`: a real project's dependency types broke the structural plane

The cross-check sweep disagreed on its first real graph. `runtime`-only
edges - which do not gate build scheduling - were being counted as
gating by the structural plane, inflating its critical path from 28
elements to 32 and skewing every graph-shape signal derived from it,
including the improvement ranking.

The rule was already written down, in detail, in
`build_element_graph`'s own docstring, and two of its three callers
applied it. This is the same shape as `UX-41`.

**Why four previous rounds could not find it:** the real subgraph has 27
runtime edges among 502. *Every fixture in this repository had zero* -
the hand-written examples use `type: build` throughout, and the synthetic
1202-element generator emitted `"build"` unconditionally. Scale did not
help, because the generator was written by the same hand as the analyzer
and reproduced only the dependency type the analyzer already handled.

That is the round's real lesson, and it is sharper than round 3's
fixture-shape one:

> **A fixture written alongside the analyzer tends to contain only the
> cases the analyzer already handles.** Real projects are not just bigger
> or messier - they are *differently shaped*, in ways the author of a
> fixture has no reason to invent.

Both gaps are now closed: the scale generator emits a realistic minority
of runtime edges, and six new tests give the suite a runtime edge for the
first time.

### What a real project could not give us here, and why

Building `freedesktop-sdk` is **blocked in this environment** by network
policy, not by anything about `bga`: the bootstrap needs a 238MB binary
seed from `cdn.registry.gitlab-static.net`, and the agent proxy answers
403 to CONNECT for that host. Chasing it would have been exactly the
"forever building an OS" this round was scoped to avoid.

So round 5's findings are all graph-only, and are labelled as such - no
timing claim in this round rests on the synthetic trace that was paired
with the real graph to get it through the pipeline. What remains untested
against a real project: attribution, floors, occupancy, both efficiency
signals, and the whole of Plane 2.
