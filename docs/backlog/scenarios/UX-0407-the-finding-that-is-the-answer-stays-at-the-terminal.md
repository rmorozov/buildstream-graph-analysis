# UX-407: the finding that *is* the answer stays at the terminal

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-389 (the same disease, plane2 blocks), UX-401 (the census that would have caught it) | **Serves:** R1 and R8 — the reader deciding what to restructure | **Topic:** analysis

## Motivation

Round 64 walked example 06 against its `optimized/` answer key. The
single output that names the *entire* key in one paragraph is
correlate's restructuring synthesis (`bga/correlate.py:1856`):

```text
Restructuring opportunity: 18 declared build edge(s) among 7
element(s) were measured never-read, and they chain those elements
along the critical path: ... Replaying this run with those edges
removed ... finishes in 8.0s against 20.9s: 12.9s
```

That paragraph appears in no `analyze.json` key, no page section,
and not in the default snapshot output — a grep of the round's
export finds zero hits for "Replaying this run" or "edges removed".
The page carries the per-element crumbs (`unused_dependencies`,
"opened no file staged by 3 declared build dependencies…"), so a
reader must open seven element folds and re-do the aggregation the
tool already did, projection and all. `UX-82` asked for exactly this
finding years of rounds ago; it exists — it just never leaves the
terminal. This is the walk's sharpest instance of "the tool had the
data and made the reader do the reasoning."

## Required Fix

- Publish the restructuring synthesis as a keyed finding in the
  correlate contract (addition — no version bump under `UX-190`),
  with its edge list, the replayed wall-clock pair and the saving.
- Render it as a section — it is table-shaped (edges) under one
  sentence (the projection), and by rank it belongs beside the
  headline's cards: on this walk it is the largest single saving the
  analysis computed (12.9 s against a 6.0 s #1 card).
- The default snapshot print keeps pointing at `bga correlate` (it
  does today); the page stops being the one surface without the
  answer.

## Out of Scope

- Trusting the projection as a promise — the existing "evidence,
  not a verdict" caveat travels with the finding wherever it goes.
- The other terminal-only blocks — `UX-389` owns the plane2 block
  triage; this is the correlate document's one synthesis.

## Acceptance Test

- On the round-64 capture: the export contains the synthesis, its
  section renders with the edge table, and the terminal and page
  print the same 8.0 s / 20.9 s / 12.9 s triple.
- Falsification: drop the key from the correlate emitter — the
  contract guard and the section's presence guard both go RED.
