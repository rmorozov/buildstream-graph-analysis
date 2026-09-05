# UX-485: the trace census cannot tell a field that arrived from one whose values another field brought

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** `UX-466` built the census; `UX-469` walked into the limit | **Found by:** round 73, closing `UX-469` | **Serves:** the round that reads a `reached` verdict and believes a field has a carrier of its own | **Topic:** contracts | **Area:** tools

## Motivation

`tools/dev_trace_coverage.py` matches **values**: a field is `reached`
when a string it holds is in the emitted trace's interned vocabulary.
That is the right method — both ends are emitted artifacts and no step
reads a Python source file for the name of anything (fixing guide §5)
— and it has one blind spot, which `UX-469` walked into.

Before `UX-469`, on a two-queue capture:

```text
DROPPED   trace.spans[].primary_resource  (0/2 value(s) in the trace)
DROPPED   trace.spans[].resources[]  (0/2 value(s) in the trace)
```

`UX-469` gave `primary_resource` a debug annotation and gave
`resources[]` nothing. Both then read:

```text
reached   trace.spans[].primary_resource  (2/2 value(s) in the trace)
reached   trace.spans[].resources[]  (2/2 value(s) in the trace)
```

The second field has no carrier. Its two values are `PROCESS` and
`DOWNLOAD`, the scalar's two values, so the vocabulary check cannot
separate them. `UX-469` handled the instance by declaring
`resources[]` in `DECLINED`, which is a statement about that one field
and not a property of the instrument.

The general shape: **any field whose vocabulary is a subset of a
carried field's reads `reached` whether it arrived or not.** Two
candidates already in the tree, both currently `reached`:
`plane2.element_attribution.recognized_elements[]` and
`plane2.by_element.{}#key` hold element uids, and the uid is the Plane
1 slice name — so every element-keyed field in the Plane 2 report is
`reached` by the same coincidence, and the census's Plane 2 count is
built out of them.

## Required Fix

- **Measure how much of the current verdict is coincidence**: for each
  `reached` field on a two-queue capture, whether its matched values
  are matched by any *other* reached field. Pasted. That number says
  whether this is a footnote or a rewrite.
- **Give the verdict a second axis, or narrow the first.** The
  decoder already knows which carrier each vocabulary string arrived
  in (`decode` returns the carriers used), so `reached via
  debug-annotation` is available in a way `reached` is not — a field
  whose values arrive only as slice names is a different answer from
  one that has a key of its own.
- Whatever it becomes, `DECLINED`'s `resources[]` entry stops being
  the thing that keeps the output honest and goes back to being a
  design decision.

## Out of Scope

- The `DECLINED` list itself — `UX-469` decided those four fields and
  this row does not reopen them.
- `trace.spans[].task_key`, the composite the census reports dropped
  on purpose: that is the mirror-image limit and `UX-466`'s docstring
  already declares it.
- The finding census (`tools/dev_finding_coverage.py`), which reads
  what `analyze` emits rather than matching values and does not have
  this problem.

## Acceptance Test

```bash
python3 tools/dev_trace_coverage.py <a capture with two queues>
```

with every `reached` field distinguishing the carrier its values
arrived in, `trace.spans[].resources[]` reading as uncarried with
`DECLINED` removed from the tool, and a guard that reddens when a
field with no carrier of its own is reported as having one.

## Outcome (round 73, 2026-09-01) — 🟢 Done

### How much of the verdict was coincidence

The first Required-Fix item, measured the only way it can be: with
`DECLINED` emptied, so nothing is hidden by a declaration, on the
two-queue capture the row was filed from.

```text
python3 tools/dev_trace_coverage.py <the two-queue capture>   # DECLINED = {}

Plane 1: 4 reached, 2 shared, 4 dropped, 0 declined, 56 unassessable
    shared    trace.spans[].primary_resource  (2/2 value(s) via debug-annotation:resource; indistinguishable from trace.spans[].resources[])
    shared    trace.spans[].resources[]  (2/2 value(s) via debug-annotation:resource; indistinguishable from trace.spans[].primary_resource)

Plane 2: 4 reached, 13 shared, 4 dropped, 0 declined, 113 unassessable
    shared    plane2.binary_cost.{}#key  (6/6 value(s) via debug-annotation:anchor_element, debug-annotation:element; indistinguishable from plane2.by_element.{}#key, plane2.commands_not_observed.elements_with_gap[] and 8 more)
    shared    plane2.by_element.{}#key
    shared    plane2.commands_not_observed.elements_with_gap[]
    shared    plane2.commands_not_observed.per_element.{}#key
    shared    plane2.configure_phase.per_element.{}#key
    shared    plane2.cpu_time.per_element.{}#key
    shared    plane2.declared_vs_used.uncovered_elements[].element
    shared    plane2.element_attribution.recognized_elements[]
    shared    plane2.peak_memory.per_element.{}#key
    shared    plane2.per_element_parallelism[].element
    shared    plane2.redundant_operations[].example_cmd  (2/2 value(s) via slice-name; indistinguishable from plane2.redundant_operations[].signature)
    shared    plane2.redundant_operations[].signature
    shared    plane2.static_census.per_element.{}.unassessable_because[]
```

**13 of Plane 2's 17 `reached` verdicts were collisions** — eleven
element-uid-keyed fields that all match the uid a slice name carries,
plus the `redundant_operations` pair, where a command string is both
the signature and the example. The row asked whether this was a
footnote or a rewrite; 13 of 17 is the answer.

### After

The shipped output on the same capture, `DECLINED` back in place:

```text
python3 tools/dev_trace_coverage.py <the two-queue capture>

Plane 1: 4 reached, 1 shared, 3 dropped, 2 declined, 56 unassessable
    DROPPED   run-context.pipeline_overhead[].phase  (0/4 value(s) in the trace)
    DROPPED   run-context.producer.contracts[]  (0/21 value(s) in the trace)
    DROPPED   trace.spans[].task_key  (0/18 value(s) in the trace)
    declined  graph.elements[].cache_key
    declined  trace.spans[].resources[]
    shared    trace.spans[].primary_resource  (2/2 value(s) via debug-annotation:resource; indistinguishable from trace.spans[].resources[])
    reached   graph.dependencies[].predecessor  (8/8 value(s) via debug-annotation:anchor_element, debug-annotation:element)
    reached   graph.dependencies[].successor  (7/7 value(s) via debug-annotation:anchor_element, debug-annotation:element, debug-annotation:targets)
    reached   graph.elements[].element_kind  (3/3 value(s) via debug-annotation:element_kind)
    reached   graph.elements[].uid  (9/9 value(s) via debug-annotation:anchor_element, debug-annotation:element, debug-annotation:targets)
```

Before this round the same two lines read:

```text
    reached   trace.spans[].primary_resource  (2/2 value(s) in the trace)
    reached   trace.spans[].resources[]  (2/2 value(s) in the trace)
```

Three things changed, one per Required-Fix item:

1. **A second verdict, `shared`.** Two fields whose matched value sets
   are equal are two fields the census cannot attribute, and it now
   says so instead of crediting both.
2. **`reached` names its carrier.** `decode()` returns a map from
   value to the *sites* it arrived at, so a verdict reads `via
   debug-annotation:element_kind` rather than `in the trace`. A reader
   can check a site; `reached` on its own they cannot.
3. **`DECLINED` is a design decision again.** A declined field is still
   measured and still counts as a collision partner, so
   `trace.spans[].resources[]` reads `declined` *and*
   `primary_resource` reads `shared … indistinguishable from
   trace.spans[].resources[]`. Before, removing the declaration was
   the only thing keeping the output honest.

### The guard builds the capture it needs, and that was the second try

The first version of the end-to-end clauses read the two-queue capture
out of `/tmp`, and skipped when it was not there — which is every
machine but the one that wrote it, and this one after a reboot. The
suite's own skip census caught it, and was right to:

```text
python3 -m pytest tests/unit/test_every_skip_reason_is_declared.py -q
E   AssertionError: 56 skip reason(s) cannot be read statically, up from the 55 measured.
```

`with_timeline` cannot be used as it stands — every span in it is
`PROCESS`, and a one-valued field is excluded before any of this is
reached (`"one distinct value cannot discriminate"`). So `_two_queue`
copies that fixture and moves half its spans to `DOWNLOAD`, in both
`primary_resource` and `resources[]`, which is exactly the collision
`UX-469` walked into. The four clauses now run everywhere, and the
suite has one fewer unreadable skip reason rather than one more.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Each was
proved to have landed with a `grep -c` before the run, and reverted
from a clean copy after it.

| # | mutation | reddened |
|---|---|---|
| T1 | `indistinguishable` returns `{}` — no collision is ever reported | **3** of 23 — the pure-function clause, the two-queue clause, and the declined-partner clause |
| T2 | a declined field is skipped when `matched` is built, as it was before this round | 1 of 23 — `test_the_two_queue_capture_names_the_collision_UX_469_declared` |
| T3 | `sites_of` credits every field to every site in the vocabulary | 1 of 23 — `test_a_reached_field_says_which_carrier_brought_its_values` |
| T4 | `decode` forgets where a value arrived: one anonymous site for all | 2 of 23 — the carrier clause and `test_the_vocabulary_maps_a_value_to_where_it_arrived` |

### A guard of mine that did not discriminate

**T3 passed on its first writing.** The carrier clause asserted only
that `" via "` was in the detail string — a *shape*, which "via
everything" satisfies as happily as "via the right thing". It is the
defect CLAUDE.md names as the most-sighted in this repository, written
into the clause meant to catch it. Strengthened to assert the real
site:

```python
kinds = reached.get("graph.elements[].element_kind")
assert kinds and kinds.endswith("via debug-annotation:element_kind"), kinds
```

after which T3 reddens.

### Deviation from the Required Fix

- **`trace.spans[].resources[]` reads `shared`, not "uncarried".** The
  Acceptance Test asked for it to read as uncarried. It cannot: which
  of two colliding fields the emitter actually read is a fact about
  the emitter's *code*, and this census reads emitted artifacts on
  purpose (fixing guide §5). Answering "uncarried" would mean a text
  scan of `tools/bga_timeline.py` — the proxy §5 is about. So the
  census reports the collision and `DECLINED` carries the decision, a
  human's, with the item number that made it.
- **No committed capture produces a `shared` verdict**, because none
  has two scheduler queues — the population gap `UX-466` stage 3 already
  declared. Handled by building the shape rather than by skipping; see
  above.

### The runs

```text
python3 -m pytest tests/unit/test_the_trace_census_reads_both_ends.py -q
23 passed in 7.97s

make test-touching   23 passed in 6.06s
make test            5,688 passed, 27 skipped in 347.21s (0:05:47)
make lint            ruff + PyMarkdown, both clean
```
