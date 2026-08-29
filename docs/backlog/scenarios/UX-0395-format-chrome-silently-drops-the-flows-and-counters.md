# UX-395: `--format chrome` silently drops the flows and counters

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-298 (the timeline speaks Perfetto natively), UX-309 (the arrows that answer "why did this start now"), UX-310 (the counters), UX-312 (the canned question library) | **Serves:** anyone who took the chrome trace to Perfetto and ran a canned query | **Topic:** capture

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
