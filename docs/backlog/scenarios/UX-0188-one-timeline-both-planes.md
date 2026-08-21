# UX-188: one timeline, both planes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-51 (the correlate join this visualizes), UX-126 (the snapshot that should feed it)

## Motivation

Field feedback: *"recheck that we can produce chrome:tracing
compatible output for plane2 capture — maybe we can make some kind of
merge tool that can merge timeline from plane 1 and plane 2."* Round
20 ground-truthed it: the pieces **exist and work** —
`bga log-to-chrome` renders a snapshot's `build.log` (verified live),
every extraction writes `run/chrome_trace.json`, and
`bga native-to-chrome combined <plane1_chrome> <raw_log> <out>
--anchor-element X` is exactly the plane-merge the user asked for.
Three gaps keep a user from reaching it:

1. **Snapshots do not retain the raw Plane 2 log** the combined mode
   needs — only the processed `plane2.json`. The merge exists for
   captures nobody makes by default (`capture run --raw-log` only).
2. **Wrong input succeeds silently**: `native-to-chrome standalone`
   fed a `plane2.json` writes `Wrote 0 trace events`, exit 0
   (reproduced live) — the wrong-input-silent-success shape.
3. **Nobody composes it**: reaching the merged timeline takes three
   commands with invented paths — the pre-UX-126 shape that snapshot
   exists to end. The converters also print their status lines to
   stdout (the one stderr-purity exception left in the tool).

## Required Fix

1. Snapshots retain the raw Plane 2 log (compressed — it is
   line-oriented text; gzip at copy-out, the readers already stream)
   behind a sticky `--keep-raw` first, default-on if the measured
   size cost on a big capture is acceptable (record the number).
2. **`bga timeline [RUN]`**: one command, `@last` grammar, that
   produces the combined chrome trace from a snapshot — Plane 1
   always, Plane 2 lanes when the raw log is present, one sentence
   naming what to open it with (Perfetto / chrome://tracing) and what
   was omitted when Plane 2 is absent.
3. `native-to-chrome` fed a file with zero parseable trace lines
   exits non-zero naming what it expected — "0 events" from a
   non-empty file is a refusal, not a success.
4. Converter status lines move to stderr (their payload is the file).

## Out of Scope

- A viewer (Perfetto exists).
- Changing either trace format.

## Acceptance Test

`bga snapshot` (with retention on) then `bga timeline @last` yields
one JSON that Perfetto's validator loads, containing both planes'
lanes with the anchor alignment `combined` mode already implements;
`bga timeline` on a raw-less snapshot renders Plane 1 and says what
is missing; `native-to-chrome standalone plane2.json out` exits
non-zero naming the expected format (mutation: restoring the silent
success reddens it); converters' stdout is empty when writing to a
file.
