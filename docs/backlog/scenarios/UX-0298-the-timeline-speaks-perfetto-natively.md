# UX-298: the timeline speaks Perfetto, natively

**Priority:** High | **Status:** 🟢 Done | **Depends on:** Direction 15, UX-188 (the timeline it succeeds), UX-297 (the stream that feeds it) | **Serves:** R1, R2 | **Topic:** capture

## Motivation

The user's proposal, adopted by Direction 15 rule 3: the event
artifact should *be* the interchange format of the tool the events
are for. Today the timeline is legacy Chrome JSON — a format
Perfetto merely tolerates — assembled in memory by converters and
regenerated from the raw log; at field scale both properties fail
(a 1.5 GB JSON document, built whole, per conversion). Protobuf
TrackEvent is appendable packet-by-packet (a `Trace` is a stream of
`TracePacket`s), gzips on the fly, interns repeated names, and is
what ui.perfetto.dev and `trace_processor` read natively — the
depth engine's own format, so the artifact written once at capture
is the artifact handed over forever.

## Required Fix

A single stdlib module emitting TrackEvent: varint/length-delimited
wire encoding with field numbers pinned as named constants;
`TrackDescriptor` per lane (process/thread uuids giving the two
planes their hierarchy, Plane 1 elements as parent tracks where the
alignment exists), `TYPE_SLICE_BEGIN/END` with interned names, one
`trusted_packet_sequence_id` per writer, `TYPE_COUNTER` reserved
for the resource series `UX-300` may add. Written streaming during
extraction (`UX-297`), gzipped output. `bga timeline` emits it by
default; the Chrome-JSON converter remains for legacy runs and
`chrome://tracing` users, stated as the compatibility path.

Correctness is held the house way, since no protobuf library
checks the writer: a golden trace whose digest is guarded; a
CI-where-available round-trip through `trace_processor` asserting
slice counts, track names and total duration against the published
report; and the one-time manual open in ui.perfetto.dev recorded
in the log with what was seen.

## Out of Scope

- A protobuf dependency, generated classes, or any second use of
  the wire encoder — Direction 15 declines the dependency: the wire
  format needed here is a page of code.
- Counters/flows beyond what the planes already record — an event
  stream may carry only what a capture measured; a new series enters
  through its own filing.
- Retiring the raw log (it stays the ground truth the trace is
  derived from).

## Acceptance Test

The golden run's trace opens in `trace_processor` (CI extra) with
the expected track count, slice count and per-element durations
equal to the published report's (equality asserted, not eyeballed);
digest stable across two runs on the same input; the emitter
streams — peak RSS on the big-run fixture bounded by the `UX-297`
ceiling, mutation: buffering packets reddens; a run captured
before this feature still gets a timeline via the legacy path.

## Outcome

🟢 **Done**, with two acceptance clauses this container could not run
and one design question answered by measurement rather than by the
filing. All three are recorded below rather than left to be discovered.

**The emitter.** `tools/native_trace/trackevent.py`: varint and
length-delimited encoding, a `TrackEventWriter` that opens a gzip
handle and hands each packet to it as it is built, `TrackDescriptor`
per lane with `ProcessDescriptor`/`ThreadDescriptor` giving the two
planes their hierarchy, `TYPE_SLICE_BEGIN`/`_END` with interned names,
`TYPE_INSTANT` for a process with no observed exit, one
`trusted_packet_sequence_id`, and `TYPE_COUNTER` pinned but unused -
`UX-300`'s series enters through its own filing, because an event
stream may carry only what a capture measured.

Measured on a generated 40,000-process capture:

```text
packets written          120,026
tracks                    40,023      one lane per traced pid, plus
                                      one per element and Plane 1's own
slices                    40,001      and one instant, for the process
                                      with no observed exit
interned names                 6      over 40,001 slices
uncompressed               4.83 MB
gzipped                    1.14 MB    (4.2x)
wall clock                 3.4 s
peak RSS                  82.4 MB
bytes on disk at slice 10,000   already non-zero
```

That last row is the streaming claim, and it is the one the guard rests
on. A ceiling cannot prove streaming: measured, a writer that buffered
every packet would add ~10 MB at this size and pass a 120 MB ceiling
comfortably. Bytes on disk while the writer is still open is something
no buffering implementation can produce, and the mutation that buffers
reddens exactly that clause.

**Why there is no protobuf dependency, and how the field numbers are
held.** Direction 15 declines the dependency and the generated classes;
what is needed here is a page of encoding. The risk that buys is a
wrong field number, which is *silent* - a reader skips a field it does
not know. So every number is a named constant, and each was read from
upstream's own `.proto` rather than from memory: the extraction is
committed as `tests/fixtures/perfetto_field_numbers.json`, carrying
each source file's sha256, and a guard holds the module's thirty-one
constants against it. Mutating `PACKET_TRACK_DESCRIPTOR` from 60 to 59
reddens that clause and *nothing else* - which is precisely why the
fixture exists, since the decoder reads through the same constant and
stays consistent with the writer.

**The format is the default, and the handoff moved with it.**
`bga timeline` writes `timeline.perfetto-trace.gz`; `--format chrome`
writes the legacy JSON, named in the guide as the compatibility path
for `chrome://tracing` and for a pipeline that already parses it. Both
read the same two logs and reach the alignment offset through the same
function, and the guard measures a process landing at the same
microsecond in both. `bga view` and `--export` carry the new format
too: `trace_file` used to render JSON and gzip it, and now renders
straight to its destination because the writer has already compressed -
so the render *is* the served file. The blob is still
`application/gzip`, which Perfetto sniffs on arrival.

**A defect found while measuring, and fixed.** The anchor was picked
from Plane 2 alone. A capture whose heaviest traced element is one
Plane 1 never built - a subproject built in an earlier run, say -
refused with `no Plane 1 'bst-builder' B event found`: a correct
refusal to a question that should not have been asked. The anchor is
now the longest element **both** planes know, falling back to the old
choice when they share none, so a capture that rendered before still
renders. Found by this item's own 20-element streaming fixture, on a
shape the two-element fixtures could not produce.

**What could not be run here, stated rather than skipped.**

1. *The `trace_processor` round-trip.* It is not installed in this
   container and there is no package for it in the environment, so the
   acceptance test's "CI extra" clause did not run. What replaced it is
   weaker in one way and stronger in another: this repository's guard
   carries **its own protobuf reader**, written from the wire rules
   rather than from the emitter, and asserts track hierarchy, slice
   nesting, interning, the sequence flags, and - the equality the
   acceptance test asks for - that the slices and instants drawn per
   element are exactly the `by_element` census the published report
   counted. It cannot catch a field number that is wrong in *both*
   directions, which is what the pinned fixture is for.
2. *The one-time manual open in ui.perfetto.dev.* This container has a
   headless Chromium but the page is a third-party origin and the trace
   would have to be uploaded to it; that is a human's check on a human's
   machine, and claiming it here would be claiming a thing not done.
   The record is: **not yet opened in the UI.**

**Falsification.** Six mutations against the committed tree:

```text
M1  a field number drifts (60 -> 59)                 1 guard red
M2  the emitter buffers every packet                 1 red
M3  the two planes are not aligned                   2 red
M4  an unfinished process gets a fabricated end      2 red
M5  every name is interned again on each use         passed - see below
M6  the sequence never declares its state cleared    1 red
```

M5 is the one worth keeping. The fixture's command lines were all
distinct, so a table that redefined every name it met produced exactly
the same trace as one that interned - the clause had nothing to
intern. The fixture now repeats a handful of command lines, which is
what a build looks like, and a second clause asserts directly that six
slices of one name are one definition and one iid. M5 reddens now.
