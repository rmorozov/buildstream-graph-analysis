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

> **Done, and it landed closer to this section's own sketch than
> expected.** `UX-51`'s `bga correlate` joins the planes on element UID,
> and the sketch above was right that the missing piece was mechanical:
> the join key already existed on both sides and matched 9 of 9 elements
> with zero mismatches. What the sketch under-sold is the *negative*
> result - an element reported as already compute-bound tells a reader to
> stop looking inside it, which is as useful as being sent there. The
> real output on this project's own `core.bst` is one line:
> *"holds 25% of the critical path but runs at only 0.85 cores busy - it
> is waiting, not computing, and its native build asked for -j1"*.

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

## What the fourth round found (2026-08-17)

The round's centre was the **plane seam**, the previous round's own item
1, and it produced a design decision rather than a defect - which is what
that item was: an open product question, not a bug.

### The seam: settled by measurement, built as `UX-51`

The question was whether the planes should become one capture or stay two
with an explicit join. Three measurements decided it before any code was
written:

| question | measured answer |
|---|---|
| would a merged capture add anything? | **no** - `UX-24`'s `run --wrapped-log` already emits both artifacts from one `bst build` |
| does a join key exist, and is it exact? | **yes** - 9 of 9 Plane 2 elements matched Plane 1 UIDs, zero mismatches; the two that did not join run no build commands |
| can the horizons be merged at all? | **no** - `architecture.md`'s standing argument; a "merge" would be a join with a misleading name |

So the contract between the planes is one string, and `bga correlate` is
a third consumer neither plane knows about. The caveats that made this
look intractable - `UX-27`'s `occupancy_ratio`, `UX-36`'s buckets, `I9` -
were never in the way, because a join does not need them reconciled.

The thing worth carrying forward is *why the answer was cheap*: every
piece had been built for another reason (`UX-23` tagged processes to fix
a pid-collision bug; `UX-24` added dual capture for a Chrome Trace view),
and the seam turned out to be one join away rather than one architecture
away. **Before designing across a seam, measure what already crosses it.**

### `examples/07`, and closing an evidence gap I had flagged myself

`UX-46` shipped in round 2 with a caveat in its own doc: every
cross-element dependency in `examples/06` is decorative, so the only
true-negative evidence was `toolchain.bst`, and a detector that flagged
*everything* would have looked identical. Round 4's item 3 was to fix
that, and `examples/07-declared-vs-used-dependencies` does: two elements
with identical declared dependencies, differing only in whether their
source includes the header, correctly separated (`1/5` files opened
versus `0 of 5`).

Worth noting as method: this gap was found by the task's own author, in
the task's own doc, and would have stayed a footnote if the doc had not
been written to say what the evidence *could not* show. A caveat you
write about your own work is only useful if something later reads it.

### The cross-check sweep, re-run

Round 3's sweep is now a standing check. Across five runs - three real
captures, the new dual capture, and the synthetic scale fixture - **40 of
40 quantity pairs agree**, up from 22 of 24 when the sweep first ran. It
costs seconds and it has already caught one serious defect (`UX-50`), so
it is worth re-running whenever a derived quantity is added.

## What the fifth round found (2026-08-17)

The round pointed `bga` at a **real, well-maintained BuildStream project**
for the first time - `freedesktop-sdk`, 1089 elements - rather than a
purpose-built example. Deliberately in baby steps: shallow clone, `bst
show` a small closure, no attempt to build the distribution.

### What worked immediately

Real graph ingestion. `tools/bst_show_to_graph.py` handled
`components/zlib.bst`'s full closure without complaint: **85 elements,
502 dependencies, 9 distinct element kinds**. The graph-only signals then
read sensibly on it - 5 choke points out of 85 (`UX-43`'s definition
holding up on real structure), max depth 27, 7 stack-consolidation
candidates, and a parallelism profile of min 1.0x / avg 2.7x / max 15.0x.

### `UX-52`: a real project's dependency types broke the structural plane

The cross-check sweep disagreed on its first real graph. `runtime`-only
edges - which do not gate build scheduling - were being counted as
gating by the structural plane, inflating its critical path from 28
elements to 32 and skewing every graph-shape signal derived from it,
including the improvement ranking.

The rule was already written down, in detail, in
`build_element_graph`'s own docstring, and two of its three callers
applied it. This is the same shape as `UX-41`.

**Why four previous rounds could not find it:** the real subgraph has 27
runtime edges among 502. *Every fixture in this repository had zero* -
the hand-written examples use `type: build` throughout, and the synthetic
1202-element generator emitted `"build"` unconditionally. Scale did not
help, because the generator was written by the same hand as the analyzer
and reproduced only the dependency type the analyzer already handled.

That is the round's real lesson, and it is sharper than round 3's
fixture-shape one:

> **A fixture written alongside the analyzer tends to contain only the
> cases the analyzer already handles.** Real projects are not just bigger
> or messier - they are *differently shaped*, in ways the author of a
> fixture has no reason to invent.

Both gaps are now closed: the scale generator emits a realistic minority
of runtime edges, and six new tests give the suite a runtime edge for the
first time.

### What a real project could not give us here, and why

Building `freedesktop-sdk` is **blocked in this environment** by network
policy, not by anything about `bga`: the bootstrap needs a 238MB binary
seed from `cdn.registry.gitlab-static.net`, and the agent proxy answers
403 to CONNECT for that host. Chasing it would have been exactly the
"forever building an OS" this round was scoped to avoid.

So round 5's findings are all graph-only, and are labelled as such - no
timing claim in this round rests on the synthetic trace that was paired
with the real graph to get it through the pipeline. What remains untested
against a real project: attribution, floors, occupancy, both efficiency
signals, and the whole of Plane 2.

## What the sixth round found (2026-08-17)

The round set out to do the one thing the fifth named as most valuable —
capture a **real timeline** from a real project, not just a real graph.
It ended up finding two defects that had nothing to do with scale and one
piece of infrastructure the project needed all along.

### Getting a real project to build at all

`freedesktop-sdk` cannot be built from the container this repository is
worked on from, and this was established rather than assumed. Two
independent blocks, both network policy:

- its bootstrap seed is a 238MB OCI image on
  `cdn.registry.gitlab-static.net`, which the egress proxy refuses with
  `403` to `CONNECT` (the registry API host itself answers normally, so
  it is specifically the blob CDN);
- its own artifact/source cache at `cache.freedesktop-sdk.io:11001`
  accepts the `CONNECT` and then resets the TLS handshake.

Nothing in the project avoids this: the only elements with no
dependencies at all are config/import elements that perform no build
work.

So the capture moved to a GitHub-hosted runner
(`.github/workflows/real-project-capture.yml`), and the method is worth
recording because both obvious approaches fail in opposite directions.
Building from source is a full compiler bootstrap and does not fit a CI
job; building with the project's own artifact cache enabled produces a
timeline in which *nothing was built*, only pulled. The workflow does
both: **warm** the local cache from the project's remote, **cut** a
bounded subgraph's artifacts, then **capture** a rebuild with remotes
ignored, so exactly that subgraph builds from source on top of a cached
base with its real dependencies, parallelism and durations.

The cut set cannot be arbitrary, and this is the part that is easy to get
silently wrong: BuildStream builds an element when *its own* artifact is
missing, so a cached dependent is never rebuilt and never asks for its
dependencies at all. The delete set has to be **upward-closed** over
build edges, up to and including the requested target, or the build stops
short of it and the capture is empty. `tools/bst_rebuild_set.py` computes
that closure from the same `graph.json` the graph extractor already
produces.

Three iterations of that workflow each taught something, and each is
recorded in its commit:

1. `bst build` is the wrong verb for the warm phase — it finished in
   **7 seconds**, because when the target's artifact is already in the
   remote there is nothing to build and therefore nothing to pull. The
   101 dependencies stayed uncached. `bst artifact pull --deps all` asks
   for the closure explicitly. A guard now asserts that the set
   BuildStream considers un-built after the cut is *exactly* the set that
   was deleted, before anything expensive starts — because the failure
   mode's only symptom was a job that times out two hours later for an
   unrelated-looking reason.
2. Workflow artifacts are served from `*.blob.core.windows.net`, which
   the same egress policy blocks — so the obvious way to get a capture
   out of CI does not work from here. The capture is also pushed to a
   branch, which has the better property anyway: a capture becomes a
   versioned, fetchable object rather than something that expires in
   fourteen days.
3. The build died on every element with `bwrap: loopback: Failed
   RTM_NEWADDR: Operation not permitted`, and the honest response was to
   *measure* rather than guess whether the Plane 2 PATH shim was
   responsible. The workflow now retries a failed traced build **without**
   the tracer; both failed identically, which exonerated the tooling and
   pointed at Ubuntu 24.04's
   `kernel.apparmor_restrict_unprivileged_userns=1`.

### `UX-53`: two duration definitions, found on a fixture that predates round 1

The cross-check sweep — written from scratch at the start of every round
since the third, and now checked in as `tools/bga_cross_check.py`
precisely because it has found something every time it was pointed
somewhere new — was aimed at `tests/fixtures/synthetic_multi_subproject`
for the first time, and disagreed:

```
structural.sensitivity.critical_path_us   144500000
floors.t_infinity_observed                118000000
```

`UX-52`'s acceptance criterion states in as many words that those two
must be equal. They were 22% apart, and in the *unsafe* direction for a
quantity Part 14.1 certifies as a floor. The gap is exactly the FETCH and
TRACK time along the critical path (20.0s + 6.5s), because `UX-50` had
built a *second* per-element duration map by summing an element's tasks,
while `analyze_graph` — three hundred lines away — already took their
maximum.

The lesson is now three rounds old and getting sharper each time. `UX-50`
was about fixture *durations*, `UX-52` about fixture *dependency types*,
and this one about **tasks per element**: every fixture that pinned this
invariant gives each element exactly one task, where max and sum
coincide, so both `UX-50` and `UX-52` tested it and neither could fail.
What is new is that the fixture with the right shape *was already in the
repository*. Nothing had ever pointed the sweep at it. The scarce
resource was not data, it was attention.

### `UX-54`: a failed build scores 1.00, and the CI gate lets it through

The capture that finally came back was of a build in which **all four
attempted elements failed** — and `bga` reported `Efficiency Score:
1.00`, never using the word "failed". A build that dies early looks, to a
scheduling model, exactly like a build with nothing left to optimize.

Following that through the CI gate this project exists to support:
efficiency 1.00, confidence 0.14, and `_compare_exit_code` **fails open**
on low confidence by design (`UX-40`). A broken build passes the gate on
scheduling grounds. The fail-open rule is right for a *noisy* signal; a
build that did not complete is a definite fact, and needs the opposite
treatment.

The status was never missing — BuildStream states it, and
`bst_log_to_chrome_trace.py` already carried it into the chrome trace's
End events. It was dropped at the last hop, and **no fixture in this
repository contains a failed task**, so nothing could notice. It took a
real project on a machine where the sandbox did not work.

That is the round's most transferable result: a capture nobody wanted
was the only one that could show it. Every example project here is
written to build cleanly, which means the entire failure axis of the tool
was untested by construction.

### The capture that finally worked

With the sandbox knob cleared, the run went through: **2,801.9 seconds
(46.7 minutes)**, 25 elements rebuilt from source on top of a 101-element
cached base, 12 element kinds, 36 runtime edges, **127,630 traced
processes** in Plane 2 — 155× the largest capture it had ever seen.

What held up, on real data, is worth stating as plainly as what did not:

- **Every cross-check agrees, 8 of 8.** `UX-52`'s runtime-edge gating and
  `UX-53`'s single duration definition both hold on a real project:
  `sensitivity.critical_path_us == t_infinity_observed == 2,796.85s`, and
  an independent longest-weighted-path pass over the raw trace reproduces
  it exactly.
- **`UX-27`'s two-signal design is vindicated by a real build.**
  `Efficiency Score 1.00` alongside `Dispatch Occupancy 33.6%` is not a
  contradiction, it is the point: `T∞` is 2,796.85s of a 2,801.9s
  makespan, so the build genuinely *is* a serial chain
  (`openssl` 487s → `cmake-stage1` **1,226s** → `python3` 496s →
  `bison` → `doxygen` 389s → `libxml2`) and the scheduler has nothing
  left to give. One number says "the scheduler is done", the other says
  "the graph is the problem", and only having both makes that legible.
- **Plane 2 survived the scale.** 127,630 processes, `getrusage` CPU time
  for 119,590 of them (93.7% coverage), no crash, no corruption.

And two things it measured about itself:

- **The hook's fixed per-process path budget is naive at this scale.**
  Round 5 recorded it as "8192 slots / 256 KiB, chosen without evidence"
  and said a large real build was what would settle it. Settled:
  **149,053 dropped paths against 65,101 recorded**, a 70% drop rate. The
  `dropped` counter existing is what let this be answered rather than
  guessed, which is the design working as intended.
- **`UX-56`**: 99.4% of those processes were tagged with
  `buildstream-build`, `freedesktop-sdk`'s build root, because the
  element tag comes from bwrap's `--dir` — the element only under
  BuildStream's *default* build-root layout. Every per-element Plane 2
  figure became a whole-build figure wearing an element's name, and
  `bga correlate`'s join key was not an element UID at all.

And one that only a real *cache* could show — **`UX-55`**: 101 of the 126
elements were cached, and `bga` reports a cached critical-path element as
"no matching task found - genuine coverage gap, worth investigating",
failing a hard gate. That drives confidence down, which makes
`UX-03`/`UX-39`'s regression gate fail open. The better the cache works —
the entire point of BuildStream — the less `bga` gates. That is the CI
story's real blocker, and no fixture could contain it: every fixture here
is a full build in which nothing is cached.

## What blocks another real-sample round: nothing, and one habit

Asked directly before round 7 was planned, and worth recording because
the answer is not "get a capture" any more:

- **The capture is on demand.** `.github/workflows/real-project-capture.yml`
  warms, cuts and captures a real `freedesktop-sdk` build and publishes
  it to `captures/fdsdk-latest`, which is fetchable from here. The
  workflow-artifact route is not (the egress policy refuses
  `*.blob.core.windows.net`), which is why the branch exists.
- **One artifact is missing, and it is not a budget problem.** `UX-56`
  guessed that the raw trace being dropped above 40MB is why round 6 had
  no bwrap argv to settle the element-tag question with. It is not: the
  shim never records the argv at all (`UX-58`). That is a few lines, and
  it unblocks `UX-56`, which in turn unblocks declared-vs-used on real
  projects - which returned entirely empty on the real capture for the
  same reason.

The habit is the more useful finding. Round 6 spent **two CI iterations**
rediscovering that Ubuntu 24.04's
`kernel.apparmor_restrict_unprivileged_userns` stops bwrap bringing up
loopback - a failure this repository's own `.github/workflows/ci.yml`
already carried a named step for, with the root cause, the upstream
issue references and the exact `sysctl` fix in a comment. The capture
workflow was written from scratch beside a file that had solved its
hardest environmental problem months earlier.

That is the same shape as `UX-53` (the fixture with the right shape was
already checked in) and `UX-41`/`UX-52` (the rule was already written
down in the code that ignored it). Three rounds running, the scarce
resource has not been evidence. **Before building capture
infrastructure, read what the repository already runs.**

### Six deferrals that were never filed

A sweep of every `## Out of Scope` section across 121 task docs, checking
each against the backlog, found six items that were deferred with a
reason and then never became scope: `UX-58` (argv), `UX-59` (no noise
model for the pre-commit scenario, deferred verbatim by `UX-39` as
"probably necessary"), `UX-60` (FETCH in efficiency signals, deferred
identically by `UX-50` and `UX-53`), `UX-61` (`max_concurrency` of 5,268
on four cores), `UX-62` (per-span terminal status), and `UX-63` (measured
per-task memory, whose stated blocker shipped two rounds ago).

The process mostly works - `UX-12`'s per-element `max-jobs` deferral
became `UX-22` and `UX-31`, `UX-36`'s CPU-accounting deferral became
`UX-45`, and `UX-03`'s "wire the gate into this repo's own CI" is live in
`ci.yml`. What the six have in common is that each was deferred by a task
that *shipped successfully*: nothing failed afterwards to make anyone
look again. A deferral inside a green task is invisible.

## Ready for the seventh round

The backlog is **not** empty for the first time in three rounds, and
that is the honest state: round 6 filed `UX-55` (open) and left `UX-56`'s
real fix open behind a guard. Both need another real capture to settle,
not more thinking. The order I would pick:

0. **`UX-55` first, before anything else.** It is the one finding that
   blocks the product's stated purpose rather than a number's accuracy:
   on an incremental build — which is every CI build — a cached element
   reads as a lost measurement, the coverage hard gate fails, confidence
   drops, and the regression gate fails open. Everything else in this
   list is improvement; this one is the difference between the CI story
   working and not.
0b. **`UX-56`'s real fix**, which needs one thing round 6 could not
   keep: a real captured bwrap argv. The raw trace exceeded the tarball
   budget and was dropped, so the next capture should keep a *sample* of
   it (the first N invocations) rather than all or nothing.
0c. **The hook's path budget**, now measured at a **70% drop rate** on a
   real build. No longer a design question, just a number to raise — and
   worth raising before the next Plane 2 measurement, since a truncated
   read set is exactly what `UX-46` refuses to draw conclusions from.

Then, from the previous round's list:

1. ~~**The seam between the two planes.**~~ **Settled and built** as
   `UX-51`: `bga correlate` joins the planes on element UID. The product
   question - one merged capture, or two with an explicit join - was
   decided by measuring three things rather than arguing them: one
   capture already yields both artifacts (`UX-24`), the join key matched
   9 of 9 elements with zero mismatches on a real dual capture, and the
   horizons provably cannot be merged. So the contract between the planes
   is one string, and each stays independently replaceable. The caveats
   that made this look intractable were never in the way: `UX-27`'s
   `occupancy_ratio` and `UX-36`'s buckets still correctly say "slot
   occupancy, not CPU", because a join does not need them reconciled.
2. ~~**A real capture at scale.**~~ **Done** in round 6, and it paid for
   itself three times over. `.github/workflows/real-project-capture.yml`
   produces one on demand — 2,801.9s of real `freedesktop-sdk` build,
   127,630 traced processes — and publishes it to a branch, so a capture
   is now a fetchable object rather than a thing that has to be arranged.
   The open question it *answered*: the hook's fixed 8192-slot / 256 KiB
   per-process path budget, which round 5 called "chosen without
   evidence", drops **70% of observed opens** at this scale. The `dropped`
   counter existing is what made that a measurement rather than a guess.
   What remains is not "get a real capture" but **use it as a regression
   fixture**: the run directory is small (5.6 KB of trace over a
   126-element graph) and is the only artifact here containing a
   partially-cached build, several element kinds and runtime edges at
   once.
3. ~~**A project whose elements genuinely consume each other.**~~
   **Done** as `examples/07-declared-vs-used-dependencies`: `user.bst`
   and `unrelated.bst` declare identical dependencies and differ only in
   whether their source includes the header, and `UX-46` separates them
   correctly (1 of 5 staged files opened, versus 0 of 5). The
   true-negative evidence no longer rests on `toolchain.bst` alone.
4. **Remote execution** and **the CI story end to end** (items 4 and 5
   from the previous round) remain untouched and remain real.

### What four rounds of doing this taught, as method

None of these is about a particular defect, and each cost real time to
learn:

- **Byte-identical output is not proof of correctness.** `UX-42`'s
  rewrite matched all five real fixtures exactly, and an oracle test
  against a naive transcription of the original then found two genuine
  bugs. Where a change claims to preserve semantics, write the oracle.
- **A filed acceptance criterion is a hypothesis, not a specification.**
  Five of mine were wrong across the first two rounds - `UX-48`'s
  "majority of idle", two of `UX-43`'s predicted choke points, and two of
  `UX-46`'s expectations about which dependencies `examples/06` really
  uses. In every case the measurement was right and the criterion was
  written before the measurement existed. Each is corrected in place in
  its own doc, with the reasoning, rather than quietly dropped.
- **A quantity computed twice is a free test** (round 3). `UX-50` needed
  no large graph, no long build and no hypothesis about where to look -
  only the observation that two published fields claim to be the same
  number. The sweep is now standing, and runs 40/40 across five runs.
- **Fixture shape matters as much as fixture size** (round 3). The
  synthetic 1202-element fixture *structurally could not* exhibit
  `UX-50`, because it emits one task per element while a real capture has
  two. Round 2's lesson was that small projects hide defects; round 3's
  is the converse, and both fixtures are needed.
- **Before designing across a seam, measure what already crosses it**
  (round 4). The plane join looked like an architecture question and was
  one join away: the key already existed, the dual capture already
  existed, and both had been built for unrelated reasons.
- **A caveat you write about your own work is only useful if something
  later reads it** (round 4). `UX-46` recorded that its own true-negative
  evidence was thin; `examples/07` exists because that sentence was read
  two rounds later.

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

## The tenth round: the two usage scenarios, re-argued (2026-08-18)

Round 10 ([`audit-round-10.md`](audit-round-10.md), filings
`UX-77`..`UX-92`) walked both scenarios end to end in a fresh
environment — the full macro→micro cycle on `examples/06` with real
dual-plane captures (**27.9s → 25.0s → 16.9s**), a real growth
experiment against both CI gates, and the fdsdk capture infrastructure.
What follows is the state of each scenario after that walk, and where
each should go next. The one-line version: **the analysis has crossed
the MVP bar in both scenarios; what remains between the tool and its
users is packaging, synthesis, and data supply — in that order.**

### Scenario 1: the local optimization helper

The loop works, and this round is the first time a full cycle was run
by following only the documentation — which is how it found that the
documented entry point crashes on install (`UX-77`) and that the
documented capture omits the flag the join needs on real projects
(`UX-80`). Both are plumbing. Fix them first; nothing else in this
scenario matters to a user who never gets past the first command.

Past the front door, the round's experience says the helper's next
frontier is **synthesis, not measurement**. Every fact of the
walkthrough's macro problem was measured — the chain on the critical
path, every chain edge individually never-read — and the conclusion was
left to the user (`UX-82`). The two planes disagreed about what to do
next on the same capture, and nothing arbitrated (`UX-83`). The measure
→ conclude gap is now the defining gap of the local scenario, and the
round's sharpest evidence for it is reflexive: the tool's own evidence,
taken seriously, improves on the walkthrough example's own "optimized"
answer (six decorative edges retained on the heaviest element). A tool
that can out-reason its own gold standard but doesn't say so out loud
is exactly one synthesis pass short of its value.

### Scenario 2: the CI tool

Three sub-jobs, re-verdicted on this round's evidence:

- **Gather analytics: works, has nowhere to put anything.** The JSON
  contract is real (findings ids, stable fields, verified). But the
  capture infrastructure force-pushes over its own history (`UX-81`),
  has no schedule, and burned 17 of 24 runs on push-cancellations
  (`UX-90`). Analytics need a time series; today the pipeline keeps
  exactly one point. This is entirely infrastructure work and it gates
  everything below.

- **Highlight problems: blocked on the per-element diff.** Unchanged
  verdict from round 1's 2b, now with sharper evidence: the growth
  experiment produced runs where the *right* CI comment is obvious
  ("`lib-h.bst`: serialized behind `lib-g.bst`, +4.1s of critical
  path, declared dep never read") and every ingredient exists — new
  elements are identifiable from the two graphs, their path deltas
  from `UX-74`'s machinery, the never-read evidence from `UX-46`. It
  is still unassembled.

- **Stop regressions: right gate, wrong denominator.** The round's
  growth experiment is the strongest validation the efficiency gate
  has ever had — it passed legitimate growth (+4.7% wall-clock, gate
  green) and failed the same growth done badly, exactly the build
  owner's stated rule. It is also the strongest indictment: the worst
  possible two-element crime scored 6.1pp against a 5.0pp default in
  an 11-element project, and dilutes below 1pp at fdsdk scale
  (`UX-79`). A whole-build average can never express "the *new* work
  is inefficient" on a large project. The gate the rule needs is
  marginal — the inefficiency of the diff — with the whole-build gate
  kept for global serialization regressions. Until `UX-79` and
  `UX-81` (the ≥3-run baseline the band gate already requires) land,
  the honest advice to a CI owner is: gate on
  `--fail-on-efficiency-regression` for repositories under ~20
  elements, treat it as advisory above that, and never gate on
  Efficiency Score (this round: build 39% faster, score 1.00 → 0.79,
  monotonically).

Two hardening items apply to any gate that ships: a gate must say when
it did not run (`UX-87`), and a comparison of the wrong two runs must
refuse rather than verdict (`UX-78`).

### The next capability rounds: what the tool could see that it doesn't

Brainstormed against this round's evidence and filed where concrete:

1. **BuildStream's own cached logs as a third plane** (`UX-91`).
   Everything `bga` reads today requires deciding to capture *before*
   building. BuildStream already persists a timestamped per-element log
   for every artifact on every machine. That is the only path to
   retrospective analysis ("what did last night's unwrapped build
   do?"), longitudinal per-element trends, per-phase
   (configure/compile/install) splits with zero capture overhead, and
   frequency analysis of repeated operations across *builds* rather
   than within one. It composes with, not replaces, the wrapper — the
   certified floors keep requiring a real capture.

2. **Cache effectiveness as a first-class analysis** (`UX-92`). For
   the incremental builds that are every CI build, the cache is the
   dominant efficiency mechanism and the tool's entire cache story is
   "stop miscounting cached elements" (`UX-55`). Hit ratios per run
   and subtree, pull-vs-rebuild economics, trends over `UX-81`'s
   history — and above all **cache-key churn detection**: an element
   that rebuilds while its declared inputs are unchanged is plausibly
   BuildStream's largest real-world waste, is pure set arithmetic over
   data already in `graph.json` across two runs, and is invisible to
   every occupancy-based signal (a churning build can score as
   perfectly efficient). If one item in this list becomes the next
   `UX-45`-class capability, it should be this one.

3. **Timestamp/operation correlation heuristics** across those logs —
   the cheap approximations of Plane 2's redundancy findings
   (recurring identical operations across elements and builds) for
   environments where the tracer can't run. Folded into `UX-91`'s
   scope rather than filed separately; measure the persisted logs'
   timestamp quality first (`UX-06`'s lesson applies).

4. Further out, in the order the evidence suggests: the marginal gate's
   successor metric (per-element CPU stretch from Plane 2's `getrusage`
   data, once Plane 2 runs in CI routinely); remote execution (round
   1's item 4, still untouched, still real); and a many-core host
   capture (every number in ten rounds is from 4 cores).
