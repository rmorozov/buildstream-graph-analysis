# UX-491: the drift gate's own line has no route a reader can reach

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-476` built the same route for the candidate | **Found by:** round 73, closing `UX-488` | **Serves:** the round that has to pair a run's printed shift with the spread it recorded and cannot read the first one | **Topic:** guards

## Motivation

`UX-476` added a `::group::the same document, for a reader without the
artifact` block so the reference candidate could be read by an API
client with no artifact access. `UX-488` used it, and found the other
half missing.

The **gate's own line** — the one that says how many files were
measured, at what shift, over what population — is printed by
`tools/dev_tier_drift.py --against` to stderr, in a step that runs
before the candidate. A GitHub log-reading client returns only a
bounded tail of a job's log, and on a full-suite job the candidate
document (nearly 400 lines) fills it. So on run `33544888654` the
recorded `spread` could be read and the gate line that should be paired
with it could not:

```text
candidate  {'files': 377, 'shift_files': 138, 'shift': 1.069, ...}
gate       (above the returned tail)
```

`UX-488` had to take its pairing from the previous run instead, and
said so. The pairing is the check that `UX-476` item 2 actually landed,
so it should not depend on how much of a log a client happens to get.

## Required Fix

- The gate's summary reaches a reader who can only read a log tail —
  the same `::group::` treatment the candidate got, or the line
  repeated in the candidate step, or the numbers carried in the
  candidate document itself.
- Whatever it becomes, `UX-488`'s Acceptance Test — a run's printed
  shift beside the spread it recorded, from **one** run — can be met
  without the artifact.

## Out of Scope

- The gate's verdict logic, which `UX-476` settled.
- Downloading the artifact — the route `UX-457` built, which works and
  is not the thing at fault here; it is simply not available to every
  reader, which is what this row is about.

## Acceptance Test

One CI run's gate line and its recorded `spread`, both pasted, both
read from that run's log alone.

## Outcome

_Not started._
