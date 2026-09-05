# UX-210: questions that know which plane they are asking

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-204 (the library these live in) | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The question library (`bga/viewer/questions.js`) is the round-23
review's "good, mostly presentation work" — and the review did not
read the SQL. Four of the six queries are written as if the trace
had one track, and `bga timeline`'s whole point is that it does
not: the merged output puts Plane 1's element spans and Plane 2's
`native: <element>` process lanes into the same `slice` table.

- **`element-time`** (`group by name` over all of `slice`): on a
  two-plane trace "the time per element" is polluted by every
  Plane 2 command name; the top-25 the reader is told to trust can
  be dominated by commands, not elements.
- **`stalls`** (`lead(ts) over (order by s.ts)` with no track
  filter): the gap after an element span is measured to the next
  slice *on any track* — thousands of interleaved native slices
  zero out exactly the element-track gaps the question promises to
  find.
- **`sandbox-tax`** (containment by time only, `c.ts >= p.ts and
  c.ts + c.dur <= p.ts + p.dur`, no track constraint): any slice
  that nests *in time* is subtracted — including other elements
  building in parallel on other tracks. The "unaccounted" figure
  is wrong even on a Plane-1-only trace the moment two elements
  overlap, and every slice, commands included, appears as an
  "element" in the output.
- **`dependency-wait`** matches `{element}` by name across all
  tracks, so a command that shares the name shape joins the answer.

These answer wrongly precisely on the trace shape the tool is
proudest of — both planes in one timeline — and they answer
*confidently*: a top-25 table with plausible numbers, nothing
flagging that the frame is mixed.

## Required Fix

Every query is track-scoped: element-plane questions join `track`
and exclude `native:%` lanes (or select them, for Plane 2
questions) explicitly; the containment join in `sandbox-tax`
constrains child slices to the element's own lane; `stalls`
windows over the element track only. Each `why` says which plane
it reads. A static guard over `QUESTIONS` asserts every entry
references track scoping, so a future question cannot ship
unscoped; one manual run against a real two-plane capture is
recorded in the log.

## Out of Scope

- New questions, or a query runner in the page.
- Changing how `bga timeline` names tracks (the queries adapt to
  the published naming, not the reverse).

## Acceptance Test

The static guard reddens when any query loses its track scoping
(mutation: strip the track join from `stalls` → red; from
`sandbox-tax`'s containment → red). On the recorded two-plane run,
`element-time` returns only element spans (no command names in the
top 25) and `stalls` returns element-track gaps rather than
micro-gaps to interleaved native slices — both checked against the
same numbers in the published report.

## Outcome

All six queries are plane-scoped, and the trace turned out to be
structured better than the fix assumed — so the scoping is cleaner than
the prescription, and one of the filing's premises was wrong in a way
that made the shipped `process-storm` query worse than described.

**What the merged trace actually looks like** (measured, `examples/06`,
871 events):

| `slice.category` | count | what it is |
| --- | --- | --- |
| `bst-builder` | 11 | Plane 1 element spans |
| `native-process` | 663 | Plane 2 processes |
| `bst-invocation` | 1 | the build itself |

**Two things this changed.** First, `category` is a published, semantic
scoping channel — "which plane is this slice from" is exactly what it
answers — so every query constrains it rather than joining `track` and
filtering by name. Second, and the filing did not catch this: `native:`
is a **process** name, emitted as `process_name` metadata for pids
2..10, and those processes carry **no `thread_name` at all**. The
existing `where t.name like 'native:%'` was therefore matching a
*process* name against the `track` table — so `process-storm` was not
merely polluted, it was very probably returning **nothing**, an empty
table reading as "no process storm". The Required Fix's own
prescription ("join `track` and exclude `native:%` lanes") would have
inherited that mistake.

**The join key is `args.element`, which both planes carry** — verified
on real slices from each (`{"action": "build", "element":
"toolchain.bst"}` and `{"element": "core.bst", "real_pid": 2}`). So an
element's processes are found by the uid the report prints, not by
parsing a span's display name (`toolchain.bst [macro-micro…/f81ed53b-
build…log]`) or by reconstructing a lane name.

Each `why` now names its plane, and `plane` is a declared field so the
guard can check the declaration against the SQL rather than inferring
it.

Tests: 6 new guards. Five mutations, each red — including **both**
halves of the acceptance's named `sandbox-tax` case, which needed a
second guard: stripping the containment scoping leaves `'bst-builder'`
elsewhere in the query, so the coarse "does this mention category"
check stayed green while the answer went wrong. Containment by time
alone subtracts any slice that happens to nest, including another
element building in parallel — wrong on every real build. One round-22
guard was updated rather than deleted: it pinned the old
`native:<uid>` form, and its property (the uid is substituted, the
example does not leak) is asserted against the new form.

**Deviation from the Required Fix:** the "one manual run against a real
two-plane capture" is **not** recorded, because
`trace_processor_shell` is not installed in this environment and
bundling Perfetto is out of scope by `UX-194`'s own decision. What was
done instead: the trace's structure was measured directly (the table
above, plus the process/thread layout and the args on both planes), the
queries are checked to parse by `sqlite3.complete_statement`, and the
existing `trace_processor`-marked test now exercises these six queries
where the binary exists. The SQL *semantics* are therefore argued from
the trace's measured shape rather than from an executed query, and this
paragraph exists so nobody reads "done" as "run".
