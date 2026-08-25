# Audit round 40: a snapshot bigger than RAM

Run on 2026-08-25, same retained environment as rounds 10-39. Two
inputs: the sibling's twelve rounds of landings since round 27
(UX-236..295, Directions 10-14 — sampled rather than exhaustively
verified this time), and the field showstopper that sets this
round's subject: a real project's dual-plane snapshot at ~2 GB
(`plane2.json` 1.5 GB, raw log 400 MB gzipped), on which `bga view`
freezes in parsing and dies of memory near server start.

## The landing, sampled

Twelve rounds could not be re-verified item by item, so the round
sampled where it mattered most: the six items this session filed in
round 27, adversarially, plus global health. All six hold —
`--explain`'s references resolve and quote the threshold constant
(publishing it as a literal reddens two guards); `whatif/v1` has no
client-arithmetic path even when the page *lies about its source*
(the guard checks the stub server was actually asked); the
aggregate's percentiles were re-derived by hand and match, with the
cross-host refusal exiting 6 per the UX-186 grammar; the backlog
split conserved all 294 rows with the guards proven retargeted over
both files by mutation; the `Serves:` guards redden both ways.
Suite: **3,524 passed, 0 failed**; lint clean; the last twenty
rows and markers all agree.

One nuance, filed as **UX-301**: UX-235's documented acceptance
mutation (`prepend`→`append` on the decision panel) no longer
discriminates — not because the guard is hollow, but because
UX-286's chapter pass became the ordering authority and its own
guards redden when *it* is mutated. The old insertion-order calls
still sit in `app.js` looking load-bearing, which is how this
verification briefly mistook them for the mechanism.

## The showstopper, reproduced and measured

A scale agent rebuilt the failure synthetically at 100 MB and
400 MB and measured every load path (full table in the report
below; ratios are measured, projections linear):

- **The monolith parses at 2.9× bytes-to-RAM.** One `json.load` of
  plane2.json costs ~4.3 GB and ~30 s at the field size — and
  `bga view` pays it **twice** before the socket exists: once for
  the analyze payload (`bga/cli.py:145`), once in the
  store-aggregate walk (`bga/store_aggregate.py:155`), which
  re-parses *every snapshot's* monolith on every view of *any* run
  to extract two scalars — measured 1.17 GB of RSS to view a 2 MB
  neighbour, and below three runs it publishes null distributions
  after paying it.
- **The band re-analyzes the store** per page load
  (`tools/bga_view.py:214`, `bga/compare.py:1070`), though the
  store rows already carry the durations a band needs.
- **The trace step is the OOM.** It decompresses the 400 MB raw
  log to ~4.7 GB of disk, then reads it as one string at a
  measured 6.3× amplification
  (`tools/native_trace_to_chrome_trace.py:258`) — **~30 GB
  projected**, immediately before `ThreadingHTTPServer` is
  constructed: "somewhere near the http server run", exactly.
- **Capture pays too:** the tracer holds the full record list to
  write the monolith, and `bga snapshot`'s auto-compare parses
  both runs' monoliths *coexisting* (`bga/cli.py:371-388`) —
  ~7-8 GB projected on the machine that just finished the build.

Two facts turn this from "big files are big" into an architecture
finding. **Ninety-five percent of the monolith is dead weight at
read time**: the embedded `"processes"` list (~2.7 M records at
field size) has no production reader — every consumer reads the
small per-element aggregates beside it in the same file. And **the
streaming fix already exists, on the wrong path**: `UX-168` taught
the capture-time tracer to stream and consume; the converter
`bga view` actually calls still does
`pair_events(parse_trace_log(f.read()))`. The house pattern in a
third costume: the analysis knows how to be small, and the paths
that matter never learned.

## The redesign: Direction 15

The user's proposal — adopt Perfetto's protobuf trace format —
is adopted, and widened into the architecture it implies. The
direction's seven rules, argued in full in
[`design/directions.md`](../design/directions.md): capture
computes and view serves (UX-226's decision promoted to law);
events are a stream, not a document; the event artifact is
TrackEvent — the interchange format of the tool the events are
for, appendable, interned, gzip-friendly, and queryable by
`trace_processor` without bga growing a query engine; no protobuf
dependency (the wire format is a page of stdlib code, correctness
held by golden traces and a CI round-trip, never by trust);
analysis reads capture-time aggregates, not events; the handoff
and the export invert to the deep link above a size threshold;
and memory becomes a guarded budget with a generated million-event
fixture.

Deliberately not adopted, with reasons recorded: SQLite/DuckDB (a
query engine inside a tool positioned to hand queries to
Perfetto), Parquet/Arrow (a dependency for analytics nothing
runs), the protobuf library (generated classes for one writer),
and any change to the small published JSON contracts — kilobyte
documents were never the problem.

Decomposed as `UX-296`..`UX-300`: the view that parses nothing;
extraction streams and the monolith retires; the TrackEvent
emitter; the handoff that does not carry the trace; and what a
two-gigabyte snapshot does to a store.

## Standing

This is the first field showstopper since round 15, and the first
that is architectural rather than behavioral. Priority for the
sibling, in dependency order: **UX-296 first and alone** — the user
cannot open their capture today, and most of 296 is deleting reads
(the two scalars to the store row, the band to the rows it already
has, the trace step out of startup); then **UX-297** (stop writing
the 95 % nobody reads — which also collapses the auto-compare
cost), then **UX-298** with `UX-297`'s streaming (the TrackEvent
artifact), then **UX-299**, with **UX-300**'s measurements taken
along the way and **UX-301** whenever a viewer file is open anyway.
The user's instinct — "we exhausted JSON's capabilities" — is
confirmed with one precision: JSON was never the problem at the
sizes the contracts live at; the monolith event document was, and
the replacement is not a different document format but the end of
event documents — aggregates in JSON, events as a stream in the
format of the tool they are for.
