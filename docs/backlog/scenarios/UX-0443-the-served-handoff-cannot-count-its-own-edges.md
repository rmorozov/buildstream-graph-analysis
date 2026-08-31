# UX-443: the served handoff cannot count its own edges

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 70, closing `UX-431` | **Serves:** anyone who runs `bga view` and opens the handoff page instead of exporting a report | **Topic:** viewer

## Motivation

`UX-431` gave the trace handoff a sentence saying what the dependency
graph's edges became — how many are arrows, and the named reason for
each one that is not. It reaches two of the three readers:

| reader | has the accounting |
|---|---|
| `bga timeline` on a terminal | yes, from `describe()` |
| `bga view --export` | yes, `run.trace_flow_losses` in the payload |
| `bga view`, served | **no** |

The served page cannot have it yet, and the reason is a decision worth
keeping. `UX-296` moved the trace render **off the startup path**: the
server asks whether a timeline *could* exist (a file test) and renders
the bytes on the first request for them. That was not an optimisation —
building the trace at startup put a 30 GB projected read between the
user and the socket on a field capture. So `run.json` is written before
anything has parsed a build log, and `flow_losses` is a fact only the
render knows.

`bga/viewer/questions.js` already draws nothing when the key is absent,
so the served page is silent rather than wrong. Silent is what
`UX-431`'s own §4e argument says is second-best.

## Required Fix

- **Get the accounting to the served page without rendering at
  startup.** The candidates, to be chosen in the item: count the edges
  and their reasons in a cheap pass that reads `graph.json` and the
  build log only (both already parsed elsewhere); or have the trace
  handler publish the accounting when it renders, and the page re-read
  `run.json` after the trace arrives; or serve it from a small endpoint
  the section fetches.
- **Whichever is chosen, the startup path must not render the trace.**
  `UX-296`'s measurement stands and this item does not reopen it.
- A guard on the **served** page, not on the export — the export half
  is already held by `TestTheLostEdgesAreAccountedFor`.

## Out of Scope

- **The accounting itself** — `UX-431` defines it and this item only
  moves it to a third reader.
- **Rendering the trace at startup**: measured and rejected (`UX-296`).

## Acceptance Test

Serve a snapshot with a timeline, fetch the handoff page, and read the
section: it names the edge count and the reason its arrows are missing,
with the same numbers `bga timeline` prints for the same snapshot. A
mutation that removes the accounting from the served payload must
redden the guard.

## Outcome

_Not started._

## Outcome (round 71, 2026-08-31) — 🟢 Done

**The first candidate, and it is cheaper than the item assumed.** The
accounting is a function of the **build log and the dependency graph**;
`flow_accounting` computes it from those two and nothing else. No
endpoint, no re-read of `run.json` after the trace arrives.

### Why the startup path is untouched

Not a timing — on a 56 KB committed log every path is fast, and the
measurement `UX-296` was made on is a 30 GB read no fixture here can
carry. What can be checked on any capture is **which files were
opened**, by wrapping `open` and `gzip.open` while each path runs:

```text
plane-1 only opens:  build.log, run/graph.json
full render opens:   analyze.json, build.log, host-samples.jsonl,
                     plane2.log.gz, run/graph.json, run/run-context.json
```

`plane2.log.gz` is the file that read was, and it is absent from the
first list. The timing agrees anyway — 0.005s against 0.090s on the
capture with a real raw log — but it is the second-best evidence and is
recorded as such.

The same census over the whole served startup confirms it end to end:

```text
startup opened: analyze.json, plane2.json, run/graph.json,
                run/run-context.json, run/sources.json, run/trace.json
raw Plane 2 log opened: False
```

### The gap, closed, on the served page

```console
$ bga view examples/06-.../runs/20260821T170127Z/run --port 8975 --no-browser
$ curl -s http://127.0.0.1:8975/run.json | ...
has_timeline: True
trace_flow_losses: {'edges': 34, 'drawn': 32, 'no_task': 0, 'out_of_order': 2}
```

and the hand-off page itself, read out of the served DOM:

```text
32 of 34 dependency edges are drawn as arrows in this trace. 2 are
not: the two spans do not begin in the dependency's order, so an arrow
would point the wrong way.
```

Same numbers `bga timeline` prints for the same snapshot, which is the
acceptance test.

### The guard is on the served side, and fetches over a socket

`tests/unit/test_the_served_handoff_counts_its_edges.py`, seven
clauses, 2.8s (medium). `run.json` is assembled **inside** `serve`, so
a guard that called the document builder could pass while the served
page still had nothing — it starts the server on a thread and fetches
`/run.json` the way the page does.

Three of the clauses are not about the new key at all:

- one holds the served numbers **equal to the render's** on the same
  capture, so the cheap path is compared rather than asserted
  equivalent;
- one re-asserts `UX-431`'s identity (drawn + named reasons = edges) on
  the served numbers, so a reason nobody counts breaks it here too;
- one asserts the **full render does** open the raw log, so the clause
  above it is a distinction rather than a fact about this capture.

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| Q1 | the served payload never gets the key (the gap, restored) | the three payload clauses |
| Q2 | `flow_accounting` renders the trace instead (`UX-296` reopened) | **the open-census clause, alone** |
| Q3 | the wrapper is handed the snapshot instead of the run directory | the payload clauses **and** the resolution clause |

Q2 is the one the second Out of Scope bullet needs: it reddens exactly
the clause that holds the startup path, and nothing else.

### Deviation from the Required Fix

None. The first of the three candidates was chosen and the reason is
measured above; the startup path does not render the trace; and the
guard is on the served page, not the export.

### The suite

```console
$ make lint
All checks passed!

$ make test
5463 passed, 28 skipped, 1 warning in 274.64s (0:04:34)
```
