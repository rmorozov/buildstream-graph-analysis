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

The first two lines need `UX-27` and `UX-39`. The element table needs
2b's per-element diff. The parenthetical needs Plane 2's sandbox-read
data, which is the most speculative item here and the one worth doing
last.

## Implementation status (updated 2026-08-16, after the first phase)

Twelve of the fourteen items argued for below have shipped - every one
whose dependencies were already closed when the round was filed. The two
that remain are the two that were blocked on items in this same round:

- **`UX-35`** (capacity-blind hints) waited on `UX-28`/`UX-29` so it can
  consume their verdict rather than grow a second, independently-derived
  capacity formula - the divergence `UX-17` was resolved to avoid.
- **`UX-39`** (the inefficiency-ratio CI gate) waited on `UX-27` for a
  metric worth gating on and `UX-40` for a gate that actually runs. Both
  are now in place: `floors.occupancy_ratio` moved +35.2pp across the
  real optimization pair where every pre-existing metric was flat or
  backwards, and real captures now clear the confidence bar instead of
  silently failing open.

Two of the round's own filings were corrected during implementation
rather than implemented as written, and both corrections are recorded in
the tasks themselves: `UX-28`'s original evidence did not support its
claim (the real defect turned out to be different and provable), and
`UX-32`'s proposed headline metric would have scored the pinned element
at 200% of what it asked for - being pinned *was* the problem.

## Suggested order

Grouped by what unblocks what, not by size.

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
