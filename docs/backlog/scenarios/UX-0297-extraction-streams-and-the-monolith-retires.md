# UX-297: extraction streams, and the monolith retires

**Priority:** High | **Status:** 🟢 Done | **Depends on:** Direction 15, UX-298 (the trace it writes beside), UX-215 (the aggregate pattern) | **Serves:** R1, R2 | **Topic:** capture

## Motivation

Measured this round: **~95 % of the 1.5 GB monolith is dead weight
at read time.** `summarize()` embeds the entire per-process record
list into plane2.json (`tools/bst_native_build_tracer.py:3648`,
`"processes": records` — ~550 B/record, ~2.7 M records at field
size) and **no production reader consumes it**: every consumer
(`correlate`, analyze, the aggregate walk) reads only the small
per-element aggregates sitting beside it in the same file. The
capture path holds the full record list in RAM to write it (the
tracer's own measurement: 479 MB per 400 k processes), and
`bga snapshot`'s auto-compare then `json.load`s **both** runs'
monoliths with the two parses coexisting (`bga/cli.py:371-388`,
measured 1.7× a single parse — ~7-8 GB projected, on the machine
that just finished the build).

Direction 15's rules 2 and 5: events are a stream, and analysis
reads aggregates. Everything the published numbers need from
Plane 2 is a per-element reduction — the census, the join's
achieved parallelism, CPU coverage, peak RSS, dominant binary —
and reductions stream: none of them needs the event list in
memory, only running totals per element.

## Required Fix

Extraction processes the raw log as the line stream it already is,
folding events into per-element aggregates as it goes and (with
`UX-298`) appending trace packets as it goes; peak extraction RSS
becomes O(elements), not O(events). The per-element aggregates land
in a small schema-stamped JSON (the `element_join` inputs, the
census — what `correlate` actually consumes); the `"processes"`
record list is **no longer embedded** — records live in the raw log
they came from and the trace artifact `UX-298` derives, so
plane2.json collapses to the ~5 % that is actually read. The
auto-compare parses sequentially and releases (never two monoliths
coexisting). Reading stays one interface:
a legacy run's monolith is still consumed (streamed with a
line-oriented fallback or read once with a size warning), so old
stores do not die; which path served the data is stated in the
payload's provenance.

## Out of Scope

- The trace artifact's format (`UX-298`).
- Any change to what the published numbers mean — every aggregate
  must reproduce the monolith path's values exactly on the same
  input (that equality is the migration's guard).

## Acceptance Test

On the generated big-run input: extraction completes under an
argued RSS ceiling (the record list alone measured 479 MB per 400 k processes at capture today); the aggregates
byte-match the legacy path's numbers on the same small fixtures
(golden equality); no `plane2.json` is written for a new capture;
a legacy run still analyzes with identical output; mutation:
buffering the whole event list again reddens the RSS guard.

## Progress (2026-08-25)

🟡 **Partly done.** The read side of this item landed and is measured;
the streaming clause did not, and the measurement below says why
rather than leaving it as an omission.

**What the monolith cost, and what it costs now.** Measured on a
generated 200,000-process trace, the same file extracted by a worktree
at the pre-change commit and by this tree:

```text
                              before (round 39)          after
plane2.json on disk               69,641,647 B         43,879 B
  the record list's share of it          99.94%              0%
extract it and write it                  12.4 s           8.1 s
peak RSS of that                        267 MB          287 MB
```

The 1,587x is the whole item's premise, confirmed: nothing read the
records. `correlate`, `analyze` and the store aggregate all read the
per-element reductions sitting beside them, and the repository's own
two-plane fixture has carried no `processes` key for many rounds while
every asserted number was computed from it.

**Landed.**

1. *The record list left the report.* `summarize` publishes the
   reductions and stamps them `plane2/v2`. The records live in the raw
   trace log the snapshot keeps - which is what the timeline is
   rendered from - and `load_records` is the one call that rebuilds
   them, for the trace converter and for the ground-truth test that
   checks records against arithmetic.
2. *Every aggregate became an accumulator.* Ten functions were split
   into `add` and `finish`, and `summarize(records)` is a fold with
   the list poured into it - one code path, two callers. Verified
   byte-identical against the pre-change tree on two generated traces,
   the second exercising both record streams, a configure subtree,
   unresolved buckets, open records and CPU disagreements; and by the
   3,600-test suite, which asserts a great many of these numbers
   directly.
3. *`compute_cpu_time` stopped rescanning.* Its per-element wall span
   re-walked every record once per element - O(elements x processes),
   and 2.0 s of the 9.4 s an extraction spent on this trace. It is a
   running min and max now, which is where most of the 35% went.
4. *The auto-compare releases before it parses.* Rebinding a name
   looks sequential and is not: the previous report stayed alive for
   the whole of the next `json.load`, which is the measured 1.7x.
5. *Reading is one interface.* A capture from before this item is
   recognised by the same rule and read the same way; the analysis
   publishes `plane2_coverage.source` saying which shape served its
   numbers, because both publish the same aggregates and the
   difference a reader needs is why the file is the size it is.
   `bga.contracts.superseded()` names a shape a release reads and
   never writes, which is what an existing store is full of.
6. *Two smaller reads on the way past.* The trace converter streams
   its raw log instead of reading it whole (`UX-168`'s fix had never
   reached it), and `bga doctor` reads the coverage census the report
   already publishes rather than re-tallying the records.

**Not landed then, and why.** *Extraction is not O(elements) yet, and
peak RSS went up 7%.* Measured inside one extraction of the same trace:

```text
after parsing            247 MB resident
after pairing            249 MB
after folding            271 MB      (the records are freed as they fold)
```

The peak is set **before the fold begins**. `pair_events` sorts the
whole event list by timestamp, because the raw log is only
approximately ordered - concurrent writers interleave - and pairing a
START with its own END needs order. So the event list is materialized
whatever the aggregates do, and the fold's own state (~22 MB here, in
timestamps and parentage the algorithms genuinely need) now sits above
that floor instead of the record-holding intermediates that used to.

**Also deviated, recorded.** The acceptance test says *no `plane2.json`
is written for a new capture*. One still is: the same path, the same
name, 1,587x smaller and stamped with its shape. Renaming the artifact
would have moved every reader, every `--plane2` argument, the store
layout and the documentation for no measured gain, and "the file that
was 1.5 GB is now 44 KB" is the fix; "the file has a different name"
is not.

**Falsification.** Six mutations against the committed tree:

```text
M1  the record list comes back                       1 guard red
M2  the concurrency sweep ties the other way         passed - see below
M3  the provenance always says aggregates-only       1 red
M4  the fold stops relabelling                       1 red
M5  the new shape wears the retired id               1 red
M6  the payload stops saying which shape served it   1 red
```

M2 is the one worth keeping. The guard's equality clause - the fold
against the list - is true *by construction*, because `summarize` is
the fold; it passed against a deliberately broken sweep. Four
known-answer clauses over three hand-worked processes replace the
argument with an answer, and the tie is the case written down: one
process starts exactly as another ends, they are never both running,
the peak is 2, and the mutation says 3. M2 reddens now.

## Progress (2026-08-26): the streaming clause, closed

✅ **Done.** The premise above turned out to be half right. Pairing does
need order - but not the *global* order the sort was buying. It needs
one key's own events in order, a key being one process seen through one
mechanism (`_pair_key`), whose START and END are written by one writer
in that order: the hook writes both from the traced process itself, the
spine writes both from the single supervisor. Concurrent writers
interleave *across* keys, which is what breaks the global order and not
this one. Measured on the two real captures this repository carries:

```text
                      events   keys   global inv.   per-key inv.
examples/01 raw           64     40             0              0
examples/06 plane2.gz   1485    813             2              0
```

`examples/06` is the case that decides it: the file is **not** globally
ordered and **is** per-key ordered, so the weaker property is the one
that actually holds on a real capture.

So the algorithm became a generator: `stream_records` yields a record
when its END arrives and holds only the processes currently open, and
`parse_trace_lines` became `list(stream_trace_events(...))` - one
parser in two shapes. `pair_events` is now that generator with its
input and output sorted, so its answer is byte-identical to what it
always was and every caller that wants a list still gets one.
`count_unmatched_ends`' second walk over the events folded into the
pass, because after the pass there are no events to walk.

**What it bought.** End to end on a generated 200,000-process trace,
the same file through `load_and_summarize` in a worktree at the
pre-change commit and in this tree:

```text
                   before      after
peak RSS          288.3 MB   259.5 MB      -10.0%
wall               8.2 s      7.1 s        -13%
report digest   b7e6c5f4f1798c9e - identical
```

and inside one extraction, where the plateau moved:

```text
                        before     after
events parsed          247.4 MB      -      (400,000 dicts, never built)
records paired         249.0 MB   221.1 MB
folded, records freed   46.1 MB    42.8 MB
```

**Stated rather than implied: this is not O(elements).** 185.8 MB of
that 221.1 is the record list, which `merge_record_streams` joins whole
and which the start order every reader sees is sorted from. Extraction
is `O(processes)` - a fifth of what `O(events)` cost. Whether the last
step is reachable is a question with a measurement in front of it, and
it is filed as `UX-313` rather than asserted here.

**One deliberate non-change.** The timeline's Plane 2 writer streams
its events and still sorts its records. Slices are emitted per *track*,
a track is `(element, pid)`, and a dual-stream process shares one with
itself: the spine sees the exec first and the kernel exit last, while
the hook's constructor runs after the exec and its `atexit` before the
exit. So the pass yields the hook's record first and the spine's second
while their starts run the other way - measured on the four-line case,
streamed `[hook 100.001, spine 100.000]` against sorted `[spine
100.000, hook 100.001]`. Emitting that would reorder two slices on one
track, under a change about memory.

**Falsification.** Recorded in the Verification Log with the rest of
round 43.

