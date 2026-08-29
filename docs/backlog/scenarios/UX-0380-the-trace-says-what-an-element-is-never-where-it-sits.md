# UX-380: the trace says what an element is, never where it sits

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-308 (a slice that says what bga knows about it), UX-312 (the trace dictionary) | **Serves:** anyone in Perfetto asking which level a slice belongs to | **Topic:** viewer

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

## Outcome

Done. A Plane 1 slice now carries `depth`, `on_critical_path` and
`downstream_count`, and the run slice carries the second factor of
`UX-116`'s question beside `builders`.

**Read, not recomputed.** `element_structure(snapshot)` reads
`analyze.json` - `elements.unweighted_depth`,
`elements.downstream_count`, `element_join[].on_critical_path` - and
the emitter copies what it finds. There is no depth recurrence in
`bga_timeline.py`, which is what keeps the timeline and the report from
disagreeing about one element.

**Absent, not defaulted.** `_plane1_annotations` filters on
`is not None`, so `depth: 0` (the root) and `on_critical_path: False`
(off the path) both survive, and an element the analysis never saw gets
none of the three rather than a zero that would put it at the graph's
root. The same rule covers a snapshot with no analysis beside it: the
keys are simply absent.

**A recorded deviation.** The Required Fix's third bullet asks for
`max_jobs` at the run level. The key is named `native_max_jobs`, not
`max_jobs`, because run-context/v9's own `max_jobs` field *means*
`builders` (`tools/_run_context_common.py`'s docstring says so) - the
two would sit side by side on the run slice saying the same thing under
different names. `native_max_jobs_source` rides with it, since `UX-377`
gave the number three tiers and `UX-357`'s rule is that a published
number names the rule that produced it.

## Verification Log

**Before and after, on `examples/06`'s real 826-slice capture** with an
`analyze.json` written beside it and the `native_max_jobs` that `UX-377`
now resolves. Decoded with the in-repo protobuf reader
(`tests/unit/test_the_slice_says_what_bga_knows.decode`):

```text
                                   before (6625f32)   after (this tree)
Plane 1 slices carrying depth              0 / 12            11 / 12
              on_critical_path             0 / 12            11 / 12
              downstream_count             0 / 12            11 / 12
distinct depths in the trace                 none    0,1,2,3,4,5,6,7,8,9
run slice concurrency keys            {builders}   {builders,
                                                    native_max_jobs,
                                                    native_max_jobs_source}
```

The one Plane 1 slice without the three is `bst build all.bst` - the
invocation-wide task, which has no element. All eleven element tasks
carry all three, and the ten distinct depths are the graph's own levels.

**What it costs**, same capture, same command:

```text
              before      after     delta
gzipped     52,636 B   52,818 B    +182 B   (+0.22 B/slice)
raw        316,553 B  316,939 B    +386 B   (+0.47 B/slice)
```

Three integers on twelve slices and two values on one, with the key
strings interned once - which is the shape `UX-308` built the
annotation table for.

**Mutation sweep**, ten mutations against the committed tree, each run
against `test_the_slice_knows_where_it_sits.py` and
`test_the_slice_says_what_bga_knows.py`:

```text
M1  element_structure returns {}                          CAUGHT (3 failed)
M2  emitter filters on truthiness, not `is not None`       CAUGHT (2 failed)
M3  a missing element defaults to depth 0                  CAUGHT (2 failed)
M4  on_critical_path read from the wrong block             CAUGHT (2 failed)
M5  reads elements.depth, not unweighted_depth             CAUGHT (3 failed)
M6  a partial analysis yields nothing                      CAUGHT (1 failed)
M7  the call site stops passing the structure              CAUGHT (1 failed)
M8  the dictionary loses the depth row                     CAUGHT (1 failed)
M9  graph-levels drops its bst-builder scope               CAUGHT (1 failed)
M10 the annotation list loses on_critical_path             CAUGHT (3 failed)
```

M2 and M3 are the two the Falsification section names in the other
direction: writing a key for an element nobody analysed, and losing the
two falsy answers that are real answers.

**The library**, `bga/viewer/questions.js`: one new `graph-levels`
question grouping on `debug.depth`, scoped
`where s.category glob '*bst-builder*'` - `UX-368`'s rule that a key
nothing asks about is a key nobody finds, and `UX-308`'s that a query
which does not name its plane returns zero rows in silence. Held by
`test_the_questions_ask_what_the_trace_answers.py`, which reads the
library by running it under node.

**The dictionary and the emitter are equal in both directions** -
`test_it_documents_nothing_the_emitter_does_not_write` and its
neighbour - so the five new rows and the five new contract entries
cannot drift apart.
