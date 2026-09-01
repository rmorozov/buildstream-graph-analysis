# What the viewer answers, and when to drop into Perfetto

`bga view` renders a page. `bga timeline` writes a trace Perfetto opens.
The page has a button that hands the trace over. Nothing in the
documentation said **when a reader should press it** — which is what
this file is for, and it states a rule rather than a feeling.

## The rule

> **The report has no time axis.** Every number in it is a total, a
> per-element aggregate, or a ranking. The moment a question needs
> *when*, or needs an individual **process**, its answer is not in the
> report — and Perfetto is the instrument.

That is not a design preference; it is a property of the payload, and
it is checked by
[`tests/unit/test_the_viewer_perfetto_boundary.py`](../../tests/unit/test_the_viewer_perfetto_boundary.py).
Measured on `tests/fixtures/macro_micro/run`:

```text
report.json                       25 top-level sections
  occupancy.peak_concurrency      2            one scalar
  occupancy.average_concurrency   1.162…       one scalar
  occupancy.resource_occupancy    {PROCESS: 1.162…}
  utilisation.buckets             6 totals, not 6 instants
  element_join[]                  11 elements, 19 keys each
```

`utilisation.buckets` looks like a series and is not: its six keys are
`useful`, `idle_no_tasks`, `idle_underparallel`, `wasted_retry`,
`wasted_rebuild`, `untracked` — a partition of the wall clock, summed.
There is no list of timestamps anywhere in the document.

## The three crossings, named

Each is a place where the report holds the *element's* answer and the
trace holds the *process's*. They are the whole boundary in practice.

| the question | the report gives you | Perfetto gives you |
|---|---|---|
| how much memory did this need? | `element_join[].peak_rss_kb` — the element's peak | `debug.max_rss_kb` on each process slice: **which** process wanted it |
| what does this element actually run? | `element_join[].dominant_binary` — one name | `debug.cmd` on each slice: the untruncated argv, in order |
| how parallel was the build? | `peak_concurrency` and `average_concurrency` — two scalars | `UX-310`'s counter track: the curve, so you can see *when* it collapsed |

A fourth is worth naming because it is the one people reach for first
and do not need: **"where did the time go, per element"** is
`attribution` and the element table, entirely in the page. The canned
question `element-time` exists so a reader can slice it *further*, not
because the page cannot answer it.

## The canned questions, sorted by whether you needed to leave

`bga view` serves seventeen questions under the handoff on its
`perfetto.html` page, ready to paste into Perfetto's query box. Sorted
against the rule above:

**Needs Perfetto — the answer is per-process or per-instant:**

| question | why the page cannot |
|---|---|
| `element-commands` | the page has `dominant_binary`, one name; this is every command |
| `peak-rss` | the page has the element's peak; this finds the single process |
| `concurrency-curve` | the page has two scalars; this is the shape over time |
| `failed-processes` | the page reports that an element failed; this reports which command did |
| `process-storm` | needs the per-process count *and* their durations together |
| `cpu-versus-wall` | per-process `debug.cpu_us` against each slice's own wall time |
| `cost-by-executable` | the page has `by_binary`, which is counts; this is wall, CPU and peak RSS per program |
| `executables-in-element` | the same pivot inside one sandbox: `binary_cost` has that element's CPU per binary, this adds the wall time and the peak resident set |
| `resource-queues` | `attribution.resource_wait_us` is the waiting summed over every scheduler queue at once; this is per queue, and only the per-queue figure says which limit to raise |

**Does not need Perfetto — the page answers it, and the query is for
slicing further:**

| question | the page's answer |
|---|---|
| `element-time` | `attribution`, and the element table |
| `stalls` | `occupancy.idle_us`, and the idle findings |
| `dependency-wait` | the critical path and the waited-on chain |
| `time-by-kind` | the by-kind breakdown |
| `waited-on-flow` | the declared graph, in `structural` |
| `sandbox-tax` | the sandbox-tax section (Plane 3) |
| `which-run-is-this` | the identity header |
| `graph-levels` | `parallelism.levels`, and the level decomposition it draws |

Nine of seventeen genuinely require the trip. The other eight are
sharper instruments for something the page already told you — which is
the right ratio for a library of *follow-up* questions, and worth
knowing before assuming a reader who opened Perfetto had to.

Three of these arrived after this section was first written and were
not added to it — `graph-levels` (`UX-380`), `cost-by-executable`
(`UX-433`) and `executables-in-element` (`UX-448`), which is what
turned the count above from thirteen into sixteen. Nothing noticed,
because the guard on this section read the library for the questions
the guide *lists* and never the other way round. It reads both
directions now
(`test_the_viewer_perfetto_boundary.py::test_the_guide_sorts_every_question_the_library_serves`).

## By role

Against [the roles model](../design/roles.md):

| role | where they live | do they ever need Perfetto? |
|---|---|---|
| **R1** the local optimizer | the page, for the whole macro→micro loop | **Yes, at the last inch.** The macro half is all aggregates; the micro half ends at "which command inside this sandbox", which is `element-commands` |
| **R2** the recipe author | the page, for their element's cost | **Yes.** Their element's *contents* are exactly the per-process half — what it ran, what wanted the memory |
| **R3** the graph owner | the page, entirely | **No.** Every structural question — critical path, floors, blast, criticality — is a per-element aggregate. R3 has no reason to open the trace |
| **R4** the CI gatekeeper | the CI comment and exit codes | **No, and it must not.** A gate is non-interactive; Perfetto is a UI. A gate that needs a human to open a trace is not a gate |
| **R5** capacity operator | — | **No, and this is a gap.** The trace is *one build*. Dropping into it cannot answer a fleet question |
| **R6** CI user (queue latency) | — | **No.** The trace starts when the build does; the waiting R6 experiences happened before the first slice |
| **R7** release manager | — | **No.** Variance and worst-case are questions about *many* runs; one trace has one |
| **R8** engineering lead | — | **No.** Cost in engineer-hours is not in a trace |

**The finding worth carrying into the next brainstorm:** dropping into
Perfetto is an escape hatch for **R1 and R2 only**. For R3 and R4 it is
unnecessary, and for R5–R8 it is *useless* — not because the UI is
wrong but because the artifact is one build, and their questions are
about many. So "go look in Perfetto" can never be the answer to the
roles the model already marks Gap or Partial. Whatever closes those has
to be a new aggregate over runs, not a better view of one.

## What the page answers about *more than one* run (`UX-394`)

The rest of this document is about one snapshot. Two of the page's
answers are not:

- **"What changed since last time?"** — the noise band and the store
  trend, which read the runs *around* this one.
- **"Show me that other run"** — the rail's run picker. `bga view` is
  started on one snapshot and serves any snapshot in that project's
  store, so moving between them is a click and not a restart. The
  stamp is in the URL (`?run=20260101T000000Z`), which means a run is a
  link you can send, and the back button walks the ones you looked at.

The picker appears only where there is a choice: a store with two or
more runs. One run is not a choice, and an **exported report has no
store at all** — it is one file over one snapshot, so it renders no
picker. That is the one place in this document where the served page
and the attachment answer differently, and it is a property of the
artifact rather than of the page.

What this does *not* make the page is a cross-run analyser. Comparing
many runs is `bga snapshot --list` and the store aggregate; the picker
moves the same single-run report from one snapshot to another.

## What the page will not do, on purpose

- **It will not become a trace viewer.** `UX-193`'s standing rule is
  that the page renders the schema and computes nothing; a time axis
  would mean carrying per-instant data, which is the trace's job.
- **The export carries the trace with it.** `UX-314`: the attached
  report holds the trace as a file you can save and drag into
  `ui.perfetto.dev`, so the boundary above survives a report that
  travelled by email.
- **Above 4 MiB compressed the handoff changes shape** (`UX-299`):
  Perfetto fetches the trace rather than receiving it by
  `postMessage`. The rule for *when to press the button* does not
  change; only the transport does.
- **Above 8,000 tracks it is refused** (`UX-430`), and that one is not
  about transport. Perfetto draws a row per track, and a big capture
  reaches the track bound while its byte figure still looks
  comfortable — 491 KB against 4 MiB at 16,832 tracks. `bga timeline
  --planes 1` is the answer, and [`cli.md`](cli.md)'s ceilings table
  is where all three bounds are listed. This is the one case where the
  rule above *does* change: the answer is still in the trace, and the
  trip has to be made with fewer lanes.
