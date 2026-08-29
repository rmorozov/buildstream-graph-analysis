# UX-395: `--format chrome` silently drops the flows and counters

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-298 (the timeline speaks Perfetto natively), UX-309 (the arrows that answer "why did this start now"), UX-310 (the counters), UX-312 (the canned question library) | **Serves:** anyone who took the chrome trace to Perfetto and ran a canned query | **Topic:** capture

## Motivation

`bga timeline` emits two formats. Measured on the same snapshot:

```text
                    slices   flows   counters
trackevent             826     836        538
chrome                 663       0          0
```

The chrome JSON carries slices and nothing else. Two of the fourteen
canned questions in the query library read exactly what it does not
carry — `waited-on-flow` reads the `flow` table, `concurrency-curve`
reads `counter` and `counter_track` — so against a chrome trace both
return zero rows, and the reader concludes the build had no
concurrency and that nothing waited on anything.

That is a wrong answer produced silently, which is the class `UX-107`
exists to prevent: *nobody could look* is being rendered as *looked
and found nothing*.

The command's own summary is where it should have been caught. The
trackevent path reports its flow and counter counts; the chrome path
omits the two lines rather than printing them as zero, so the output
does not even hint that two thirds of the trace's structure was
dropped.

**The shipped path is sound.** The page's embedded handoff is the
trackevent protobuf, so a reader who clicks through from the report
gets the complete trace. This is the documented
`bga timeline --format chrome` invocation, taken by hand.

The other twelve queries were checked against the emitted trace's real
tables and arg keys this round: all resolve.

## Required Fix

The reader is told, at the moment the choice is made and at the moment
it bites.

- **The chrome summary reports flows and counters as `0`**, beside the
  slice count, rather than omitting the rows — the same shape the
  trackevent summary prints.
- **`--format chrome` says what it costs**, in its help and in the
  summary: the JSON format carries no flows and no counters, and the
  queries that read them return nothing.
- **The query library names its requirement.** Each canned query
  declares the tables it reads, so the two that need a trackevent
  trace can say so beside themselves instead of returning an empty
  result set.

## Falsification

A guard that emits both formats from one fixture and asserts the
summary's reported flow and counter counts equal the trace's actual
ones — zero included. Today the chrome summary reports neither, so
there is nothing to compare.

And a guard over the query library: every canned query's declared
tables are a subset of the tables the format it is offered for
actually emits. Today `waited-on-flow` and `concurrency-curve` are
offered for both formats and satisfy only one.

## Out of Scope

- Adding flows and counters to the chrome JSON. The format has async
  and counter events, but `UX-298` chose trackevent precisely because
  it carries this structure natively; re-implementing it in JSON is a
  larger decision than telling the truth about the current output.
- Which format should be the default. It is trackevent and stays so.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The summary, before and after

On `UX-358`'s committed two-plane snapshot, both formats from the same
two logs:

```console
$ # before
Wrote both planes to …/t.chrome, aligned on work-a.bst.
  Open it with Perfetto (https://ui.perfetto.dev) or chrome://tracing.

$ # after
Wrote both planes to …/t.chrome, aligned on work-a.bst.
  3 slices, 0 flows, 0 counters.
  This format carries slices only - no flows and no counters - so the
  queries that read them (`waited-on-flow`, `concurrency-curve`) return
  nothing. `--format trackevent` carries all three.
  Open it with Perfetto (https://ui.perfetto.dev) or chrome://tracing.
```

And the trackevent summary now prints the same three, so the two can
be compared at a glance:

```text
  4 slices, 0 flows, 3 counters on 7 tracks. …
```

The counts are read **off the file**, not off the converter's own
bookkeeping: the chrome path calls two converters that have always
written this shape, and what a summary should report is what landed on
disk. The guard re-derives them from the JSON and additionally asserts
the writer emits no `s`/`t`/`f`/`C` events, so the zeroes stay true
facts rather than a constant.

### Told at the moment the choice is made

`--format`'s help now reads "`chrome` writes the legacy Chrome JSON -
slices only, no flows and no counters, so the queries that read them
return nothing".

### The query library names its requirement

`concurrency-curve` already declared `reads: "counter"` and nothing
rendered it; `waited-on-flow` declared nothing. Both declare now, and
`requirementLine` draws the sentence beside the query in both places a
query is rendered — the worked example and the four category folds:

```text
Needs a trackevent trace: this reads the `flow` table, which
`bga timeline --format chrome` does not write. Against the legacy JSON
it returns no rows - which is the format missing the structure, not
the build lacking it.
```

The last clause is the whole point, and a guard asserts it: a reader
who reads an empty result as "the build had none" is exactly the wrong
answer this item was filed on.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| H1 | omit the two zeroes from the chrome summary again | 4 of 9, incl. `test_the_chrome_summary_reports_all_three_counts` |
| H2 | drop `CHROME_COST` from the summary | 1 of 9: `test_the_summary_names_the_price` |
| H3 | remove `reads: "flow"` from `waited-on-flow` | 1 of 9: `test_both_queries_that_need_a_table_declare_it` |
| H4 | reword the requirement to drop "not the build lacking it" | 1 of 9: `test_the_sentence_says_which_format_and_why_it_is_empty` |

### Deviation from the Required Fix

- **None.** All three bullets are done as written, and the Out of
  Scope is respected: no flows or counters were added to the chrome
  JSON, and trackevent stays the default.
- The counts in the filing (826/836/538 against 663/0/0) came from a
  live snapshot that is not in the tree. This closes against
  `UX-358`'s committed two-plane snapshot, whose numbers are smaller
  (4/0/3 against 3/0/0) and whose *shape* is the same — and the guard
  asserts the premise rather than the figures: the trackevent trace
  carries counters and the chrome one carries none.
