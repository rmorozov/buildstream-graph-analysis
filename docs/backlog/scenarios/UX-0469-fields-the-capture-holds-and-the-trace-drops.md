# UX-469: the resource a task held reaches no Perfetto carrier

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-466` measured it; nothing blocks the fix | **Found by:** round 72, `tools/dev_trace_coverage.py` over a generated two-plane capture | **Serves:** the reader who opens the trace to ask which tasks were waiting on DOWNLOAD and cannot filter for them | **Topic:** contracts

## Motivation

`UX-466`'s census reads a capture's own JSON and the bytes
`bga timeline` writes. Over a generated build with both a FETCH and a
BUILD queue:

```text
Plane 1: 4 reached, 6 dropped, 56 unassessable
    DROPPED   trace.spans[].primary_resource  (0/2 value(s) in the trace)
    DROPPED   trace.spans[].resources[]       (0/2 value(s) in the trace)
    DROPPED   graph.elements[].cache_key      (0/9 value(s) in the trace)
    DROPPED   run-context.pipeline_overhead[].phase (0/4 value(s))
```

The resource a task held — `PROCESS` or `DOWNLOAD` — is in every span
and reaches no slice, category, annotation or track. The carrier is
already there and already used for something else: slices carry
categories `bst-builder` and `bst-invocation`, so a reader can filter
by *which plane* a slice came from and not by *what it was waiting
for*, which is the question `wait-category` is the whole finding
about.

No committed capture could have shown this. `with_timeline`'s spans
carry one resource value, so the field is single-valued and the census
correctly calls it unassessable rather than dropped. It took a build
with two queues to make the question answerable, which is `UX-465`'s
argument in one line.

Two more in the same class, from the same census:

- `graph.elements[].cache_key` — a reader looking at a slice cannot
  tell which artifact it produced.
- Plane 2's static census *binary* lists (`static_executables`,
  `own_static`, `staged_by_dependencies`) — every per-element key
  arrives, no list of program names does.

## Required Fix

For each of the four, decide and record: a carrier, or a declared
reason it has none. `UX-466`'s census is the check — a field that gets
a carrier moves from `DROPPED` to `reached` in its output, and a field
that gets a reason moves into the tool's own declared list beside
`build-failed`'s.

Not "add everything": a trace with an annotation per field is a trace
nobody can read, and `UX-360`'s volume budget applies to the trace as
much as to the page. The resource is the one with a reader waiting for
it; the other three may well be declined.

## Out of Scope

- `trace.spans[].task_key`, which the census reports dropped because
  the trace **decomposes** it — the uid is the slice name and the rest
  is elsewhere. That is correct behaviour and `UX-466`'s docstring
  declares it.
- The third instrument `UX-470` asks for: this row is about fields the
  capture *holds*, not about fields the planes could hold and do not.
- Changing what any plane records — every field here is one the
  capture already holds, so the whole question is which carrier
  it should arrive in. A plane that could record more and does
  not is `UX-470`.

## Acceptance Test

```bash
python3 tools/dev_trace_coverage.py <a capture with two queues>
```

with `trace.spans[].primary_resource` and `trace.spans[].resources[]`
either under `reached` or named in the tool's declared list, and the
Perfetto query library gaining the question the new carrier answers.
