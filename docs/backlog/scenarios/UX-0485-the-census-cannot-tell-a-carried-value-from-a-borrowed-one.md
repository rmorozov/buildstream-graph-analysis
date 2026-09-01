# UX-485: the trace census cannot tell a field that arrived from one whose values another field brought

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-466` built the census; `UX-469` walked into the limit | **Found by:** round 73, closing `UX-469` | **Serves:** the round that reads a `reached` verdict and believes a field has a carrier of its own | **Topic:** contracts

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

## Outcome

_Not started._
