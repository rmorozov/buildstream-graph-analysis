# UX-364: the Perfetto lead promises a plane the trace does not carry

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-348 (the lead sentence), UX-362 (the same defect, opposite sign) | **Serves:** anyone opening a Plane 1 capture's trace in Perfetto | **Topic:** viewer

## Motivation

`UX-362` fixed an absence sentence that denied a timeline it did not
own. Sweeping the same page for every Plane 2 claim — the measurement
that item should have made and did not — found the mirror image three
sections up, in `UX-348`'s handoff lead:

> **Both planes of this run land in one trace: Plane 1's element spans
> and Plane 2's process lanes**, on one clock, joined by the element uid
> this report prints. Open it with "Open timeline in Perfetto" at the
> top of this page, then Query (SQL), and paste one of these.

On `tests/fixtures/with_timeline` — Plane 1, no Plane 2 — the second
half is conditional on `options.hasTimeline` and correct. The first
half is unconditional and false: there are no process lanes in that
trace, and the sentence tells the reader to go looking for them.

```text
with_timeline, every rendered sentence naming Plane 2
  1. "✓ high confidence · 100% task coverage · Plane 2 not captured"   true
  2. "Both planes of this run land in one trace: … Plane 2's process
      lanes …"                                                        FALSE
  3..11. the query library's own descriptions                      library
  12. "Plane 2 was not captured for this run, so there is no
      per-process detail…"                            true after `UX-362`
  13. the schema's sentence for `plane2_absence`                       true
```

**Why this was not folded into `UX-362`.** That item's Required Fix is
explicit — *"The change is one string and the guards that quote it"* —
and this one is not. The correct predicate is not `has_timeline`: this
capture *has* a timeline and still has no Plane 2 lanes. Nor is it
`plane2_absence`, because `DECLINED` means the plane was captured and
this analysis was told to ignore it, while `bga timeline` reads the raw
log regardless and the lanes *are* in the trace. The honest predicate
is whether the trace was built with a Plane 2 raw log, and **no
published field says so**:

```text
run keys matching plane|timeline|trace   golden []  macro_micro []  with_timeline []
top-level plane keys                     ['plane2_absence'] / +coverage / ['plane2_absence']
```

`run.has_timeline` is injected by the view layer, not published in
`report.json`. So this is a contract change plus a renderer change, and
it belongs in its own item where the new field can be named, versioned
and guarded.

## Required Fix

Publish what the trace carries, then say only that:

- A field on the run — the natural spelling is `has_plane2_lanes` — set
  from the same fact `bga timeline` branches on (the raw Plane 2 log was
  present when the trace was built), not from `plane2_absence` and not
  from `--no-plane2`.
- The lead sentence names one plane or two according to it. A Plane 1
  trace gets a lead about element spans that does not mention process
  lanes, and does not imply a join that has nothing to join.

## Falsification

Boot `tests/fixtures/with_timeline` and assert no rendered sentence
claims Plane 2 content is in the trace, while `macro_micro` and a
two-plane capture keep the claim they are entitled to. The clause has to
fail on today's tree, which it does — sentence 2 above.

The `DECLINED` case is the discriminating one and needs its own fixture
or a constructed run: Plane 2 captured, analysis told to ignore it, raw
log present. A fix that keyed off `plane2_absence` passes every clause
above and is wrong exactly there.

## Out of Scope

- The query library's own descriptions (rows 3–11). They describe what
  a query asks, not what this run contains, and a reader who opens the
  Plane 2 category on a Plane 1 capture is asking a different question
  — whether those queries should be marked unanswerable is `UX-321`'s
  territory, not this item's.
- `UX-362`'s absence sentence, which is done.
