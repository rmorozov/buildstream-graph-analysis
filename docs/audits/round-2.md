# Audit round 2

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping. Rounds 7-10 were always separate files; rounds 2-6 had accumulated inside the design doc, which made it an argument about direction *and* a changelog. The text below is unedited apart from heading levels.

## What the second round found (2026-08-16)

> **Status: everything below shipped, and the backlog is now empty.**
> `UX-41`, `UX-43`, `UX-44` and `UX-48` (the four
> placeholders), `UX-42` and `UX-47` (the two performance defects), then
> `UX-45` and `UX-46` (the two Plane 2 capabilities, each verified
> against a real wrapped build).
>
> Two things are worth carrying forward from doing them, both about
> *verification* rather than about the defects:
>
> - **Byte-identical output on real fixtures did not establish
>   correctness.** `UX-42`'s rewrite produced identical output on all
>   five real captures, and an oracle test against a naive transcription
>   of the original algorithm then found two real bugs in it. Both
>   changed how gaps were *segmented*, which a downstream merge step
>   hides. Where a change claims to preserve semantics exactly, an oracle
>   beats a snapshot.
> - **Three of my own filed acceptance criteria were wrong**, and the
>   measurement was right each time: `UX-48` asked for "the majority" of
>   a starved run's idle to be underparallel (the true answer is 25%, and
>   the rest is genuinely unusable capacity), and two `UX-43` test
>   assertions predicted choke points the correct implementation rightly
>   excluded. Criteria written before implementing are hypotheses too.
>   Each is corrected in place in its own doc rather than quietly dropped.
>
> One new item was filed from this work rather than folded in silently:
> `UX-49`, `parallelism_efficiency` measuring width uniformity rather
> than parallelism, which `UX-41` made visible - since renamed to
> `width_uniformity`, and closed.

The round above was run. It used a 1202-element project as the vehicle,
exactly as suggested, and the vehicle turned out to be the finding rather
than the setting: **items (1) and (2) produced one filing each, and scale
produced five** (`UX-41`..`UX-44`, `UX-47`) - plus a sixth, `UX-48`, from
following the pattern those five exposed back into code scale never
touched.

### The placeholder pattern

Three of the five are the same defect wearing different names:

| what it claims | what it is | filed as |
|---|---|---|
| slack (`_compute_all_slacks`) | `duration * 0.5`, under the comment *"In full implementation, would use forward/backward pass"* | `UX-44` |
| choke points | `in_degree >= 2 and out_degree >= 2`, under a comment naming the dominator approach | `UX-43` |
| level decomposition | BFS first-visit-wins, i.e. *shortest* path from a root | `UX-41` |

Each is a handful of lines. Each is reachable from `bga analyze`'s default
text output. Each is plausible at 11 elements and absurd at 1200 - 43% of
the graph flagged as a bottleneck, a 14-level graph reported as 3 levels,
a "best-case speedup" that converges on 2.0x for any input. And **none of
them says anything provisional in the output a user reads.**

That is the structural lesson, and it generalizes past these three. The
first round audited *what the tool says*; this round found that some of
what it says is scaffolding that was never replaced, and that small
example projects are exactly the conditions under which scaffolding looks
like a measurement. Two follow-ons worth making explicit:

- **Grep for the rest deliberately.** `# Simplified:`, `# Placeholder:`,
  `# Rough estimate`, `# In full implementation` are literal comments in
  shipped code paths that feed the default report. That search is cheap
  and does not need another scale probe to justify it - **so this round
  ran it.** Eleven hits across `bga/`, seven of them in
  `bga/structural/analyzer.py` and already covered by `UX-41`/`UX-43`/
  `UX-44`. Of the four outside it, one is a real user-facing defect and
  is filed as `UX-48`: `IDLE_UNDERPARALLEL` is declared, read by
  `idle_pct`, and **never assigned anywhere**, so every run books its
  whole idle capacity to `IDLE_NO_TASKS`. The two buckets recommend
  opposite fixes - "restructure the graph" versus "raise `--builders`" -
  and a deliberately builder-starved real capture (`--builders 2`, six
  ready libraries) reports 72.30s of "nothing was ready to run". That one
  needed no scale to find, only the sweep.

  The two remaining hits were checked and not filed:
  `diagnostics/analyzer.py`'s `churn_blast_radius = {}` is honestly
  labelled *"would require historical churn data"* and has no data source
  to compute from, and `compute_ready_queue_metrics`'s simplification is
  approximately right for BuildStream's scheduler - though it is the same
  ready-set computation `UX-48` needs, so the two should be reconciled
  rather than duplicated.
- **A quantity computed from a placeholder should not render under a name
  that promises a measurement.** Either compute it or label it. `UX-13`
  and `UX-36` already established this discipline for the floors and
  occupancy blocks - it was never applied to the structural block.

### Scale is a correctness probe, not a performance probe

The expectation going in was that a thousand-element project would test
*readability* (`UX-33`'s rendering) and *speed*. It did test speed -
`UX-42`, 68 seconds, 98% in one quadratic function; `UX-47`, every narrow
subcommand paying the full price. But the three correctness bugs above
were all invisible at small scale for the same reason: **a small graph
does not have enough structure for a wrong structural computation to
disagree with a right one.** `examples/06` has one root, so BFS depth and
longest-path depth differ by little; it has nine buildable elements, so
"43% of the graph" is five elements and looks like a real answer.

The practical consequence for future rounds: a large fixture is worth
keeping around as a *correctness* fixture, not only a benchmark, and
cross-checking two independently-computed quantities against each other
(`max_depth` vs. `len(levels)`, which openly contradict each other today)
is the cheapest way to catch this class without knowing what to look for.

### What the other two probes settled

Both were worth doing, and neither produced work of the size expected:

- **A real CPU measurement (`UX-45`)** is genuinely two `getrusage` calls
  in a destructor that already runs in every traced process. Reading the
  hook confirmed the cost; what it also confirmed is that the *hard* part
  is not the capture but the plumbing - Plane 2 traces one element under
  a wrapped build, Plane 1 covers the whole run, and I9 reconciliation
  needs both for the same run. `UX-45` therefore ships the measurement
  and explicitly refuses to weaken the three standing caveats on the
  strength of partial coverage.
- **Declared-vs-used dependencies (`UX-46`)** produced a **refutation**.
  The cheap approach - match staged dependency paths against the traced
  command lines Plane 2 already records - does not work, and the reason
  is structural rather than fixable: BuildStream stages every build
  dependency into one shared sandbox root, so by the time a compiler
  runs, a dependency's headers are indistinguishable from the base
  sysroot. Real trace data shows all nine elements of `examples/06` with
  the same toolchain-only path set. The real mechanism is file-open
  interception plus a staged-path→element map, which is a much larger
  task, and `UX-46` is filed at that size.

  This is the round's best argument for measuring before filing. The
  hypothesis was mine, formed from reading the hook; had it been written
  up unchecked it would have read as a small, obviously-correct task, and
  whoever picked it up would have discovered the refutation after
  starting rather than before.

### What the third round should probe

The three unaddressed items from the previous round's list stand as
written - **remote execution** (4) and **the CI story end to end** (5)
were not touched, and **scale** (3) is now half-explored: the analysis
side has been probed at 1200 elements, the *capture* side has not, since
the fixture was synthesized rather than built. Adding to them:

6. **A real capture at scale.** Everything in `UX-41`..`UX-44` was found
   against a synthetic run directory. It is internally consistent and the
   findings do not depend on it being real, but nothing yet tells us
   whether the *ingestion* path - `bst_log_to_chrome_trace.py`,
   `bst_show_to_graph.py`, the Plane 2 shim - survives a thousand-element
   build, nor how long that build's own capture overhead is.
7. **A many-core host.** Still untouched, still the condition under which
   `UX-28`'s re-based oversubscription threshold and `UX-27`'s
   `occupancy_ratio` make materially different calls than they do on the
   4-core host every number in both rounds came from.
8. **Beyond the placeholder sweep.** The comment-grep is done (`UX-48`
   was its yield). What it cannot find is the placeholder that was
   written *without* an apologetic comment - `_compute_level_decomposition`
   (`UX-41`) is exactly that, and was caught only because two published
   numbers contradicted each other. Systematically cross-checking
   independently-computed quantities that ought to agree - `max_depth`
   vs. `len(levels)`, `blast_radius` vs. `choke_points`,
   `certified_headroom` vs. `total_improvable_time_us` - is the version
   of this sweep that would have found `UX-41` without a 1200-element
   graph, and it is still un-run.
