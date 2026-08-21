# UX-194: the Perfetto handoff

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-193 (the page that hosts the button), UX-188 (`bga timeline`, the input)

## Motivation

Direction 7's timeline rule: none of our own, ever —
ui.perfetto.dev's renderer and its SQL engine are the timeline. The
mechanics are the documented deep-link handshake: open
`ui.perfetto.dev`, wait for its `PING`, `postMessage` the trace bytes
— ~30 lines, no upload (the bytes go tab-to-tab, processed
client-side; one docs sentence says so, because it *looks* like an
upload and users should know it is not).

## Required Fix

1. **The handshake** on `bga view`'s page: an "Open timeline in
   Perfetto" button per run, feeding UX-188's combined trace
   (gzipped — Perfetto accepts gzip; measure and record the size win
   on a real capture).
2. **`bga view --perfetto [RUN]`**: skip the report page — serve the
   trace, open a minimal page that runs the handshake immediately,
   exit when the tab has the bytes (the server needs to outlive the
   handshake, not the session; say so in one line).
3. **The canned-SQL page**: PerfettoSQL snippets, paste-ready, each
   with one sentence of what it answers — per-element aggregate
   duration, sandbox-tax share, longest stalls, process-count per
   element — grown as questions recur. A docs page served by view,
   not a feature.
4. **The format decision, guard-visible**: legacy Chrome JSON stays;
   the reasons and the revisit trigger (a trace too large to post
   comfortably) recorded in Direction 7 and referenced from
   `bga timeline`'s docs — so the next person reaching for protobuf
   finds the argument, not an accident.

## Out of Scope

- The protobuf/TraceProcessor native format (decision recorded;
  revisit on the named trigger).
- Bundling Perfetto or running trace_processor locally.

## Acceptance Test

The handshake page, driven by a scripted `window` double (no real
browser in CI): posts the PING, receives the bytes, byte-identical to
the served trace. `--perfetto` serves and prints the url with
`--no-browser`; the trace it serves is UX-188's output verbatim
(digest-compared). The gzip size win is measured on the golden run
and recorded in the log. The SQL snippets execute against a trace
loaded in trace_processor_shell if available locally (marked test,
skipped in CI) — the snippets must at least parse.
