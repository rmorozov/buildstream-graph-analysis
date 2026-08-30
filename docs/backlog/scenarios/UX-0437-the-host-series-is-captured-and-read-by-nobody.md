# UX-437: the host memory series is captured every run and read by nobody

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** round 69, strand (a) of the outside walk — is every captured thing reachable? | **Serves:** anyone whose build was slow because the host ran out of memory | **Topic:** viewer

## Motivation

`bga snapshot` samples the host every two seconds for the whole build
and writes `host-samples.jsonl` beside the run. On a real capture of
`examples/06`:

```text
host-samples.jsonl   2,230 B   15 samples
keys: available, cached_kb, clock, interval_s, mem_available_kb,
      mem_free_kb, mem_total_kb, monotonic_at_start, pgmajfault,
      pswpin, pswpout, schema, swap_free_kb, swap_total_kb, t,
      wall_at_start
```

**Nothing reads it.** Checked four ways on that capture:

| destination | result |
|---|---|
| the published page payload | 0 of 14 data keys present |
| `plane2.json` | no `host`, `mem` or `swap` key at all |
| the terminal report | no line mentions host memory or swap |
| the Perfetto trace | one counter track, `traced processes running` |

The two apparent payload hits — `schema` and `available` — are generic
names colliding with unrelated keys elsewhere, so the real reach is
zero. And the reader function exists:

```text
$ grep -rn "read_host_samples" --include=*.py .
tests/unit/test_the_host_was_asked.py:64
tests/unit/test_the_host_was_asked.py:100
tests/unit/test_the_host_was_asked.py:149
tools/bst_native_build_tracer.py:807      <- the definition
```

**`read_host_samples()` is called by its own test and by nothing else.**

`UX-378` built the capture side in round 61 and was right to stop
there — its Out of Scope says so plainly:

> Acting on the series. Naming a capture as memory-starved is a finding
> and a later item; this one is about there being something to read.

**The later item was never filed.** Fixing guide §3.11 asks for the row
before the commit lands, and this is what its absence costs: eight
rounds of every capture writing a series that no reader, no page and no
query has ever seen. This is that row.

The data is not marginal. `pswpin`/`pswpout` and `pgmajfault` are the
difference between "the build was slow" and "the build was swapping",
and `mem_available_kb` against `mem_total_kb` is what says whether the
capacity recommendation `UX-116` prints was reachable on this host at
all.

## Required Fix

- **Decide the destination first**, because there are three and they
  are not equivalent: a counter track in the trace (the series drawn
  against the build, which is what a time series wants), a section on
  the page, or a finding when the series says the host was starved.
  The trace is the cheapest and the most natural shape; the finding is
  what `UX-378` had in mind.
- **Publish it wherever that lands**, with the schema and the sentence
  the visual contract requires — `mem_available_kb` is bytes and must
  say so.
- **A guard that a captured file has a consumer.** This one was found
  by a sweep written for the round; nothing standing asks the question,
  which is why eight rounds passed. The census `UX-401` runs over
  published keys — the gap is one level earlier, between what the
  capture writes and what gets published at all.

## Out of Scope

- **Changing what is sampled**: `UX-378` chose the fields against a
  measurement and this item consumes them rather than revisiting them.
- **The other low-reach files the same sweep flagged** —
  `run/graph.json` at 17% and `plane2.json` at 49% — which are screening
  numbers from a name-matching instrument that over-counts, and each
  needs its own reading before anything is claimed.
- **Naming a host as under-provisioned**: a verdict is a separate
  decision from making the series visible, and the same split `UX-378`
  made still applies.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
```

The series reaches a named destination and a reader can see it. A
mutation deleting `host-samples.jsonl` before the render must redden
the guard; a guard that passes on a capture with no consumer for the
file is the defect this item is.

## Outcome

_Not started._
