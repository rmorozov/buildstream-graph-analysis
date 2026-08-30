# UX-431: the arrow count reports zero losses, having drawn no arrows

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, two real captures of `examples/06` — a field report that the graph shape could not be resolved in the trace | **Serves:** anyone opening the timeline to see why an element started when it did | **Topic:** contracts

## Motivation

The dependency graph reaches the trace as Perfetto flows, one per
element→element edge. Measured on two **real** captures of
`examples/06-macro-micro-optimization` — 11 elements, 34 edges in
`run/graph.json` — taken with `bga snapshot -- bst build all.bst`:

```text
                        edges   flows   flows_dropped
mostly-cached build        34       0               0
full rebuild               34      24              24
```

Two different failures, and the first is the silent one.

**The cached build drew no arrows at all and reported no losses.** That
is the ordinary case — the build people actually profile is the one
where most elements are already built. `_plane1_flows`
(`tools/bga_timeline.py:716-768`) has two skip paths and counts one:

```python
if source is None or sink is None:
    continue                    # <- not counted
if source["ts"] >= sink["ts"]:
    dropped += 1                # <- counted
    continue
```

The uncounted path means "one end of this edge produced no task in this
run", which is exactly what a cached element is. So the reader opens
the timeline, finds no arrows, and is told in the same breath that
nothing was dropped.

A zero meaning "nothing was lost" and a zero meaning "this counter does
not watch that door" are indistinguishable, and the second is worse
than no counter: **it converts an absence the reader might have
questioned into an assurance.**

**The full rebuild exposes the second failure.** There the count works —
and says 24 of 34 edges were refused for endpoint ordering, leaving ten
arrows out of thirty-four. 71% of the graph's edges are dropped on a
successful, fully-parallel build, which is a far larger share than the
"two edges on `examples/06`" the code comment cites as the case it was
written for. Whether that is correct behaviour badly explained, or a
rule that is too strict, is the question this item has to answer — but
it cannot be answered while the number reaches no reader.

**The count is never shown.** `flows_dropped` is in the render result
and asserted in `tests/unit/test_the_arrows_say_why_now.py`, but
`describe()` does not print it and nothing under `bga/viewer/` reads
it — so even the reason that *is* counted reaches no reader.

Two neighbours found on the same captures:

- **No fixture in this repository carries an `analyze.json`**
  (`find tests/fixtures -name analyze.json` finds nothing), so `depth`,
  `on_critical_path` and `downstream_count` are absent from every
  fixture-rendered trace and the questions that group by them are
  exercised by nothing. A real `bga snapshot` **does** write one — this
  is a fixture gap, not a product one.
- `graph-levels` is separately broken in a way real data revealed, and
  is filed as `UX-434`.

## Required Fix

- **Count every reason an edge produced no arrow, separately**, and
  name them: no task at either end, and endpoints out of order.
- **Report the counts to the reader**, not only to the render result —
  the trace handoff states what it could not carry, in the place the
  arrows are missing from.
- **A fixture with an `analyze.json`**, so the three graph annotations
  and `graph-levels` are exercised by a guard rather than by a reader.
- Decide, and write down, whether an edge whose predecessor was cached
  should draw an arrow from *somewhere* — it is a real dependency the
  reader is trying to see, and "no task" is the tool's reason, not
  theirs.

## Out of Scope

- **Emitting `dependency_type` on the flow**: `graph.json` carries it
  and the trace drops it, which is a real gap and a separate item — it
  changes the trace dictionary, this one changes a count.
- **The missing edge-listing query**: nothing in the library returns
  the edge set or a path, only `waited-on-flow` for one element. Filed
  separately; this item is about the arrows that were promised and not
  drawn.
- **`element_join` being empty** for that run — analyzer behaviour, and
  it needs its own measurement before anything is claimed about it.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst      # once warm, so most elements cache
bga timeline .bga/runs/<stamp> -o /tmp/six.pftrace
```

The result accounts for every edge in `graph.json`: emitted plus each
named reason for loss sums to the edge count. A mutation that turns the
counted skip into an uncounted one must redden the guard — as must a
capture where most edges vanish and the totals still balance to zero
loss, which is today's behaviour.

## Outcome

_Not started._
