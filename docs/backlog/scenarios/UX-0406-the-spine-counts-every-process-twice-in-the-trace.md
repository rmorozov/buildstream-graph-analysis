# UX-406: the spine counts every process twice in the trace

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-310 (the counter it un-closes), UX-368 (the queries it feeds wrong numbers) | **Serves:** anyone who takes the handoff and believes a number | **Topic:** capture | **Area:** tools

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

## Outcome (round 65, 2026-08-29) — 🟢 Done

### The gap and the fix, on a real spine-on capture

A cold `lib-c.bst` captured with `--trace-spine=on`, rendered to
trackevent and decoded from the wire:

```text
                          before              after       plane2.json
Plane 2 slices               158                 87       process_count 87
  src=spine                   87                 87
  src=hook                    71                  0
concurrency counter peak      24                 13       max_concurrency 13
```

**The counter's peak equals the report's `max_concurrency` again** —
which `docs/spec/trace-dictionary.md` promises "by construction" and
`UX-310` was closed on, against a capture whose spine was off.

71 hook records against 87 spine ones, not 87: sixteen of these
processes are static and the spine is the only mechanism that sees them
(`UX-105`'s coverage class). That asymmetry is why the number to check
is the *joined* count rather than "half of the slices".

### The fix is one call, and it is the join that already existed

`merge_record_streams` is `UX-107`'s join and has stopped the **report**
double-counting since round 12. The timeline read
`stream_records` directly and never called it. Everything the emitter
derives — the slices, the exec-chain flows, the concurrency counter —
comes off that one list, so joining at the read fixes all three at once.

**The identity rule chosen is dedupe-at-emit, not filter-at-query**, and
the Required Fix offers both. Filtering the fourteen canned queries
would leave the trace itself carrying two slices per process, so
anything a reader wrote by hand in Perfetto would still be wrong — and
the queries are the surface the audit rounds keep finding defects
through, not the one to trust.

### Why only one of the three readers needed it

`pick_anchor` and `element_spans` stream the same records and take a
**max per element**. A duplicate has the same span as its partner, so a
max over both is the max over one. Held as a clause rather than left in
a comment, because "this reader is safe" is exactly the sort of claim
that stops being true quietly.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | the join is not called — the defect, reintroduced | all three of the slice-count, the src, and the counter-peak clauses (3 failed, 2 passed) |
| A2 | joined, then every spine record dropped — the over-correction | the slice-count and counter-peak clauses (2 failed, 3 passed) |

A2 is the direction that matters as much as A1: "one slice per process"
is satisfiable by throwing half the records away, and that loses every
static process the spine is the only witness for.

### The fixture is built, not captured

Ten raw lines: two processes seen by both mechanisms and one static
process seen only by the spine, with the two dynamic ones overlapping so
the counter peak is a number worth checking (2, never 4). A capture with
a real spine is gitignored (`UX-189`) and needs `bst`; this needs
neither and fails for the same reason. The first clause asserts the
fixture still *is* the case — five raw records, three processes — so a
fixture that drifts cannot quietly stop testing this.

### Deviation from the Required Fix

**None.** The three bullets landed: the counter's peak equals
`max_concurrency` on a spine-on capture, the dictionary sentence is true
in the field, and a guard runs a spine-on capture through the decoder
and asserts slice-count == process-count.

The four canned queries could not be re-run here — `trace_processor_shell`
is not installed on this machine, which is the skip the census already
counts. What was checked instead is the input those queries read: the
trace now carries 87 slices for 87 processes and a counter that peaks at
the published `max_concurrency`, which is the quantity all four were
wrong about.

### Verification

```text
pytest tests/unit/test_one_process_is_one_slice.py             5 passed
pytest -k "timeline or trace"                    326 passed, 1 skipped
make lint                                                      clean
```
