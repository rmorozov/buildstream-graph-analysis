# UX-431: the arrow count reports zero losses, having dropped 3,481 of 3,500

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, an outside walk of `bga snapshot` → `bga view` → Perfetto — a field report that the graph shape could not be resolved in the trace | **Serves:** anyone opening the timeline to see why an element started when it did | **Topic:** contracts

## Motivation

The dependency graph reaches the trace as Perfetto flows, one per
element→element edge. Measured on a 1,202-element run:

```text
edges in run/graph.json      3,500
flows emitted                   19
flows_dropped                    0
```

3,481 edges reached no arrow, and the counter that exists to report
loss read **zero**.

`_plane1_flows` (`tools/bga_timeline.py:716-768`) has two skip paths and
counts one of them:

```python
if source is None or sink is None:
    continue                    # <- not counted
if source["ts"] >= sink["ts"]:
    dropped += 1                # <- counted
    continue
```

The uncounted path is the one that fires in practice. It means "one end
of this edge produced no task in this run" — a cached element, or one
built earlier. That is not an edge case; **it is what most edges of an
incremental build are**, which is the build people actually profile.

So the reader opens the timeline, finds almost no arrows, and is told
in the same breath that nothing was dropped. A zero meaning "nothing
was lost" and a zero meaning "this counter does not watch that door"
are indistinguishable, and the second is worse than no counter at all:
it converts an absence the reader might have questioned into an
assurance.

**The count is also never shown.** `flows_dropped` is in the render
result and asserted in `tests/unit/test_the_arrows_say_why_now.py`, but
`describe()` does not print it and nothing under `bga/viewer/` reads
it — so even the reason that *is* counted reaches no reader.

Two neighbours found while measuring this, both feeding the same field
report:

- **`graph-levels` returns no rows without `analyze.json`.** `depth`,
  `on_critical_path` and `downstream_count` are read from the analysis
  beside the snapshot and silently omitted when it is absent. No
  fixture in this repository has an `analyze.json` (`find tests/fixtures
  -name analyze.json` finds nothing), so the query is exercised by
  nothing at any level.
- **`on_critical_path` was still absent with `analyze.json` present**,
  because it is read from `element_join`, which was empty for that run.

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
bga gen-synthetic /tmp/scale --seed 1
bga timeline /tmp/snapshot -o /tmp/two.pftrace
```

The result accounts for every edge in `graph.json`: emitted plus each
named reason for loss sums to the edge count. A mutation that turns the
counted skip into an uncounted one must redden the guard — as must a
capture where most edges vanish and the totals still balance to zero
loss, which is today's behaviour.

## Outcome

_Not started._
