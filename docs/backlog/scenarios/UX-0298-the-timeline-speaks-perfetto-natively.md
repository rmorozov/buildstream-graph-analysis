# UX-298: the timeline speaks Perfetto, natively

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** Direction 15, UX-188 (the timeline it succeeds), UX-297 (the stream that feeds it) | **Serves:** R1, R2 | **Topic:** capture

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
