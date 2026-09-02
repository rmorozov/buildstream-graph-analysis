# UX-194: the Perfetto handoff

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-193 (the page that hosts the button), UX-188 (`bga timeline`, the input) | **Topic:** viewer

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

---

## What was built

**The handshake** (`bga/viewer/perfetto.js`, ~90 lines with the
comments): open `ui.perfetto.dev`, ping every 50 ms until it answers
`PONG`, post the buffer once, stop pinging. A button on the report
page — shown only when the run actually has a timeline, because a dead
button is worse than none — and `bga view --perfetto` for the direct
route.

**The gzip win, measured on a real capture** of `examples/06` (871
events, both planes merged, from an actual `bst build all.bst` under
`bga snapshot`):

```text
272,964 B  ->  24,782 B    9.1%, 11x smaller
```

On the tiny golden run it is 1,543 → 348 B (22.6%) — the small-file
case where the gzip header is a visible share. Served as
`application/gzip` rather than with `Content-Encoding: gzip`, because
the page hands the *compressed* bytes to Perfetto, which sniffs gzip
itself; a transparently-decoding fetch would undo the whole win. The
served trace is digest-identical to `bga timeline`'s own output.

**`--perfetto`** lands on a page that runs the handshake immediately
and says, in the two places a user looks, that this is not an upload.
It says so because it looks exactly like one. The server outlives the
launch — the tab fetches from it — and the line says so. A run with no
raw Plane 2 log exits **7** rather than opening a page that would 404.

**The canned-SQL page**: five questions with a sentence each on what
they answer — per-element aggregate, process count per lane, sandbox
tax, longest stalls, one element's commands. Guarded to be `SELECT`
statements that parse, with a `trace_processor_shell` test that runs
them against a real trace when it happens to be installed and skips
otherwise (bundling Perfetto is out of scope, and a CI job that
downloaded it would make a docs page a network dependency).

Tests: 22 (`tests/unit/test_the_perfetto_handoff.py`), the handshake
driven by a scripted `window` double under Node. Nine mutations, each
red.

### Three things found while building it

1. **`bga view` printed a doomed scratch path** — `UX-197` item 2, one
   command over. That item fixed the Plane 1 converter because
   `bga timeline` calls it, and the guard written then watched only
   `timeline`'s output. `bga view` renders through the *merge*
   converter into a temporary directory it deletes, and got
   `Wrote 871 trace events to /tmp/bga-view-XXXX/timeline.json`. Both
   converters take `quiet` now, and the new guard asserts on stderr
   containing no `/tmp/` at all rather than on one command's output.
   **One caller per fix is how a class survives.**
2. **A guard that asserted the wrong thing, found by falsifying it.**
   `test_a_message_from_another_origin_is_ignored` claimed the origin
   check stops an imposter being *handed the trace*; deleting the check
   left it green. It could not have failed: `tab.postMessage(msg,
   origin)` names Perfetto's origin as the only acceptable target, so
   the bytes cannot reach anywhere else whatever answers. What the
   check actually prevents is firing **early** — a stray `PONG` would
   post the buffer before Perfetto's worker is up, and Perfetto would
   silently never receive it. Rewritten to assert that, and the
   module's own comment corrected: it was making the same wrong claim.
3. **Two harness defects that made mutations hang rather than fail.**
   A mutation removing the `resolve` left the promise pending forever
   (fixed with a wall-clock backstop), and pending timers kept Node
   alive after the result was logged (fixed with an explicit exit). The
   suite went from a 60 s subprocess timeout to 4.9 s.

**Deviation from the Required Fix:** none. Item 4's format decision was
already argued in Direction 7 by the filing round, with the revisit
trigger named; this adds the reference from `bga timeline`'s docs and a
guard that both keep saying it.

