# UX-296: the view that parses nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-226 (the decision this promotes), UX-203 (the store rows it leans on) | **Serves:** R1, R2 | **Topic:** viewer

## Motivation

The field showstopper, reproduced and measured this round: a real
dual-plane snapshot's run directory reached ~2 GB (`plane2.json`
1.5 GB; raw log 400 MB gzipped), and `bga view` on it froze in
parsing and then died of memory near server start.

Measured mechanism: `serve()` builds every payload before the
socket exists, serially running every whole-file load path in the
codebase. (1) The analyze payload `json.load`s the entire
plane2.json (`bga/cli.py:145`) — measured 2.9× bytes-to-RAM, ~4.3 GB
projected at field size, ~30 s a pass. (2) The store-aggregate walk
(`bga/store_aggregate.py:155`) re-parses **every snapshot's**
plane2.json on every view of **any** run, to extract two scalars —
measured 1.17 GB of RSS to view a 2 MB neighbour, and with fewer
than three runs it publishes null distributions after paying it.
The element-slice precedent (capture-time writing, `UX-226`) was
never extended to these scalars. (3) The band re-analyzes every
historical run in-process per page load (`tools/bga_view.py:214`,
`bga/compare.py:1070`) — though store rows already carry the
durations a band needs. (4) The trace step decompresses the 400 MB
raw log to ~4.7 GB on disk and reads it as **one string** at a
measured 6.3× amplification (`tools/native_trace_to_chrome_trace.py:258`)
— ~30 GB projected, immediately before `ThreadingHTTPServer` is
constructed at `tools/bga_view.py:760`: the observed OOM "near the
http server run", with (1)+(2) as the observed freeze before it.

Direction 15's first rule is the fix's shape: **capture computes;
view serves.** Nothing on the `bga view` path may do O(events)
work; large artifacts are opened only to stream bytes to a socket.

## Required Fix

The measured load sites leave the view path: the resource scalars
join the capture-time store row (the `UX-226` precedent, extended);
the band builds from the durations the store rows already carry
rather than re-analyzing the store; the analyze payload is read
from the run's published report where one exists; the trace step
leaves startup entirely — built on demand at first request, spilled
to disk rather than RAM until `UX-297`/`UX-298` retire it. A run
predating an artifact gets the sentence naming the command that
produces it, not an in-process analysis. Serving large files streams (fixed-size
chunks), never `read()`-whole. The guard is a generated big-run
fixture (order 10^6 events, built by the test, never committed)
with a **peak-RSS ceiling** on the view startup path and a startup
**time ceiling** — both with argued numbers in the guard's
docstring, the page-size lesson applied to RAM.

## Out of Scope

- The storage format itself (`UX-297`/`UX-298`) — this item makes
  view honest about what already exists on disk.
- The capture-side footprint (`UX-300`).

## Acceptance Test

On the generated big-run fixture: `bga view` reaches "serving on
127.0.0.1" under the RSS ceiling and the time ceiling with the
big artifacts untouched (open-count asserted via an audit hook —
the trace file may be opened only by the byte-serving handler);
mutation: reintroducing a whole-file parse on the startup path
reddens both. A store containing one big run pays nothing for it
when a different run is viewed (measured in the guard).
