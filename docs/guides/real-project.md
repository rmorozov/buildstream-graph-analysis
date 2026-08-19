# Using `bga` on a real project, end to end

This is the long-form walkthrough: from a project you have never traced
before to a ranked, evidenced list of what to change — and how to tell
which of the tool's answers you can act on and which you cannot.

Every output below is **real**, from a capture of
[`freedesktop-sdk`](https://gitlab.com/freedesktop-sdk/freedesktop-sdk)
at `953683fb` on a 4-core GitHub Actions runner with `--builders 4
--max-jobs 4` — a 3614-second build of 90 elements, 25 of which rebuilt.
Nothing here is illustrative or reconstructed. Provenance for every
figure is in [Appendix: where these numbers came from](#appendix-where-these-numbers-came-from).

If you want the 30-second version first, the top of
[`README.md`](../../README.md) runs against a checked-in fixture and needs
no BuildStream at all.

---

## What you get, and what it costs

| step | what it answers | needs a live `bst`? |
|---|---|---|
| 0. `bga cache-logs` | What has this project been spending time on already | no — **and no capture either** |
| 1–2. Capture and extract | — | **yes** |
| 3. `bga analyze` | Where is the time, what is worth fixing, and what after that | no |
| 4. Floors and the two efficiency signals | Is this a scheduler problem, a graph problem, or a work problem | no |
| 5. `bga capture report` | Inside one element, what was it actually doing | no (the capture needed one) |
| 6. `bga correlate` | Which of those inside-facts matter, ranked by whole-build impact | no |
| 7. `bga compare` | Did my change actually help | no |

Steps 3–7 read finished artifacts. You can capture on a build machine
and analyse anywhere, including from a tarball someone hands you.

Step 0 is different from all of them: it reads logs BuildStream already
wrote, for builds that already happened. If you have ever built this
project on this machine, you can run it right now, before reading any
further.

---

## Step 0a — the evidence you already have (Plane 3)

Before capturing anything, look at what BuildStream kept. It writes a log
for every element it builds, under
`$XDG_CACHE_HOME/buildstream/logs/<project>/`, and never reads them
again:

```bash
bga cache-logs --project <your-project-name>
```

Real output, from a freedesktop-sdk log tree:

```text
Sandbox tax: 13.0s of 4409.0s element time (0.3%) across 23 build log(s) went to
staging, integrating and caching rather than to the build itself
  Who paid it (by toll seconds, not by share):
    components/libffi.bst                4.0s toll of 49.0s (8%)
    components/bison.bst                 3.0s toll of 137.0s (2%)

Configure tax (Plane 3, self-reported): 35.5s of 4409.0s element time (0.8%),
reported by 3 of 23 build log(s)
  5 element(s) have traced configure work and no self-report - an autotools or
  meson build system, and the case the self-report alone is blind to
```

**What to do with it.** Three questions it answers that no capture can:

- *Is any element paying more to be an element than to build?* That is
  the sandbox tax. A high toll share on a short element is the signal
  behind the `merge-candidate` finding — pass the JSON to
  `bga correlate --cache-logs` and it will say so with the Plane 1 impact
  attached.
- *Which elements does this project keep rebuilding?* The developer-tax
  ranking, across every build in the tree rather than the one you
  happened to capture.
- *Where does configure time go?* With `--native-report PLANE2.json` it
  puts the build tool's own self-reported figure beside Plane 2's traced
  CPU, per element, side by side and never summed.

**What it costs, and the report says all of it:** one-second resolution,
no scheduler context, no `--builders`, no per-command timing, and no
session id — so "how many builds" is a lower bound taken from the
most-rebuilt element, never a count. Nothing here may feed a certified
floor.

---

## Step 0 — prerequisites

```bash
pip install -e ".[bst]"
```

Plane 1 (the whole-project analysis) needs only Python. Plane 2 — the
tracer that looks *inside* an element's sandbox — needs a real `bst` and
a working `bubblewrap`, because it captures by injecting an `LD_PRELOAD`
hook into the processes the sandbox execs. See
[`docs/spec/ingestion-pipeline.md`](../spec/ingestion-pipeline.md) for the full
dependency list and its known limits.

Two limits worth knowing before you start, because they shape what you
can conclude:

- **Statically-linked processes are invisible** to the `LD_PRELOAD`
  mechanism — a static binary never invokes the dynamic linker, so
  nothing loads the hook. Two things now measure that gap instead of
  disclaiming it. `bga capture census PROJECT` scans the staged sandbox
  roots and says which elements stage a static executable at all
  (`UX-105`), and `bga capture run --trace-spine` runs a ptrace
  process-event tracer inside the sandbox that records every process
  whatever its linkage (`UX-106`). With the spine on, each process in
  the report carries `spine+hook`, `spine-only` or `hook-only`, and the
  report states the coverage as a number rather than a footnote
  (`UX-107`).
- **The spine is opt-in, and the reason is measured.** On
  `examples/06-macro-micro-optimization` it costs **+2.7%** wall over ten
  runs per mode, and on `examples/08-process-storm` — 575 processes per
  second, built to be the worst case — **+13.5%**. Both are past the 2%
  budget `UX-106` set for defaulting it on, so it stays a flag. Turn it
  on when coverage matters more than 3-13% of the build: a static
  toolchain, a busybox sandbox, or any report whose process list looks
  suspiciously short.
- **Plane 2 costs real overhead.** `--trace-opens` in particular runs on
  a hot path. Capture it deliberately, not by default.

---

## Step 1 — capture both planes from one build

One `bst build` produces both artifacts. Do not run two builds: the
second would be a different build, and joining the planes across two
builds silently correlates one build's sandboxes against another's
timeline.

```bash
bga capture run \
    --wrapped-log /tmp/plane1.log \
    --trace-opens \
    /path/to/your/project /tmp/plane2.json \
    -- bst build <your-target>
```

- `--wrapped-log` writes the Plane 1 log **and** records the real `bst`
  invocation on its own first line. That first line is where
  `--max-jobs` lives; without it, `bga`'s capacity checks have nothing to
  check against, and they say so rather than passing silently.
- `--trace-opens` enables the declared-vs-used analysis in step 5. Skip
  it if you only want timing.

**Which build to capture matters more than anything else in this guide.**
There are two CI scenarios and they answer different questions:

| scenario | what it measures | how to capture |
|---|---|---|
| **nightly, caches off** | the project's *real* critical path | drop the cache dir / use a fresh cache before building |
| **pre-commit, caches on** | the handful of elements your change rebuilt | build normally on a warm cache |

The capture below is the second kind, and `bga` says so before any
number, because it changes what those numbers are *about*:

```text
Incremental run (caches on): BuildStream skipped elements it had already built,
2 of them on the critical path. Coverage and the floors below describe the work
this run actually did, not the whole project - compare against another
incremental run, not against a caches-off nightly
```

If you compare an incremental run against a caches-off one, `bga compare`
refuses (exit 6) rather than producing a meaningless delta.

## Step 2 — turn the log into a run directory

```bash
bga extract --format wrapped /path/to/your/project /tmp/plane1.log /tmp/run
```

That writes `/tmp/run/{graph.json,trace.json,run-context.json}` — the
three files everything downstream reads. Archive this directory: it is
small, it is the input to every later comparison, and re-capturing it
costs you another full build.

---

## Step 3 — read the headline

```bash
bga analyze /tmp/run
```

Real output, top of the report:

```text
Key Findings:
  Incremental run (caches on): BuildStream skipped elements it had already built, 2 of them on the critical path...
  Confidence: 1.00 (high)
  Biggest Opportunity: this build is execution-bound - no wait category exceeds 1% of wall-clock time, so there is no scheduling gap to close
  Where the time is: 4 element(s) are 94.0% of the 3610.5s critical path - this build is chain-bound, not scheduler-bound
    components/_private/cmake-stage1.bst    1569.8s (43.5% of path)  -> fixing it saves 1569.8s (43.4% of the build)
    components/openssl.bst                   672.1s (18.6% of path)  -> fixing it saves 522.5s (14.5% of the build)
    components/python3.bst                   639.8s (17.7% of path)  -> fixing it saves 114.1s (3.2% of the build)
    components/doxygen.bst                   513.5s (14.2% of path)  -> fixing it saves 513.5s (14.2% of the build)
    -> these elements must get faster, or come off the chain; the scheduler has no room left to give
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so savings on one element are often capped by the next chain rather than by its own duration
  Together, the top 3 are worth 2605.8s (72% of the build) - exactly the sum of their individual savings, so they are three separate pieces of work that do not overlap
  Work them in this order (by what a fix is worth, not by size), with what the build drops to: components/_private/cmake-stage1.bst (2041s) -> components/openssl.bst (1518s) -> components/doxygen.bst (1005s)
    - the last of those leaves 72% of the build removed, projected from this run without building again
  Waiting off the critical path, worth nothing to fix today: components/_private/git-minimal.bst (548s), components/icu.bst (431s) (+2 more) - they bound how far shortening the chain can go
    (structural projections over this run's measured durations, where "fixed" means the element becomes instant - a re-capture is still the ground truth)
  Efficiency Score: 1.00 (...)
```

### How to read it, line by line

**`Confidence` first, always.** Below "high", stop and fix the capture —
every number under it describes a trace with known gaps. A failed build
is called out even louder, before any efficiency figure, because
otherwise a build where four elements failed reports a perfect score.

**`Biggest Opportunity` tells you which *kind* of problem you have.** It
names the largest non-execution category — dependency wait, resource
wait, scheduler wait, idle, retries. Here it names none of them, because
99.9% of the time went into execution. That is a real finding and the
most common one on a serious project: *there is no scheduling gap to
close; the work itself is the cost.*

**The table is two questions at once, and they disagree.** Rows are
ordered by **duration** — that is what "where is the time" means. The
right-hand column is what a fix is actually *worth*, and on a dense graph
it is a different number: `python3.bst` is the third-largest element on
the chain at 17.7%, and making it instant would save **3.2%** of the
build, because a near-tie chain takes over the moment it shrinks. If you
only had the share column you would have spent a week for a minute.

**The `zero slack` note tells you whether the top row is even
meaningful.** 77% of elements with zero slack means this is a mesh of
near-equal chains, not one dominant chain. On a mesh, a single element's
saving is usually capped by the next chain rather than by its own size —
which is exactly what the right-hand column is measuring.

**"Together, the top 3 are worth …"** is the sentence to plan around.
Whether savings *add* is a property of your graph, simulated rather than
assumed: two links of one chain compose, two parallel branches take a
maximum. Here they add exactly, which means the three are independent
pieces of work — three people can take one each and the results still sum
to 72%.

**"Work them in this order … with what the build drops to"** is the
horizon. Without it, finding the second thing to fix costs another full
build; the projection is a handful of longest-path recomputations over
data you already have (17 ms on this 126-element graph).

**"Waiting off the critical path"** are the elements every ranking is
right to place last and that you still need to know about.
`git-minimal.bst` is the **fourth-heaviest element in this entire build**
and is worth nothing to fix today. It is the floor your chain-shortening
is heading towards.

> **What this block is not.** Everything after "Together, the top 3…" is
> a structural projection over this run's measured durations, where
> "fixed" means the element becomes instant. It is an upper bound on
> where to look, not a forecast, and a re-capture is still the ground
> truth. The report says so on its own last line.

---

## Step 4 — floors: is this a scheduler, graph, or work problem?

```text
Certified Floors:
  T∞ (observed critical path): 3610.50s
  LB (resource lower bound):   3610.50s
  Certified Headroom:          0.00s
  T_C (replay makespan):       3610.50s
  Efficiency Score:            1.00 (scheduling is near the certified floor for this graph ...)
  Dispatch Occupancy:          33.8% of available slot-time used
```

**`Certified Headroom` is a proof, not an estimate.** It is the gap
between what the build took and the fastest any schedule could have
finished *the work this build actually did*. Zero here means: **no
amount of rescheduling can help.** That is the strongest negative result
the tool produces, and it saves you from tuning `--builders` for a week.

**The two efficiency numbers must be read together, and they are
deliberately not one number:**

| reading | what it means |
|---|---|
| high score, high occupancy | genuinely well packed |
| **high score, low occupancy** | **the scheduler did fine — your graph is the problem** |
| low score | the scheduler left real time on the table |

This build is the middle row: 1.00 against 33.8%. `Efficiency Score` is
built entirely from the graph the run actually had, so a build whose
independent elements were accidentally chained scores a perfect 1.00 —
correctly, and uselessly. `Dispatch Occupancy` never consults the graph,
so serializing work that could have run concurrently pushes it down.

The measured proof that neither can be dropped: on a real project, three
one-line fixes made a build **30.5% faster** while `Efficiency Score`
moved **1.00 → 0.83** and `Dispatch Occupancy` moved **27.8% → 63.0%**.
Both of the first two numbers went the wrong way. See
[`UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md).

### If your build is *not* execution-bound

You will see a wait category instead, with a next step attached to it:

```text
  Biggest Opportunity: 70.1% of wall-clock time is RESOURCE WAIT (250.25s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a
       higher N, or `bga sweep` to find the real knee point
```

Then the questions to ask are capacity questions, and `bga` answers them
without another build:

```bash
bga sweep /tmp/run --resource PROCESS --min-capacity 1 --max-capacity 16  # how many builders is enough?
bga replay /tmp/run --capacity 16                                          # simulate a bigger machine
```

**If you captured Plane 2, pass it in.** Both of those are replay-model
answers and the replay model does not know about CPU, so on a host that
is already saturated they will happily recommend more builders:

```bash
bga analyze /tmp/run --plane2 /tmp/plane2.json
bga sweep   /tmp/run --resource PROCESS --plane2 /tmp/plane2.json
```

With the Plane 2 report in hand, a saturated host is told not to raise
capacity, and an element pinned to `-j1` is named first — that is
capacity you already have, and it costs nothing to reclaim.

---

## Step 5 — go inside the elements

Plane 1 stops at one start/end timestamp per element; that is all a
BuildStream log contains. The tracer you ran in step 1 recorded every
process *inside* each sandbox.

```bash
bga capture report /tmp/plane2.json
```

**Real CPU time**, which is the one measurement that separates "this
element is expensive" from "this element is waiting":

```text
Real CPU time (getrusage): 11744.07s across 119492 of 127627 traced processes
  components/_private/cmake-stage1.bst 5351.14s CPU over 1567.12s wall =  3.41 cores busy  [84% of processes measured]
  components/doxygen.bst               1825.48s CPU over  512.62s wall =  3.56 cores busy  [80% of processes measured]
  components/openssl.bst               1079.03s CPU over  668.73s wall =  1.61 cores busy  [87% of processes measured]
  components/bison.bst                  130.42s CPU over  142.97s wall =  0.91 cores busy  [100% of processes measured]
```

On a 4-core runner, 3.41 and 3.56 cores busy means those elements are
genuinely compute-bound — there is nothing to win from their
parallelism. **`bison.bst` at 0.91 is the outlier**: one core busy is the
signature of a build that never overlapped any work, and it is a job-count
setting, not a rewrite.

Coverage is always stated. A process killed by a signal or replaced by
`exec` runs no destructor, so it is counted as **unmeasured**, never as
zero.

**Where that CPU went**, ranked by time rather than by invocation count:

```text
Where the time went inside each element (by CPU time, not count):
  components/_private/cmake-stage1.bst
    cc1plus           4352.6 CPU s (81.3%)     885 process(es), 5525.6s wall
    as                 397.5 CPU s ( 7.4%)    1918 process(es), 5929.8s wall
    cc1                252.9 CPU s ( 4.7%)    1034 process(es), 272.4s wall
    dwz                137.0 CPU s ( 2.6%)       1 process(es), 138.6s wall
    NOTE: dwz is a SINGLE process holding 138.6s of wall time - a serialization
    point that more parallelism cannot help
```

Two different findings in one block. **81% of the element that is 43% of
your build is `cc1plus`** — this is a C++ template-instantiation problem,
and that is a specific day's work (precompiled headers, `extern
template`, splitting translation units), not a scheduling one. And `dwz`
is *one process* holding 138.6 seconds: no `-j` value touches it.

Ranking by count would have hidden both. `as` runs 1918 times to
`cc1plus`'s 885 and costs a tenth as much; `dwz` runs once.

**Peak memory**, which is how you decide whether you can raise
`--builders` at all:

```text
Peak Memory (largest single process per element):
  components/_private/cmake-stage1.bst       1901.9 MB  (10057 of 11974 processes measured)
  components/doxygen.bst                     1491.6 MB  (913 of 1139 processes measured)
  NOTE: a per-process peak, not a concurrent total - these are maxima and must not be summed.
```

1902 MB in a single process means four concurrent builders each running
something like it need ~7.6 GB. That is a hard constraint on
`--builders` that no timing signal would ever have shown you.

**Work repeated across elements:**

```text
Redundant cross-element operations (329 found, 42 above 0.05s):
  30x across 2 elements (components/bison.bst, components/doxygen.bst) - up to 20.401s
    recoverable wall-clock (worst element: components/doxygen.bst)
    /usr/bin/m4 -P
  242x across 2 elements (components/bison.bst, components/gperf.bst) - up to 10.314s
    recoverable wall-clock (worst element: components/bison.bst)
    x86_64-unknown-linux-gnu-gcc -o conftest -O2 -pipe -g ... conftest.c
```

These are `autoconf` probes and `m4` runs re-executed independently in
each element's sandbox — the classic case for a shared cache. Note the
scoring: **recoverable wall-clock for the worst-affected element**, not
process time summed across elements that ran concurrently. The figures
are per-signature maxima and **do not add**; the report says so under the
block.

---

## Step 6 — join the planes

Neither plane alone tells you what to do. Plane 1 knows `cmake-stage1` is
43% of your build; Plane 2 knows it is 81% `cc1plus` with a 1.9 GB peak.
The join says both, about the same element, ranked by whole-build impact:

```bash
bga correlate /tmp/run /tmp/plane2.json
```

```text
PARTIAL ATTRIBUTION - the rows below are correct for the elements they name,
and say nothing about the rest:
  109873 of 127627 traced processes (86.1%) are attributed to a named element;
  the remaining 17754 are in the unresolved bucket 'buildstream-build' ...

Joined 11 element(s) on element UID (126 in Plane 1, 11 traced in Plane 2)
  3 Plane 2 name(s) are not declared elements and are excluded from the rows below:
  buildstream-build, flit_core, unknown

What to do next (ranked by Plane 1 impact):
  components/_private/cmake-stage1.bst:
    - holds 43% of the critical path and fixing it is worth 1569.8s (43.4% of the build)
      - already compute-bound at 3.41 cores busy, so there is nothing to gain from its
      parallelism; shortening it means less work
    - 81% of its measured CPU is one binary, `cc1plus` (885 process(es), 4353 CPU s) -
      this element is a `cc1plus` problem, so look there before anywhere else
    - `dwz` is a SINGLE process holding 138.6s of wall time - a serialization point no
      job count can help; it has to get faster or go away
    - its largest single process peaked at 1902 MB resident - multiply by however many
      elements build concurrently before raising `builders`
    - opened no file staged by 1 declared build dependency (public-stacks/runtime-minimal.bst)
      - worth checking whether the edge is needed at build time, or only at runtime; this
      is evidence, not a verdict (a runtime-only dependency looks identical here)
    (84% of this element's processes were measured)
```

### Reading the join

**Rows are ordered by evidence strength**, strongest measurement first
and the explicitly hedged one last. That ordering is a field in the JSON
(`severity`), not just a convention in the prose.

**A restructuring finding, when the edges form a chain.** Individually
hedged "never read this dependency" rows are hard to act on; when a
*group* of them chains elements along the critical path, the join says so
as one finding and replays the run without those edges to attach a
number. That is the difference between reporting five bricks and naming
the wall.

**Negative results are load-bearing.** "Already compute-bound at 3.41
cores busy" is telling you to *stop looking* at this element's
parallelism. That is worth as much as a positive finding and is much
easier to skip past.

**Coverage is attached to every row.** "(84% of this element's processes
were measured)" scopes the four lines above it. The header does the same
for the whole report: 86.1% attributed, and the report names the bucket
holding the rest instead of quietly folding it in.

**Names that are not elements are excluded and listed.** Plane 2 derives
its element tag from the sandbox's own directory, which is the element
only under BuildStream's default build-root layout. On a project that
sets its own `build-root`, that produces names like `buildstream-build`
or `flit_core` that are not elements at all. They are checked against the
declared graph and kept out of the recommendations — the tool refuses
rather than guessing.

**The hedged row is hedged for a reason.** "Opened no file staged by a
declared build dependency" cannot distinguish an unused edge from a
runtime-only one, or from a dependency needed just for a directory to
exist. Treat it as a question to ask, never as a licence to delete an
edge.

---

## Step 7 — change something, then prove it

Make one change. Re-capture. Compare:

```bash
bga compare /tmp/run-before /tmp/run-after
```

You get a signed delta for every certified floor, both efficiency
signals, and each attribution category, plus a verdict gated on
confidence.

If the two runs do not look like the same project — fewer than half
their element UIDs shared — or one is a caches-off run and the other
incremental, `bga compare` **refuses**: exit **6**, naming the check that
failed, and prints no comparison. That exit code is deliberately not 4 or
5: in CI the likeliest way to feed `compare` two unrelated runs is an
artifact-path bug, and a pipeline keying on the gates' codes must not
read it as "your build got slower". `--allow-mismatch` compares anyway,
with the warning attached.

**One capture is not a baseline.** Run-to-run noise on this real build,
measured across two captures of the *same commit* with nothing changed,
is **2.9%** against a default significance rule of 1%. If you are gating
CI, build a baseline set instead of trusting a single pair:

```bash
bga compare baseline/run candidate/run \
    --baseline-run baseline/run-2 --baseline-run baseline/run-3 --band-k 3.0
```

That replaces the fixed threshold with a median ± k·MAD band over the
baseline set (a minimum of three runs, because a "band" over two points
just restates them).

## Step 8 — put it in CI

Two independent gates, because "slower" and "less efficient" are
different verdicts:

```bash
bga compare runs/baseline runs/candidate --fail-on-regression            # exit 4: slower
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression # exit 5: less efficient
```

The efficiency gate is the one worth reaching for on a growing project.
Adding three well-parallelized elements makes the build slower, and a
wall-clock gate cannot tell that apart from a regression — so the only
remedy is raising the threshold, which blinds it to everything else.
Measured on a real project:

| change | wall-clock | duration gate | occupancy | efficiency gate |
|---|---|---|---|---|
| two more well-parallelized elements | +2.5% | **fails** | 60.0% → 73.8% | passes |
| graph serialized, one element `-j1` | +44% | fails | 63.0% → 27.8% | **fails** |
| oversubscribed (`8×8` on 4 cores) | +19% | fails | 63.0% → 48.6% | **fails** |
| nothing changed (repeat capture) | −7.4% noise | fires on ±1% noise | 60.0% → 59.0% | passes |

A third gate exists for the case those two cannot express, and it is the
one a growing project wants. Occupancy is a whole-build average, so the
same badly-added pair of elements moves it **−14.6pp** in an 11-element
project and **−0.5pp** in a 1201-element one — the gate goes blind
exactly as the project gets big enough for CI to matter.
`--fail-on-inefficient-additions` asks instead what share of the work
*this change* added landed on the critical path, which mentions only the
added elements and so does not dilute:

```bash
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions
```

```text
New this change: g.bst, h.bst - 8.0s of work added, 8.0s of it on the critical path
(stretch 1.00)
```

For anything programmatic, read the JSON rather than the prose. Every
conclusion the text report draws is published as data, with a stable id
you can key on:

```bash
# Is this build chain-bound, and where is its time?
bga analyze /tmp/run --format json \
  | jq '.findings[] | select(.id == "time-concentration") | .evidence'

# Fail the job on anything the tool considers critical
bga analyze /tmp/run --format json \
  | jq -e '[.findings[] | select(.severity == "critical")] | length == 0'
```

---

## What the tool refuses to say, and why that matters

A short list, because knowing where a tool stops is what makes the rest
usable:

- **It will not attribute what it could not measure.** Unmeasured
  processes are counted as unmeasured, never as zero; partially covered
  elements state their coverage on every row.
- **It will not join fiction.** A Plane 2 bucket name that is not a
  declared element never enters the recommendations, even if it looks
  like one.
- **It will not call a dependency unused when it cannot tell.** A
  dependency that stages almost nothing of its own — a `stack` stages one
  marker file — is set aside as *aggregating*, and counted rather than
  reported as a finding.
- **It will not treat a projection as a measurement.** The horizon and
  joint-saving figures say on their own line that they are structural
  projections over this run's durations.
- **It will not compare across cache scenarios.** An incremental run and
  a caches-off nightly measure different builds.

---

## Appendix: where these numbers came from

The capture is run
[`32064333551`](https://github.com/rmorozov/buildstream-graph-analysis/actions/runs/32064333551),
published to the `captures/fdsdk-latest` branch as `5eda28a`:
`freedesktop-sdk` at `953683fb`, BuildStream 2.7.0, a 4-core runner,
`--builders 4 --max-jobs 4`, traced build exit 0. 127,627 processes
traced, 88,363 file paths recorded, zero dropped.

Plane 1 figures (`bga analyze`, `bga correlate`) are that capture's own
`run/` directory analysed with the current code. Two Plane 2 blocks —
`binary_cost` (the "where the time went inside each element" table) and
the redundancy list — were **recomputed from that capture's own process
records**, because the capture predates
[`UX-69`](../backlog/scenarios/UX-0069-plane-2-ranks-by-count-not-time.md) and
[`UX-73`](../backlog/scenarios/UX-0073-redundancy-findings-treat-the-unresolved-bucket-as-an-element.md);
the inputs are the same 127,627 records, only the analysis is newer.

The `+2.5% / +44% / +19%` efficiency-gate table and the `30.5% faster`
pair are from `examples/06-macro-micro-optimization`, measured locally
and written up in
[`UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md)
and [`UX-39`](../backlog/scenarios/UX-0039-ci-gate-cannot-express-inefficiency-regression.md).

The gap this paragraph used to apologise for is closed. **A caches-off
capture now exists** — `bootstrap/build/gcc-stage1.bst`, the whole
closure built from source with remotes ignored: 18 elements built, **0
cached**, in 34.2 minutes, at confidence 1.00 and with no
incremental-run caveat anywhere in the report. Its critical path is the
project's real one for that target, not a chain through a rebuilt
subset:

```text
Where the time is: 3 element(s) are 99.7% of the 1980.5s critical path
  bootstrap/build/gcc-stage1.bst  1248.7s (63.0% of path)  -> fixing it saves 1248.7s
  bootstrap/base-sdk/gettext.bst   725.9s (36.6% of path)  -> fixing it saves  110.1s
```

Note what the second row says, and what only a cold capture could have
shown: `gettext` is 36.6% of the path and worth **5.4%** of the build.
It sits behind `gcc-stage1` on the chain, so shortening it moves the
finish by a fraction of its own size. Share of the path and what a fix
is worth are different numbers, and here they differ by 6.6x.

The incremental captures remain the pre-commit scenario and are still
what you compare a pre-commit run against — `bga compare` refuses a
cold-vs-incremental pair outright, which is the point of having both.
See [`docs/audits/round-9.md`](../audits/round-9.md) and
[`UX-86`](../backlog/scenarios/UX-0086-caches-off-capture-has-never-been-performed.md).

## Where to go next

- [`docs/guides/cli.md`](cli.md) — every command and flag
- [`docs/design/architecture.md`](../design/architecture.md) — how the two planes work and why they are not merged
- [`docs/guides/optimization-walkthrough-06.md`](optimization-walkthrough-06.md) — the same cycle on a small project, written up as a case where the tool did *not* guide well
- [`docs/backlog/scenarios/README.md`](../backlog/scenarios/README.md) — every behaviour above, with the evidence that produced it
