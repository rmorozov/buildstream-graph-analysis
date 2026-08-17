# Design directions: `bga` as a local optimization helper, and `bga` as a CI gate

Written 2026-08-16 after a full hands-on audit and a real macro-then-micro
optimization walkthrough
([`optimization-walkthrough-06.md`](optimization-walkthrough-06.md)). This
is an argument about direction, not a task list — the tasks it argues for
are filed individually as `UX-27`..`UX-40` in
[`scenarios/`](scenarios/README.md). Read
[`architecture.md`](architecture.md) first for what the tool is today.

## The one finding everything else follows from

`bga` measures **how well the scheduler packed the graph it was given**.
It does not measure, and today cannot measure, **whether that graph was
worth packing**.

Every certified floor is derived from the run's own observed graph and
observed durations. A build whose six independent libraries have been
accidentally chained one behind another has a critical path equal to its
own total work, so `LB == T∞ == T_C` exactly, headroom is zero, and
`efficiency_score` is 1.00. Real, measured, on a project built for this
audit:

| | wall-clock | `efficiency_score` | `certified_headroom` | dispatch occupancy |
|---|---|---|---|---|
| deliberately mis-optimized | 39.57s | **1.00 "very efficient"** | **0.00s** | 25.4% |
| three one-line fixes | 27.50s (−30.5%) | **0.83** | **4.05s** | 55.9% |

The tool's headline efficiency number is anti-correlated with real
efficiency across the entire class of problem that build-graph
optimization exists to solve. That is not a bug in the arithmetic — the
arithmetic is right, and `docs/specification.md` Parts 14–18 mandate it.
It is a missing layer: nothing sits above the floors asking whether the
graph is the right graph.

This single fact is why the local helper mis-directs users and why the CI
gate cannot be built on the metrics that exist. Both sections below
reduce to it.

## Direction 1: `bga` as a local optimization helper

**Who this is.** One person, one machine, an iterative loop: build,
analyze, change something, rebuild, compare. `README.md` already sells
this loop and `UX-05`'s walkthrough shows it working on a `sleep N` proxy
project. It stops working on a real one.

### What already works, and should not be disturbed

The analysis engine is genuinely good and the audit found no correctness
defects in it. Attribution sums to the horizon; the determinism harness
is real; the invariants are enforced; `bga compare`'s verdict was right on
every pair tested; blast-radius ranking is the right primitive; the
two-plane split is the right architecture. `choke_points` correctly
identified the artificial chain. `critical_path` was correct every time.
The problem is almost never that `bga` does not know — it is that it does
not say.

### The shape of the fix: stop making the user read JSON

Of the three real problems in the walkthrough project, **zero** were found
by reading the text report:

- The six-deep chain was found by reading `structural.choke_points` out of
  `-f json`. The text report printed `Bottlenecks Identified: 5` and no
  names, and printed `Critical Path Length: 10 elements` and no path,
  because `bga/report/text.py` suppresses the path above five elements —
  i.e. exactly when a human cannot hold it in their head (`UX-33`).
- The over-declared `codegen.bst` dependency was found by knowing the
  project.
- The `notparallel: True` on the heaviest element was found by an ad-hoc
  script over Plane 2's own JSON (`UX-32`).

Meanwhile the report's own ranked "what to fix first" list led with a
`stack` element and a zero-duration `import` element at sensitivity 1.00
(`UX-34`), and its next-step hint recommended raising `--builders` on a
host already running four compilers per core (`UX-35`).

So the first direction is unglamorous and high-value: **every signal the
tool already computes should reach the text report, named, ranked by
whether a human can act on it, and filtered of things that cannot be
acted on.** `UX-25` established the pattern (name the elements, tag the
structural ones); `UX-33`/`UX-34`/`UX-35` apply it to the three places it
was not applied.

> **Done.** All three shipped. The critical path is printed in full with
> per-link durations, choke points are named, structural elements are
> filtered out of the what-to-fix ranking, and the `RESOURCE WAIT` hint
> is conditioned on a real capacity verdict. The paragraphs above
> describe the state that motivated them, not the current output.

### The second direction: make the micro level a first-class answer

Plane 2 is the tool's most distinctive asset and its report is a census —
counts by binary, counts by element, one global concurrency number. The
question it was built to answer ("is this element's native build system
achieving the parallelism it should?") is answerable from data it already
writes to disk, per element, and is not answered:

```
              baseline                      optimized/
  core.bst    peak=1  span=13.05s           peak=4  span=6.03s
  lib-a.bst   peak=3  span= 1.88s           peak=3  span=6.67s
```

One element at peak 1 while its siblings reach 3–4 is the whole finding.
Achieved-vs-requested parallelism per element (`UX-32`) is the single
highest-value addition to Plane 2, and it needs no new instrumentation —
the element's own `make -j1` appears verbatim in the captured `cmd`
strings.

> **Done, with one correction.** Achieved-vs-requested turned out to be
> the wrong headline: a `-j1`-pinned element achieves 100% (200% in the
> real trace, since a gcc driver pipelines `cc1plus` into `as`) of what
> it asked for, and being pinned is the problem. The shipped report emits
> `pinned_to_one_job` and `underachieved_requested_jobs` instead. The
> same finding is now *also* available from Plane 1 alone, from a plain
> `bst show` (`UX-31`).

### The third direction: close the macro→micro loop

Today the two planes are separate tools with separate invocations,
separate artifacts, and — apart from `UX-24`'s combined Chrome Trace — no
analytical connection. The optimization cycle a user actually runs is a
loop between them:

> Plane 1 ranks elements by blast radius and critical-path membership →
> the user picks the top one → Plane 2 explains where *that element's*
> time went → the fix is either a graph change (back to Plane 1) or a
> native-build change (stay in Plane 2).

The missing piece is small and mechanical: Plane 1 knows which elements
are worth looking inside; Plane 2 knows what happened inside them.
Nothing carries a recommendation across. A concrete first step is a single
line in Plane 1's output — *"`core.bst` is on the critical path and is
41% of it; run the Plane 2 tracer against it"* — and a Plane 2 mode that
accepts Plane 1's element ranking and reports the top N elements' internal
parallelism first. This is deliberately not a merge of the two horizons,
which `architecture.md` argues against for good reasons.

### The fourth direction: the capacity axis should stop being decorative

The walkthrough's third iteration is the honest low point, and also the
place where the audit's own first answer turned out to be wrong. On a
4-core host running `--builders 4 --max-jobs 4`, `bga` reported
`violations: []` — because `native_max_jobs` was `null`, recorded only
when the operator passed a flag, even though line 1 of the log the
extractor just parsed reads `Executing command: bst --builders 4
--max-jobs 4 build all.bst` (`UX-29`).

Supplied by hand, the check still did not fire. The audit initially read
that as a second defect, citing the +81% per-element contention Plane 2
measured. That reading does not hold: `UX-09`'s own real timing table
measured 4×4 on this exact host as the *fastest* of six configurations,
and the run in question was 30.5% faster overall. Higher per-element cost
under concurrency is what beneficial parallelism costs, not evidence of
harm.

The defect that survived re-verification is different and sharper: the
bar was BuildStream's own unconfigured default (`4 × min(cores, 8)`),
which stops growing at 8 cores while the host does not. The ratio at
which the check fired was therefore 4× the cores on a 4-core host and
0.5× on a 64-core one, and above 8 cores it flagged configurations
sitting *below* one process per core — reported as oversubscribed by one
branch while meeting the next branch's own definition of idle capacity
(`UX-28`).

Five shipped features (`UX-12`/`UX-15`/`UX-16`/`UX-17`/`UX-21`) hang off
that field and that threshold. Both are now fixed, which turns a dormant
subsystem on — and the episode is the clearest argument in this document
for the general point: a config-level check reasoning about *potential*
demand cannot settle these questions, because potential demand overstates
real demand whenever an element has less parallel work than it has job
slots. `UX-32`'s measured per-element concurrency is what would.

### What a good local session should look like

Concretely, the report a user should get on the walkthrough's baseline:

```
Biggest structural problem: 6 elements are serialized that need not be
  lib-a.bst → lib-b.bst → lib-c.bst → lib-d.bst → lib-e.bst → lib-f.bst
  Each depends only on core.bst. Estimated wall-clock if fanned out: 21s (from 39.6s).

Dispatch occupancy: 25.4% of available slot-time used (40.25s of 158.3s).

Elements worth looking inside (Plane 2):
  core.bst - 41% of the critical path, pinned to -j1 by `notparallel`.

Capacity: builders 4 x max-jobs 4 = 16 potential processes on 4 cores.
```

Every number in that block is either already computed today or is
derivable from data already captured. None of it is currently printed.

## Direction 2: `bga` as a CI tool

Three jobs, in increasing order of how hard they are and how badly the
current design serves them.

### 2a. Gather analytics — nearly done, needs plumbing not design

`bga analyze -f json` is complete, stable, deterministic (`I11`, with a
real N-run harness), and carries provenance and run identity. The CI job
in `.github/workflows/ci.yml` already captures real runs, real Chrome
traces, and full run directories as artifacts, and it already treats a
`bga` failure as data rather than as a build break. This is the part of
the tool that is ready.

What is missing is the boring part: a documented, stable "one row per
run" projection for a time series (run identity, targets, wall-clock,
occupancy ratio, per-category attribution, per-element durations,
confidence and its sub-scores), so a pipeline can append to a store
without re-deriving a schema from the full report. Worth pinning
explicitly as a compatibility surface, because everything in 2b and 2c
consumes it.

One real caveat to document loudly: `run_identity` correctly refuses to
compare unlike things, and `bga compare` warns when two runs do not look
like the same project. In CI, where the project legitimately changes every
commit, "not the same project" is the normal case, and the warning must
not become noise that trains people to ignore it.

### 2b. Highlight problems — blocked on the metric, not on the plumbing

Everything in Direction 1 applies verbatim: a CI comment that says
`Bottlenecks Identified: 5` without naming them is worse than useless,
because nobody will run the JSON query by hand.

The additional CI-specific need is **attribution of a problem to a
change**. "This build is 25% efficient" is a fact about a repository, not
about a pull request. "This pull request added `lib-g.bst`, which is
serialized behind `lib-f.bst` for no declared reason, and cost 4.1s of
critical path" is reviewable. That requires per-element diffing between
two runs — which elements are new, which changed duration, which changed
position relative to the critical path — and `bga compare` today reports
only aggregates (floors, categories, a verdict). This is the single
highest-value CI-specific addition, and it is a natural extension of
`UX-01`'s existing machinery rather than new analysis.

### 2c. Stop regressions — the part that needs a new metric

The requirement, in the build owner's own words: *adding new elements and
making the build slower is fine; adding them in an unoptimized way is
not.* There should be a level of inefficiency the owner considers normal,
and a large regression past it should stop the pipeline.

The current gate cannot express that, and was never meant to.
`--fail-on-regression` compares `total_duration_us` at a 1% threshold.
Measured against real runs (`UX-39`):

- **It fires on noise.** A pure capacity change on an unmodified source
  tree — `+1.19s` on a 28s build, `+4.3%` — exits 4.
- **It cannot allow legitimate growth.** Three new elements make the build
  slower; the gate fails; the only remedy is raising the threshold, which
  blinds it to everything else.
- **The tool's own efficiency numbers point the wrong way**, so gating on
  them instead would be worse than gating on duration: serializing the
  build *raises* `efficiency_score` to 1.00 and *lowers* headroom to zero.

And in practice the gate is frequently not running at all: it fails open
below 0.8 confidence, and real captures land at ~0.69 because BuildStream's
own startup is counted against `attribution_score`. The smaller the
project, the larger startup's share, the more likely the gate is silently
disabled — with nothing printed to say so (`UX-40`).

**The shape of the fix.** A gate on a ratio that is invariant to how much
work the build does. The candidate the audit data supports is work-vs-span:

```
occupancy_ratio = Σ task occupancy / (wall_clock × capacity)

  mis-optimized build:  40.25s / (39.57s × 4) = 25.4%
  optimized build:      61.45s / (27.50s × 4) = 55.9%
```

Add three well-parallelized elements and this barely moves. Add three
serialized ones and it drops sharply. That is exactly the discrimination
required, and it needs no data that is not already ingested. Its known
weakness must be stated rather than hidden: the numerator inflates under
contention, because the same work costs more occupancy when elements
overlap — which is why `UX-27` should settle the metric before `UX-39`
ships a gate on top of it, and why the honest long-run version measures
real CPU time from Plane 2 rather than slot occupancy.

Around that metric, three properties matter more than the exact formula:

1. **An absolute floor, not only a delta.** `--min-efficiency 0.45`
   expresses "we accept some inefficiency, we do not accept this much"
   without needing a trustworthy baseline. A delta gate alone ratchets: a
   slow drift of 2% per commit never trips it.
2. **Independent gates with distinct exit codes.** "Slower" and "less
   efficient" are different verdicts and different teams' problems. A
   pipeline should be able to warn on the first and fail on the second.
3. **A defensible threshold, derived rather than guessed.** 1% on
   wall-clock is below the noise floor of any real build. Whatever bar the
   efficiency gate takes should come from repeated captures of an
   unchanged project on the target runner. This is also the honest answer
   to noise generally — a single-baseline comparison will always be
   fragile, and multi-run baselining is the real fix, deliberately scoped
   out of `UX-39` so it does not silently become that task.

> **Done.** `--fail-on-efficiency-regression`/`--min-efficiency` ship on
> `occupancy_ratio` with their own exit code `5` (`UX-39`), and the
> confidence interaction that kept the gate from running is fixed
> (`UX-40`). All three properties below were implemented as argued; the
> default tolerance was derived from three repeat captures of an
> unchanged project (1.0pp of measured occupancy noise, against 7.4% of
> wall-clock noise on the same three - which is now measured evidence,
> not assertion, that the duration gate's 1% default sits below the noise
> floor). Multi-run baselining remains deliberately out of scope and is
> the most likely thing to force itself next.

### What a good CI comment should look like

```
Build efficiency: 52% occupancy (baseline 55%, floor 45%)  PASS
Wall-clock: 31.2s (baseline 27.5s, +13.5%)                 WARN - 2 new elements
New elements this change:
  lib-g.bst  2.9s  parallel with lib-a..f          ok
  lib-h.bst  4.1s  serialized behind lib-g.bst     <- 4.1s of new critical path
                   (declares a build dep on lib-g.bst; nothing in its
                    sandbox read lib-g.bst's output)
```

The first two lines need `UX-27` and `UX-39` - **both now shipped**, so
that half is buildable today. The element table needs 2b's per-element
diff, which is still open. The parenthetical needs Plane 2's sandbox-read
data - the declared-vs-used detection now named as candidate (1) for the
next round.

## Implementation status (updated 2026-08-16, round complete)

**All fourteen items of the `UX-27`..`UX-40` round are done.** What
follows below is the argument that produced them, kept because the
reasoning is still the reasoning - but several of its complaints are now
historical, and are marked where they are.

Four of the round's own filings were corrected during implementation
rather than implemented as written. That is worth more than the fixes
themselves as a signal about how the next round should be run:

- **`UX-28`'s evidence did not support its claim.** It cited an 81%
  per-element contention increase as proof the oversubscription check
  could not fire. The two runs were not comparable and the costlier one
  was 30.5% *faster* overall - beneficial parallelism, not harm. The real
  defect (a bar whose ratio-to-cores collapses as the host grows) was
  different, provable, and only found by checking the fix against
  `UX-09`'s existing measurements instead of against the intuition that
  produced the filing.
- **`UX-32`'s proposed headline metric was backwards.** Achieved-vs-requested
  scores a `-j1`-pinned element at 200% of what it asked for; being pinned
  *is* the problem.
- **`UX-30` and `UX-40` each carried a secondary claim that was already
  implemented** (monotonicity violations are shown; the fail-open does
  warn). Both were pinned by tests rather than "fixed".

The rate is roughly one filing in four. A round of audit findings written
from a single hands-on session should be treated as *hypotheses with
evidence attached*, not as a work list - and the cheapest way to catch
the bad ones is to re-check each against measurements the repo already
has before writing any code.

## What the next audit round should probe

The last round audited **what the tool says**. The obvious next targets
are the two things it still cannot say, and the two places its own claims
have never been tested:

1. **Declared-vs-used dependencies.** The over-declared `codegen.bst`
   build-dep in `examples/06` was the one problem in that project that no
   `bga` signal found - it was found by knowing the project. Plane 2
   already traces every process inside a `--dir`-tagged sandbox, so
   "which of this element's declared build deps did its sandbox never
   read?" is answerable in principle and would close the last macro-level
   gap. `UX-27`'s sketch 3, deliberately deferred.
2. **A real CPU measurement.** Every efficiency number in the tool is
   built on slot *occupancy*, and the honest caveat attached to
   `occupancy_ratio`, to the `UX-36` bucket labels, and to `UX-37`'s
   scoring is the same one: occupancy is not CPU time, and inflates under
   contention. `getrusage` in Plane 2's hook destructor would give real
   per-process CPU time and collapse three separate caveats into one
   measurement.
3. **Scale.** Every finding in the last round came from projects of 8-13
   elements on one 4-core host. `docs/tasks/P1-16`/`P1-21` did real
   performance work on large graphs, but no audit has walked a
   *thousand*-element project end to end and asked whether the report is
   still readable, whether the critical-path rendering `UX-33` added is
   still the right shape at that size, or whether `bga sweep`'s knee is
   still meaningful. Nor has anything been captured on a many-core host,
   where `UX-28`'s re-based threshold makes materially different calls
   than the old one did.
4. **Remote execution.** `UX-09` noted it and nothing has revisited it:
   with a remote-execution sandbox the compute happens on a worker pool
   whose size and scheduling are invisible to the local client, so
   `builders` - the denominator of `occupancy_ratio` and the basis of
   `LB` - stops meaning what the tool assumes. Whether `bga` should
   detect that mode and refuse to certify, or model it, is an open
   product question, not a bug.
5. **The CI story end to end.** `UX-39` shipped the gate; nobody has run
   a real pipeline against it for a week and found out what it feels like
   to own. The two things most likely to be wrong are the derived 5.0pp
   default (one project, one runner) and the absence of multi-run
   baselining, which `UX-39` scoped out explicitly and which a single
   noisy runner will eventually force.

A good next round would pick (1) or (2) as its centre - both are real
capability, not polish - and use a project a full order of magnitude
larger than `examples/06` as the vehicle, which would incidentally
exercise (3).

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

## What the third round found (2026-08-17)

The round opened with the backlog empty, so it ran the one probe the
previous round had listed and never executed: **cross-checking quantities
that are computed independently and ought to agree**. That single sweep -
eight pairs across four fixtures, a few minutes of work - found the
round's only defect, and it was a serious one.

### `UX-50`: the flagship answer was wrong on real runs

`sensitivity.critical_path_us` and `floors.t_infinity_observed` are the
same quantity computed two ways. On one real capture they differed by
**9 seconds**. The cause was a dict comprehension keyed on element UID
over a task list that has more than one task per element, so whichever
task arrived last won - and when that was the zero-duration `FETCH`, the
structural analyzer read the build's heaviest element as 0.00s and
dropped it from the improvement ranking entirely.

Three things about it are worth keeping:

- **It was data-order dependent** - 0 of 11 elements affected on two real
  captures, 2 of 11 on a third. Defects that strike some runs and not
  others are exactly what a single hand-checked example cannot find, and
  what a cross-check finds immediately.
- **`UX-44` verified against the run that happened to work.** The
  baseline's ordering favours `BUILD` for every element, so the ranking
  looked right. Verifying against more than one real capture would have
  caught it; verifying against the *fixed* project rather than the broken
  one would have caught it faster.
- **The synthetic scale fixture could not have found it.**
  `gen_synthetic_scale_run.py` emits one `BUILD` task per element, so the
  comprehension has nothing to collapse. Round 2 leaned on that fixture
  because it exposed what small projects hid; this is the converse. A
  real 11-element capture is the better fixture for this class, and both
  are needed.

### What else was probed, and found nothing

Recorded because a non-finding is worth the same as a finding when it
retires a worry:

- **The extended cross-check** (choke-point impact vs blast radius,
  attribution sum vs total duration, `T_C >= T∞`) found **zero**
  disagreements. Outside `StructuralAnalyzer` the published quantities
  are internally consistent.
- **`UX-46`'s per-process path budget**, chosen without evidence at 8192
  slots / 256 KiB, was measured against the real 822-process capture:
  median 8 unique paths per process, p90 93, **peak 149** - 1.8% of the
  budget, with zero drops. A 55x margin for a cmake/C++ toolchain, and
  the `dropped` counter exists to detect the case where it is not.

### The method that produced this round

Two rounds established that placeholders hide in comments; this round
established the complement. **A quantity computed twice is a free test.**
Nothing about `UX-50` required a large graph, a long build, or a
hypothesis about where to look - only the observation that two published
fields claim to be the same number. The eight pairs swept here are now
pinned as tests, and the sweep itself is worth re-running whenever a new
derived quantity is published.

## Ready for the fourth round

The backlog is empty. Everything filed across three audit
rounds is implemented and verified against real captures, so the next
round starts from a clean board rather than from a work queue. What that
round should probe, in the order I would pick:

1. **The seam between the two planes.** Still the biggest thing the
   tool cannot do, and it got *sharper* rather than smaller as Plane 2
   improved. `UX-45` measures real CPU time per element; `UX-27`'s
   `occupancy_ratio`, `UX-36`'s buckets and `I9` reconciliation all still
   say "this is slot occupancy, not CPU" - correctly, because the two
   planes cover different scopes of different runs. A user optimizing a
   real project still runs two tools over two captures and joins the
   answers by hand, which is exactly what `docs/optimization-walkthrough-06.md`
   records and what its closing note still says is open. Whether these
   should become one capture, or stay two with an explicit join, is a
   real product question and the most valuable one left.
2. **A real capture at scale** (item 6 above, unchanged). Now more
   pointed: `UX-46`'s open-interception runs on a hot path and has only
   been exercised on an 822-process build. Its per-process path budget is
   a fixed 8192 slots / 256 KiB, chosen without evidence, and a large
   real build is what would say whether that is generous or naive - the
   `dropped` counter exists precisely so this can be answered rather than
   guessed.
3. **A project whose elements genuinely consume each other.** `UX-46`'s
   true-negative evidence currently rests on `toolchain.bst` alone,
   because every cross-element dependency in `examples/06` turned out to
   be decorative. A fixture where element B really does `#include` A's
   staged header would let the unused-dependency detector be tested in
   both directions, and would incidentally make the macro walkthrough
   more representative of a real project.
4. **Remote execution** and **the CI story end to end** (items 4 and 5
   from the previous round) remain untouched and remain real.

### What two rounds of doing this taught, as method

Worth carrying into the third round, because both cost real time to
learn and neither is about any particular defect:

- **Byte-identical output is not proof of correctness.** `UX-42`'s
  rewrite matched all five real fixtures exactly, and an oracle test
  against a naive transcription of the original then found two genuine
  bugs. Where a change claims to preserve semantics, write the oracle.
- **A filed acceptance criterion is a hypothesis, not a specification.**
  Five of mine were wrong across the two rounds - `UX-48`'s "majority of
  idle", two of `UX-43`'s predicted choke points, and two of `UX-46`'s
  expectations about which dependencies `examples/06` really uses. In
  every case the measurement was right and the criterion was written
  before the measurement existed. Each is corrected in place in its own
  doc, with the reasoning, rather than quietly dropped.

## Suggested order (historical - all of these shipped)

Grouped by what unblocks what, not by size. Kept as written, because the
sequencing reasoning is reusable; every item named below is now done.

**First — turn on what already exists.** `UX-33` (name the critical path
and the choke points), `UX-34` (drop structural noise from the
what-to-fix list), `UX-29` (auto-extract `native_max_jobs`), `UX-28` (fix
the oversubscription threshold), `UX-35` (make the hints capacity-aware).
Each is small, each is independent, and together they change what a local
user sees from "a number I cannot act on" to "a named element I can go
edit". `UX-30` (the sweep knee point) belongs here too — it is small and
it currently gives an actively wrong answer.

**Second — settle the metric.** `UX-27`. Everything in 2c depends on it,
and shipping a CI gate on top of the current `efficiency_score` would
ratify a metric that points the wrong way. `UX-36` (say that the
occupancy block is occupancy) is a prerequisite in practice, since the
occupancy ratio is the leading candidate and its meaning has to be
correct where users read it.

**Third — the CI gate.** `UX-40` first (a gate that fails open on most
real runs cannot be evaluated), then `UX-39`, then 2b's per-element diff.

**Fourth — the micro level.** `UX-32` (per-element achieved parallelism)
is the highest-value Plane 2 work and stands alone. `UX-31` (capture
`notparallel`, the real per-element control) is its cheap Plane 1
counterpart. `UX-37` (redundancy findings scored in wall-clock, filtered,
readable) and `UX-38` (the tracer's artifact-confusion trap) are polish on
the same tool.

## Verification Log

Written 2026-08-16 from a real session: BuildStream 2.7.0 with
`buildstream-plugins`, real `bwrap` sandboxes, real `gcc 13`/`cmake 3.28`
staged by `examples/stage_cpp_toolchain.sh`, on a 4-core / 16GB Linux
host. Every number quoted is from a real build and a real `bga`
invocation in that session, recorded in
[`optimization-walkthrough-06.md`](optimization-walkthrough-06.md); every
claim about what the code does was checked against the source rather than
inferred from output. The proposed report and CI-comment layouts are
illustrations of intent, not implemented output.
