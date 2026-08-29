# UX-406: the spine counts every process twice in the trace

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-310 (the counter it un-closes), UX-368 (the queries it feeds wrong numbers) | **Serves:** anyone who takes the handoff and believes a number | **Topic:** capture

## Motivation

With `--trace-spine=on` the round-64 capture (813 processes) emits
**two slices per process** — 813 with `debug.src=hook` and 813 with
`debug.src=spine` (`select debug.src, count(*)` in trace_processor
v57.2). Four of the fourteen canned queries then answer confidently
and wrongly, measured on `examples/06-macro-micro-optimization`:

```text
concurrency-curve   peak 44        plane2.json max_concurrency: 24
process-storm       core.bst 224   report says 112
cpu-versus-wall     core.bst 13.77 CPU-s   report says 7.14
sandbox-tax         core.bst -112.1 unaccounted seconds
```

`docs/spec/trace-dictionary.md` promises the counter's "peak equals
the report's `max_concurrency` **by construction**", and `UX-310`
was closed on that equality — on a capture whose spine was off. This
is not `UX-395` (a format dropping tables): these queries resolve
and return wrong numbers, which is strictly worse. Round 63 checked
that twelve of fourteen queries *resolve*; nobody had checked that
their answers are right with both sources on.

## Required Fix

Pick one identity rule and enforce it end to end: either the
timeline dedupes at emit time (one slice per process, the spine
enriching the hook record it corroborates — the join key exists,
`UX-56`'s attribution work built it), or every canned query and the
counter emitter filter on one `debug.src`. Either way:

- the counter's peak equals `max_concurrency` again on a spine-on
  capture, and the trace-dictionary sentence becomes true in the
  field;
- the four queries above return the report's numbers on the round-64
  capture;
- a guard runs one spine-on capture fixture through the decoder and
  asserts slice-count == process-count (the `trace_processor` gate
  covers the query half where the shell is present).

## Out of Scope

- Turning the spine off by default — its corroboration is the point
  (`UX-376`'s census leans on it); only its double-billing goes.
- The chrome format's missing tables — that is `UX-395`, already
  filed.

## Acceptance Test

- On a spine-on capture of example 06: `concurrency-curve` peak ==
  published `max_concurrency`; `process-storm` for core.bst == the
  report's process count; `sandbox-tax` has no negative rows.
- Falsification: re-emit both sources unfiltered — the
  slice-count guard goes RED.
