# UX-466: nothing measures which captured field reaches a Perfetto slice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** stage 3 needs `UX-465` · independent of `UX-464` | **Found by:** round 72, thread 1 of the audit — whether the maximum information Perfetto and `bga view` could analyse is captured, and whether the mapping to Perfetto's format is right | **Serves:** the reader who opens the trace expecting a field the capture holds and finds the track empty | **Topic:** contracts

## Motivation

Three planes write records; one trace is emitted from them. Nothing in
the suite reads both ends and says which captured field reaches a
slice, an arg, a counter or a track, and which is held and dropped.
`UX-356` did this for the *element join* — every field reaches a
reader — and found the gap worth a row. The same question has never
been asked of the trace.

Without that instrument, thread 1 can only be answered by reading
source and forming an impression, which is fixing guide §5's first
shape: a text scan that cannot tell what the code emits from what it
mentions. This round has already made that mistake twice.

## Required Fix

Three stages, in order. Stage 1 is the instrument every later claim
rests on.

1. **The field census.** `tools/dev_trace_coverage.py`: read a
   capture's own records — Plane 1's parsed log, Plane 2's hook
   records, Plane 3's spine records — and the trace emitted from it,
   and report per field whether it reaches the trace and as what
   (slice name, arg key, counter series, track, flow). Reads emitted
   artifacts on both sides, never source text. Run it over both
   committed fixtures and paste the table.
2. **The other direction.** Which of Perfetto's own carriers the
   emitted trace uses at all — counters, flows, async slices, instant
   events, process/thread descriptors, args — and which it does not,
   against the fields stage 1 reports as held-but-dropped. A field we
   hold and a carrier we do not use is a mapping gap; a field we do
   not hold is a capture gap, and they get different rows.
3. **What the planes could capture and do not.** Needs a real build to
   answer honestly, so it needs `UX-465`. Deferred until then rather
   than guessed.

Stages 1 and 2 land together; stage 3 is a separate commit.

## Out of Scope

- Adding any field to any plane. This item measures; what it finds
  gets filed.
- The viewer's rendering of the trace — `UX-467` asks whether the
  conclusions are sound, this one asks whether the data arrives.
- The Perfetto query library. `UX-368` and round 69 covered the
  queries; the question here is what the queries have to work with.

## Acceptance Test

```bash
python3 tools/dev_trace_coverage.py tests/fixtures/with_timeline
```

pasted, with a line per plane naming fields held, fields emitted, and
fields dropped, and every dropped field either filed as a row or
declared with a reason in the tool itself — `UX-376`'s rule, that a
census names what it could not assess.
