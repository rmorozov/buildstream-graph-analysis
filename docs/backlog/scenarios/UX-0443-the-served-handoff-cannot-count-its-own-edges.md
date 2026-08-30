# UX-443: the served handoff cannot count its own edges

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 70, closing `UX-431` | **Serves:** anyone who runs `bga view` and opens the handoff page instead of exporting a report | **Topic:** viewer

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
