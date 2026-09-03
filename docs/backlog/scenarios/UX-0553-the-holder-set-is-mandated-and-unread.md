# UX-553: the resource-holder set is spec-mandated and reaches no reader

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-541` (the measurement that found it) | **Found by:** `UX-541`, answering its own reader question | **Serves:** anyone who has to price a spec clause | **Topic:** contracts

## Motivation

Spec Part 8.2 requires `blocking_tasks` — the time-weighted set of
tasks holding the resource — for every resource-wait interval, and
`_build_holder_info` produces it. Nothing reads it.

```text
grep -rn blocking_tasks bga/     -> bga/attribution/blame_chain.py only (its own producer)
bga/validation/invariants.py:327 -> reads 'ambiguous', not the set
bga/schemas.py                   -> no contract carries it
```

Emptying the field leaves the published document **byte-identical** at
1,202 / 2,402 / 4,002 elements — measured in `UX-541`'s Outcome — and
costs 7.8% of `analyze` at 4,002 to compute.

This is `UX-243`'s shape (a published quantity with no consumer) with
one difference that makes it harder: the field is not bga's own
invention, it is ground truth asking for it. So the question is not
"delete it" but "who was Part 8.2 written for, and does that reader
exist yet".

## Required Fix

Decide, and write the decision down rather than leaving it implicit:

- if the holder set has an intended reader that has not been built —
  the "which tasks were holding the resource" question a page could
  answer — name it and file that, and the cost stops being waste;
- if it has none, it is a spec clause bga satisfies for nobody. Say so
  here. Editing Part 8.2 is out of scope for this row; naming the gap
  is not.

## Out of Scope

- Editing `docs/spec/specification.md` — ground truth, and Part 8.2 is
  outside the Part 32 registry this repository may touch.
- Re-doing `UX-541`'s cut, which is already taken.

## Acceptance Test

The decision written above, with the reader named or its absence
stated, and — if a reader is named — a row filed for it.

## Outcome (round 81, 2026-09-03) — 🟢 Done

**Premise:** falsified — the reader exists (`UX-469`); it reads the trace, not this field.

**The reader exists. It reads the trace, not this field.**

### What the search found

The question Part 8.2 anticipates — *which tasks were holding the
resource I was waiting on* — is already asked and already answered, by
`UX-469`, through a different path:

```text
bga/viewer/questions.js:228   id: "resource-queues"
  "Which scheduler queue was the build waiting in?"
  returns resource · tasks · elements · seconds · window_seconds
tools/bga_timeline.py:205     debug.resource, per task slice
tools/bga_timeline.py:1106    where it is written
```

`UX-469`'s own comment states the gap it closed in exactly the terms
this row was filed in: `attribution`'s `resource_wait_us` "is one
number over the whole build … so that figure says a queue was full
without saying which. The trace carries `debug.resource` now; this is
the question it was added for."

So the reader was built. It just reads Plane 1's trace, where it
already is, rather than a field the analysis document does not carry.

### What that leaves

Two different granularities, and only the coarse one has a consumer:

```text
who asks                          what answers it            granularity
"which queue was full"            resource-queues (live)     per queue
"which tasks held it"             blocking_tasks (nothing)   per task, time-weighted
```

The finer question is answerable from the same trace — every task
slice carries its `debug.resource` on a timeline the reader can query
over the wait window — so `blocking_tasks` is a second computation of
something the trace already holds, in a document that does not publish
it. `UX-541` measured what that costs: at most **7.8%** of `analyze`
at 4,002 elements, and the published document is byte-identical
without it.

### The decision

**It is a spec clause bga satisfies for nobody, and no row is filed to
build a reader for it.** Not because the question is uninteresting —
it is the one `UX-469` was filed for — but because the path that
serves it is the trace, and adding a second path would put the same
answer in two places, which is what `UX-535` had to undo this round
one layer up.

What would change this: a reader who needs the holder set *without*
the trace — a `--planes 1` capture, or the CI comment, neither of
which can run a Perfetto query. Neither asks today. If one does, the
field is already computed and the row to file is "publish it", not
"compute it".

### No guard, and why

**0 mutations red.** This row produces no code and no guard. Its whole
deliverable is the decision above, and there is nothing to falsify: a
guard asserting "`blocking_tasks` has no reader" would freeze the
absence rather than the claim, and would have to be deleted by the
first round that adds one. `UX-541`'s bound guard already holds the
part that matters — that the map is built once per gap rather than per
segment.

### Deviation from the Required Fix

None. The fix named two branches and required the decision be written
rather than left implicit; the second branch is the measured one.
