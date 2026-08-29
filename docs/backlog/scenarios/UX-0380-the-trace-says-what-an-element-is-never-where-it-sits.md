# UX-380: the trace says what an element is, never where it sits

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-308 (a slice that says what bga knows about it), UX-312 (the trace dictionary) | **Serves:** anyone in Perfetto asking which level a slice belongs to | **Topic:** viewer

## Motivation

Round 60 asked whether `bga view` or Perfetto can show which elements
belong to which graph level. Half the answer is yes: the analyzer
computes it and publishes it, and the element table has the column.

```text
analyze/v4    elements.unweighted_depth   {"toolchain.bst": 0, "mod0.bst": 1, ...}
              parallelism.levels          [0, 1, 2]
              parallelism.width_at_level  [1, 10, 1]
element.js    ["elements.unweighted_depth", null, "Depth", "count"]
```

The other half is no. The trace dictionary is the complete list of what
a slice carries, and every structural fact is missing from it. What a
Plane 1 slice knows about its element:

```text
element        the uid
element_kind   cmake / import / manual / ...
task_type      build / fetch / pull / push / track
outcome        SUCCESS / FAILURE / CACHED / SKIPPED
```

and that is all. No depth, no `on_critical_path`, no
`downstream_count`, no edge to a dependency. So in Perfetto — the tool
`UX-198` put one click away precisely so a reader could ask their own
questions — every question about the *shape* of the build is
unanswerable, while every question about its timing is answerable. A
reader cannot select level 3, cannot filter to the critical path, and
cannot ask why the level-2 elements all started at the same moment,
which is the question a level decomposition exists to answer.

The run-level keys have the same hole from the other side: `builders` is
there, `max_jobs` is not (`UX-377`), so a reader cannot even see the
two factors of `UX-116`'s question in the trace that shows their effect.

The values are free. `analyze/v4` holds all of them for the same run,
keyed by the same uid the trace already writes on every slice — which is
`UX-308`'s own argument for the `element` key, applied one attribute
over.

## Required Fix

`PLANE1_ANNOTATIONS` gains the structural keys, and the trace dictionary
gains a row for each:

- `depth` — the element's `unweighted_depth`, the longest path in edges
  from a source, which is the same number the element table's `Depth`
  column shows and `parallelism.levels` decomposes by.
- `on_critical_path` and `downstream_count` — the two facts every
  finding in the report is ranked by, so a reader can select in Perfetto
  the set the report is talking about.
- `max_jobs` at the run level, beside `builders`, once `UX-377` gives it
  a value that is right.

The keys go on Plane 1 slices only, where the element is the subject.
`UX-308`'s correction applies unchanged: a Plane 2 slice does not get a
key it cannot fill, because a question filtering on an absent key
returns zero rows silently.

The query library gains one question that uses them — "what ran at each
level" — since `UX-368` established that a key nothing asks about is a
key nobody finds.

## Falsification

Export a trace and assert every Plane 1 slice carries `depth`, and that
the set of distinct depths equals `parallelism.levels` from `analyze`
on the same run. Today the key is absent, so the first assertion fails
on every slice.

The other direction, so the fix is not "annotate everything": a Plane 2
slice carries no `depth`, and the query that uses it names Plane 1 in
its `where`.

## Out of Scope

- The element table's `Depth` column. It already exists and renders the
  same number correctly, so the gap this item names is the trace and
  not the page.
- Drawing the graph in Perfetto. This is an annotation on the slices
  that are already there, not a new view.
