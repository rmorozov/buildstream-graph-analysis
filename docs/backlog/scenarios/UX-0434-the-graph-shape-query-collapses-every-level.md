# UX-434: the graph-shape query collapses every level into one row

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, running the question library against a real capture of `examples/06-macro-micro-optimization` | **Serves:** anyone opening the timeline to see the shape of their dependency graph | **Topic:** viewer

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

## Outcome

_Not started._
