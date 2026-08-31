# UX-434: the graph-shape query collapses every level into one row

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, running the question library against a real capture of `examples/06-macro-micro-optimization` | **Serves:** anyone opening the timeline to see the shape of their dependency graph | **Topic:** viewer

## Motivation

`graph-levels` is the question that answers "what does my graph look
like, level by level". A field report said it could not be made to
resolve the graph's shape. Run against a real capture, it returns
**one row**:

```text
"depth","elements","seconds","on_path"
2,10,28.527000,0.000000
```

One level, ten elements, and nothing on the critical path — for a
project whose entire purpose is a **six-deep chain** with a critical
path through it.

The annotations are all present and correct. Read directly from the
same trace:

```text
"element","depth","downstream","oncp"
"all.bst",9,0,"true"
"app.bst",8,1,"true"
"codegen.bst",1,8,"false"
"core.bst",1,8,"true"
"lib-a.bst",2,7,"true"
"lib-b.bst",3,6,"true"
"lib-c.bst",4,5,"true"
"lib-d.bst",5,4,"true"
"lib-e.bst",6,3,"true"
"lib-f.bst",7,2,"true"
```

Nine distinct depths, the chain plainly visible, `codegen.bst`
correctly off the path. **The data is there and the query cannot see
it.** Two independent defects, both in this one query:

**1. `group by depth` binds to Perfetto's column, not to the alias.**
The `slice` table has its own `depth` — the slice's *nesting* depth —
and it shadows the `extract_arg(...) as depth` alias. Every builder
slice is at nesting depth 0:

```text
"slice_depth","n"
0,20
```

so there is exactly one group, and the `depth` column printed beside it
is whichever row SQLite happened to keep. The reported `2` is not a
level; it is an arbitrary element's depth standing for all of them.

**2. `sum(...'debug.on_critical_path')` sums strings.** The annotation
is emitted as the string `"true"`/`"false"` (`EXIT_STATUS_OK`'s
neighbour rule — Plane 1's booleans are strings in the arg table), and
`sum('true')` is `0`. The column reads zero on every capture, including
one where eight of ten elements are on the path.

Disambiguated and compared as a string, the same trace answers
correctly:

```text
"graph_depth","elements","seconds","on_path"
1,2,13.013000,2
2,1,3.004000,2
3,1,2.003000,2
4,1,2.001000,2
5,1,2.002000,2
6,1,3.005000,2
7,1,2.004000,2
8,1,1.495000,2
9,1,0.000000,1
```

**Why no guard caught it.** `test_the_questions_ask_what_the_trace_answers`
checks the *vocabulary* — every `debug.` key a question names is one the
emitter writes — and every key here is correct. The query is
well-formed, names only real annotations, and returns a row, so nothing
static can tell it is wrong. Only executing it against a capture with a
known shape can, and until `UX-432` nothing ever had.

A sweep of the other thirteen questions for the same alias/column
collision found none: `graph-levels` is the only one that groups by a
name the `slice` table also defines.

## Required Fix

- **Disambiguate the alias.** Project the annotations in a subquery and
  group by the projected name, so no `slice` column can shadow it —
  and prefer a name (`graph_depth`) that cannot collide in the first
  place.
- **Compare the boolean as the string it is**, or emit it as an integer
  and say so in `docs/spec/trace-dictionary.md`. Either is fine; both
  being true at once is what this is.
- **A guard that runs the query and asserts its shape**, against a
  fixture whose graph is known — one row per depth, and the critical
  path count matching the analysis. `UX-432` makes that one command;
  what it needs is a committed capture with an `analyze.json`, which
  `UX-431` also asks for.
- Re-check the remaining thirteen against real data as part of the same
  work — the sweep above was static, and this defect is the reason a
  static sweep is not enough.

## Out of Scope

- **The absent arrows**: `UX-431` holds the flow accounting, which is a
  different mechanism in a different file.
- **Emitting `depth` under a less collidable annotation name**: worth
  considering, but it changes the trace dictionary and every saved
  query a reader already has, so it is its own decision.
- **The `[NULL]` element row** the wrapper span puts at the top of three
  Plane 1 questions — same capture, different cause, and it needs its
  own item.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga timeline .bga/runs/<stamp> -o /tmp/six.pftrace
python tools/dev_perfetto_queries.py /tmp/six.pftrace
```

`graph-levels` returns one row per distinct depth — nine for this
project — and `on_path` is non-zero where the analysis says elements are
on the critical path. A mutation restoring `group by depth` must redden
the guard, and so must one restoring the numeric `sum`.

## Outcome (round 70, 2026-08-30) — 🟢 Done

### Both defects reproduced on a committed fixture, then closed

`tests/fixtures/with_timeline` gained an `analyze.json` in `UX-431`, so
its trace now carries the annotations. Rendered and queried with the
pinned `trace_processor_shell` v57.2 — the query **as it was**:

```console
$ trace_processor_shell -q old.sql six.pftrace
"depth","elements","seconds","on_path"
0,11,50.191000,0.000000
```

One row for a ten-level graph, and `on_path` zero on a run where ten of
eleven elements are on the path. The stored type says why:

```console
$ ... select distinct extract_arg(...,'debug.on_critical_path') v, typeof(...) t
"v","t"
"[NULL]","null"
"true","text"
"false","text"
```

And after:

```console
$ trace_processor_shell -q final.sql six.pftrace
"graph_depth","elements","seconds","on_path"
0,1,0.000000,1
1,2,26.031000,1
2,1,3.005000,1
3,1,4.004000,1
4,1,3.005000,1
5,1,4.006000,1
6,1,3.004000,1
7,1,4.004000,1
8,1,3.132000,1
9,1,0.000000,1
```

Ten rows, one per level. Level 1 holds two elements and reports one on
the path — `core.bst` on it and `codegen.bst` off it, which is what the
analysis says.

The whole library against the same trace, `tools/dev_perfetto_queries.py`:

```text
  graph-levels         Plane 1         10 row(s)
  ...
empty:  6/14  ['process-storm', 'element-commands', 'failed-processes',
               'cpu-versus-wall', 'peak-rss', 'concurrency-curve']
errors: 0/14  []
```

The six empties are the six Plane 2 questions, on a Plane 1 fixture.
That is the re-check the item's fourth bullet asks for: fourteen queries
run against real data, no errors, and every empty result explained by
the capture rather than by the query.

### What changed in the query

Both fixes, and one the guard found:

1. The annotations are projected in a **subquery** and grouped by the
   projected name, so no `slice` column can shadow the alias — and the
   name is `graph_depth`, which cannot collide in the first place.
2. `on_critical_path` is compared as the **string** it is.
3. And counted over **distinct elements**, like `elements` beside it. An
   element can produce more than one task in a run — it is why
   `_plane1_flows` has a last-ending and a first-beginning rule — and
   the first fix summed slices, which would report a level of one
   element as two. Found by mutation `G5`, which the original fixture
   could not discriminate because every element appeared once.

`docs/spec/trace-dictionary.md` now states both traps on the keys they
belong to: `depth` says `slice` has one of its own and a query must
project it first, `on_critical_path` says the value is the text `true`
or `false` and `sum()` over it is 0.

### The guard, and why it can run in CI

`tests/unit/test_the_graph_shape_query_answers.py`. The clauses that
decide **execute the shipped SQL**, read out of `bga/viewer/questions.js`
by node, against a `slice` table built in SQLite — with **its own
`depth` column**, which is the entire mechanism. SQLite is not Perfetto,
but the shadowing is plain SQL name resolution, and the old query
against that table gives exactly what the real reader gave:

```text
OLD: [(0, 4, 0.0)]     # one row, on_path 0.0, from four elements at three depths
```

Two further clauses run the same query through the **real reader** when
this machine has one, so the emulation is anchored rather than trusted.
They are skipped where `trace_processor_shell` is absent — which
includes CI — so every property they check is also checked against the
SQLite table.

The fifth clause is the sweep the item asks for, executable rather than
static: no question aliases a name the `slice` table also defines and
then groups or orders by it.

```text
G1 the whole query as it was              red: one_row_per_level, each_level_counts,
                                               critical_path_not_always_zero,
                                               no_question_groups_by_a_slice_name,
                                               real_reader_gives_one_row_per_level,
                                               real_reader_counts_the_critical_path
G2 the alias is named `depth` again       red: no_question_groups_by_a_slice_name
G3 the boolean is summed numerically      red: critical_path_not_always_zero,
                                               real_reader_counts_the_critical_path
G6 the path counts slices, not elements   red: critical_path_not_always_zero
G4 the wrapper span is not filtered out   red: one_row_per_level, each_level_counts,
                                               critical_path_not_always_zero,
                                               the_wrapper_span_is_not_a_level,
                                               real_reader_gives_one_row_per_level,
                                               real_reader_counts_the_critical_path
G5 elements counted, not distinguished    red: each_level_counts_its_own_elements
```

**Two clauses did not discriminate on the first pass**, and both are
worth the record:

- **G5** passed, because the fixture gave every element one slice, so
  `count(x)` and `count(distinct x)` agreed. `lib-a.bst` now appears
  twice at one depth. Writing that case is what exposed defect 3 above:
  the `on_path` column had the same bug and no clause could see it.
- **G2** reddened the two real-reader clauses **for the wrong reason** —
  they skipped the CSV header by matching `"graph_depth"`, so a renamed
  column made the header parse as a row. They now drop the first line by
  position. With that fixed G2 reddens only the sweep clause, which is
  the honest answer: the subquery alone closes the collision, and the
  rename is what the sweep enforces.

### What it cost, and the budget that refused it

The corrected query is longer than the broken one, and the page half of
the export met `PAGE_BUDGET_B` at **286,195 B** against 286,000.

It was landed by trimming **prose and whitespace** — two sentences of
`returns` that the trace dictionary now carries instead, and one alias
per line folded onto two — and never the query's meaning. A wrong query
that fits is worse than a right one that does not, and that is the one
growth this budget must not refuse.

```text
page (both fixtures)   285,704 -> 285,928   (+224, all UX-434)
golden total           385,968 -> 386,192   (bound 387,500)
macro_micro total      441,321 -> 441,545   (bound 443,000)
```

**72 bytes of headroom, and `PAGE_BUDGET_B` is no longer the binding
number** — `test_only_one_number_bounds_the_page` derives a second
ceiling of 286,040 from the 2.4x data ratio, 112 B above where the page
sits. The two have converged and the next source addition of any size
trips both. Not resolved here, because choosing between them is a
decision about what the page is for: **`UX-444`**, filed with these
measurements.

### Deviation from the Required Fix

None on the query. The item offered "compare as a string, **or** emit as
an integer and say so in the dictionary" — comparing was chosen, because
changing the emitted type would break every saved query a reader already
has, and the dictionary says so either way. One addition: the distinct
count, above.

### The suite

```console
$ make lint
All checks passed!

$ make test
5367 passed, 26 skipped, 1 warning in 296.62s (0:04:56)
```

### What that green run could not see (round 70, 2026-08-31)

The two clauses of `TestTheQueryAnswersARealTrace` coined their own
wording for "Perfetto's shell is not installed" instead of asking
`tests/trace_processor.py`, which `UX-321` built to be the one gate.
This machine has the binary, so the clauses **ran** and the skip census
never saw the reason. Every CI runner has no binary, so they skipped,
and the census failed all four interpreters after every test had passed:

```text
5260 passed, 144 skipped in 334.53s (0:05:34)
================================= skip census ==================================
2 test(s) skipped for a reason this suite has never declared: 'no
trace_processor_shell (tools/dev_perfetto_queries.py --fetch)'. Add it
to KNOWN_SKIP_REASONS in tests/conftest.py …
make: *** [Makefile:51: test] Error 1
```

Fixed by asking the shared gate — `trace_processor.shell()` and
`trace_processor.REASON` — which also gives these clauses the
`BGA_TRACE_PROCESSOR` override the hardcoded path did not honour. The
declared baseline moved with the measurement:

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_real_reader_agrees.py \
    tests/unit/test_the_perfetto_handoff.py \
    tests/unit/test_the_graph_shape_query_answers.py -q -rs \
  | grep -c "trace_processor_shell is not installed"
16
```

14 -> 16 in `KNOWN_SKIP_REASONS`. That the census can only check a
reason on a machine where the skip fires — the reason this was green
here and red there, and the second time this exact shape has landed
(`tests/conftest.py:116` records round 50's) — is filed as **`UX-449`**.
