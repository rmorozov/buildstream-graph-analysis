# UX-431: the arrow count reports zero losses, having drawn no arrows

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, two real captures of `examples/06` — a field report that the graph shape could not be resolved in the trace | **Serves:** anyone opening the timeline to see why an element started when it did | **Topic:** contracts

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

## Outcome (round 70, 2026-08-30) — 🟢 Done

### What replaced the counter

`flows_dropped` — one integer, one of two reasons — is gone.
`_plane1_flows` now returns a **mapping**, and the render result carries
it as `flow_losses`:

```python
{"edges": 34, "drawn": 32, "no_task": 0, "out_of_order": 2}
```

`FLOW_LOSS_REASONS` in `tools/bga_timeline.py` holds one key per reason
**and the sentence it prints**, because the reason and its wording are
one fact. The property a guard can hold is an identity rather than a
threshold: **drawn plus every named reason equals the edge count**, on
every capture. A reason nobody counts breaks it.

### It reaches three readers, and the third is filed

```console
$ python -c "...render('tests/fixtures/with_timeline', out); print(describe(...))"
Wrote Plane 1 to .../six.pftrace.
  Plane 2 is not in it: this snapshot kept no raw trace log. ...
  13 slices, 32 flows, 0 counters on 14 tracks. Open it with Perfetto ...
  32 of 34 dependency edge(s) drawn as arrows.
    2 not drawn: the two slices do not begin in the dependency's order, so an arrow would point the wrong way.

edges in graph.json: 34
accounting: {'edges': 34, 'drawn': 32, 'no_task': 0, 'out_of_order': 2}
balances: True
```

| reader | how |
|---|---|
| `bga timeline` on a terminal | `describe()`, above |
| `bga view --export` | `run.trace_flow_losses`, drawn by `questions.js` |
| `bga view`, served | **not yet — `UX-443`** |

The served page cannot have it without undoing `UX-296`, which moved the
trace render off the startup path after a 30 GB projected read landed
between a user and the socket. `run.json` is written before anything has
parsed a build log. `flowAccounting` draws nothing when the key is
absent, so the served page is silent rather than wrong; the row is filed
and the reason is in it.

**Printed on every run that had edges**, including the run that drew them
all. A line that appears only on loss teaches a reader that its absence
means nothing was lost, which is the reading this item exists to remove.
Only the reasons that actually took an edge are named.

### The decision the item asked for

*Should an edge whose predecessor was cached draw an arrow from
somewhere?* **No.** Perfetto infers a flow's direction from the two
slices' timestamps, so an arrow needs two slices; the predecessor has
none. Every candidate source is a lie of a different kind — the
element's *previous* run is a different build, the wrapper span is not
the element, and a zero-length marker at the dependent's start is an
arrow from itself. The honest answer is the count and the sentence, which
is what this item builds. "No task" is the tool's reason and not the
reader's, so the sentence says *cached, or built earlier* rather than
naming the mechanism.

### The fixture, and the defect it found

`tests/fixtures/with_timeline/analyze.json`, produced by running `bga
analyze` on the fixture's own run and rewriting its absolute paths, the
way `tests/test_golden.py` does. It is the first fixture in this
repository with one, so `depth`, `on_critical_path` and
`downstream_count` are now exercised by a guard rather than by a reader.
Its graph is the six-deep chain `UX-434` needs: ten distinct depths,
eleven elements, `codegen.bst` off the critical path.

Building it found a second defect. `element_structure` read
`on_critical_path` from `element_join` — which is **Plane 2's** table —
so a Plane 1 capture lost the annotation from every slice while
`critical_path_detail`, in the same document, named the path. It now
falls back to that, and gives every element the analysis knows the key,
`false` included: a key present on some slices and absent from others is
a `group by` that silently drops rows, which is `UX-434`'s subject.

### The ten mutations

```text
E1  the cached skip is uncounted again    red: every_edge_is_an_arrow_or_a_named_reason,
                                               two_reasons_are_told_apart,
                                               cached_build_says_why, reader_is_told
E2  describe drops the accounting         red: reader_is_told, drew_them_all_still_says_so
E3  it speaks only on loss                red: a_run_that_drew_them_all_still_says_so
E4  every reason named, count or not      red: reader_is_told, drew_them_all_still_says_so
E5  the payload drops it                  red: the_export_is_given_the_accounting
E6  the page draws nothing                red: the_paragraph_names_the_count_and_the_reason
E7  the page names every reason           red: the_paragraph_names_the_count_and_the_reason
E8  the page draws it with no timeline    red: a_run_with_no_timeline_draws_no_accounting
E9  the critical path falls back to none  red: all_three_annotations_reach_every_element,
                                               the_critical_path_comes_from_the_analysis
E10 the path is every element             red: the_critical_path_comes_from_the_analysis
```

All ten discriminate on the first pass. E10 is the one worth naming: a
fallback that marked everything on the path would satisfy "the key is
present everywhere" and say nothing, which is why the clause asserts
`codegen.bst` is **off** it.

### What the change cost

Measured with `export` then the embedded-payload split, before and after:

```text
                      page       data      total
golden      before  284,584    100,264    384,848
            after   285,704    100,264    385,968   (+1,120, all source)
macro_micro before  284,584    155,617    440,201
            after   285,704    155,617    441,321   (+1,120, all source)
```

**All source, zero payload**, and the reason is worth recording: neither
committed export carries a timeline — neither fixture has a `build.log`
— so neither publishes `trace_flow_losses` and the new paragraph does
not render in either. The measurement is what says so; the guard that
exercises the payload runs on `with_timeline`, the only committed
fixture with one.

Both bounds restated with that split (386,000 → 387,500 and 441,000 →
443,000). `PAGE_BUDGET_B` is **not** raised: the page half now sits 296 B
under it, and the budget is `UX-360`'s judgement about what a reader
downloads rather than a high-water mark. The next source addition trips
it, which is what a budget is for.

`bga/viewer/app.js` sits exactly on `UX-337`'s 1500-line ceiling, so the
one new option shares a line with `tracePlanes`. Splitting the file is
`UX-337`'s business and not this item's; the guard is the thing saying
so, and it said so on the first run.

### Deviation from the Required Fix

Two additions, both forced by the work:

- **`element_structure`'s critical-path fallback.** The item's fixture
  clause asks for the three annotations to be exercised, and one of them
  could not be present on any Plane 1 fixture. Fixing the source was the
  smallest way to satisfy the clause honestly.
- **`UX-443`**, for the served page. Filed rather than done, because
  doing it means either rendering at startup — measured and rejected by
  `UX-296` — or a new fetch the section does not have.

`docs/design/styleguide.md` §4e is annotated: its example is this
defect, and it now says what closed and what did not.

### The suite

```console
$ make lint
All checks passed!

$ make test
5360 passed, 26 skipped, 1 warning in 273.91s (0:04:33)
```
