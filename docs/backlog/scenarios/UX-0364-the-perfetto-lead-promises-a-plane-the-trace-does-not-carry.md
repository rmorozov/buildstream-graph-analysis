# UX-364: the Perfetto lead promises a plane the trace does not carry

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-348 (the lead sentence), UX-362 (the same defect, opposite sign) | **Serves:** anyone opening a Plane 1 capture's trace in Perfetto | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome (round 58, 2026-08-28) — 🟢 Done

### The predicate that did not exist

The filing said the honest fact was "whether the trace was built with a
Plane 2 raw log, and no published field says so". That was right about
the gap and slightly wrong about the fix: the fact did not need
deriving, because **`render` already computes it and every caller threw
it away**. It returns `planes` — `["1"]` or `["1", "2"]`.

So `trace_render` keeps the render's own result, `trace_with_planes`
returns `(bytes, planes)`, and the export publishes
`run.trace_planes`. `trace_bytes` still exists and delegates, so its
five other callers are untouched.

### Why neither existing predicate would do

```text
                       absence(run)                      trace planes
two_plane snapshot     "Plane 2 was not captured…"       ["1", "2"]
```

`plane2_absence` answers "is Plane 2 in this **analysis**" and looks for
the report beside the run; the lead asks "is Plane 2 in this **trace**",
which the renderer decides from the raw log. They disagree outright on
the fixture this item adds, and a fix keyed on the absence sentence
would have told that page's reader the plane was never captured over a
trace that carries it. `has_timeline` cannot tell the two trace shapes
apart at all.

The filing named `DECLINED` as the discriminating case. It is one, and
constructing it needs a 46 KB Plane 2 *report* this guard would have to
fake; the disagreement above needs nothing faked and refutes the same
predicate, so that is what the file argues from. Recorded in the guard's
docstring rather than left as a silent substitution.

### The sentence, on every state

```text
fixture         trace_planes   the lead says
golden                  None   no timeline to open here
macro_micro             None   no timeline to open here
with_timeline          ["1"]   Plane 2 is not in it
two_plane          ["1","2"]   Both planes … land in one trace
```

**Three shapes, not two.** The first draft branched on the planes and
kept the old *"lands in this run's trace"* opener for the other side,
which then told `golden` and `macro_micro` — neither of which has a
trace at all — that their element spans were in one. One false claim
traded for another. The browser clause caught it; reading the diff did
not.

### The state that was unreachable

`tests/pages.py` grows `two_plane_snapshot`: a four-line wrapped Plane 1
log, two raw Plane 2 records and the golden run, merging into a real
two-plane trace. Until it existed no guard could reach a page whose
trace carries Plane 2 — which is exactly why the sentence could claim it
unchecked for two rounds. `UX-358`'s lesson, applied before the fix
rather than after it.

### Mutations

Four against the committed tree, all reverted:

| | mutation | result |
|---|---|---|
| M1 | claim both planes unconditionally — the defect itself | 2 failed |
| M2 | stop publishing `trace_planes` | 3 failed |
| M3 | ignore the renderer and report both planes always | 3 failed |
| M4 | the no-trace branch reverts to claiming a trace | 3 failed |

### Three guards moved, none weakened

- **`test_the_lead_says_how_to_open_the_timeline`** asserted `"one
  trace" in lead` — wording this item deliberately changed, and not the
  clause's own stated intent. Replaced by the how-to-open pair it is
  named for, with the trace-contents half pointed at the new file.
- **`test_an_over_threshold_export_carries_the_command_not_the_trace`**
  faked `trace_bytes`, which the export no longer calls. Re-pointed at
  the widened seam; same blob, same threshold, same claims.
- **`test_the_quoted_button_label_is_the_one_the_page_draws`** read a
  label split across a JS concatenation and reported a control named
  ``Open "       + "timeline in Perfetto``. The sentence now keeps the
  label contiguous *and* the guard joins adjacent literals, so a future
  split reports the split.

### Deviation from the Required Fix

The field is `run.trace_planes` (a list) rather than the suggested
`has_plane2_lanes` (a boolean). The renderer's answer is already a list
of the planes it wrote, and a boolean would throw away which plane a
one-plane trace has — a distinction the sentence uses.

The query library's descriptions stay out of scope as filed; the lead
now says in one clause that the Plane 2 queries return nothing on a
Plane 1 trace, which is the reader-facing half of what `UX-321` would
formalise.
