# Using `bga` on a real project, end to end

This is the long-form walkthrough: from a project you have never traced
before to a ranked, evidenced list of what to change — and how to tell
which of the tool's answers you can act on and which you cannot.

Every output below is **real**, from a capture of
[`freedesktop-sdk`](https://gitlab.com/freedesktop-sdk/freedesktop-sdk)
at `953683fb` on a 4-core GitHub Actions runner with `--builders 4
--max-jobs 4` — a 3614-second build of 90 elements, 25 of which rebuilt,
except where a block names a different project. Nothing here is
illustrative or reconstructed. Provenance for every figure is in
[Appendix: where these numbers came from](#appendix-where-these-numbers-came-from).

If you want the 30-second version first, the top of
[`README.md`](../../README.md) runs against a checked-in fixture and needs
no BuildStream at all.

---

## The short version: two commands, and the second one answers the question

Everything below is the long form, and it is worth reading once. But the
loop you will actually run twice a day is two lines, from inside the
project:

```bash
bga snapshot -- bst build <your-target>
# ...make your change...
bga snapshot -- bst build <your-target>
```

The first prints the analysis. The second prints the analysis **and**
the comparison against the first — `IMPROVED`, `REGRESSED`, or
`NO SIGNIFICANT CHANGE`, with the deltas under it.

`bga snapshot` is `bga capture run` + `bga extract` + `bga analyze` +
`bga compare`, run for you, into `.bga/runs/<UTC-stamp>/` under the
project. It invents no paths, because the store already knows them
(`UX-126`); it changes no number, because it is those commands rather
than a reimplementation of them; and it refuses what they refuse — a
caches-off run against a caches-on one still says so instead of
comparing.

The store is a way of *naming* runs, so every command that takes a run
directory takes a name too:

```bash
bga analyze @last              # the newest snapshot
bga compare @prev @last        # the last two
bga analyze @20260819          # by stamp prefix
bga snapshot --list            # what is on disk, with sizes, and which alias is which
```

An explicit path keeps working everywhere it worked before. Outside a
project, an alias fails by name — *"there is no BuildStream project here
to resolve it against"* — rather than as a missing directory.

When a capture fails, `--diagnose` now keeps what the sandbox said. The
summary quotes the failing sandbox's stderr instead of leaving you with
`buildbox-run failed with returncode 1`, and

```bash
bga capture replay-sandbox <snapshot>/plane2.json.diagnostics.jsonl --list
bga capture replay-sandbox <snapshot>/plane2.json.diagnostics.jsonl -n 2
```

re-runs one recorded sandbox directly, with `buildbox-run` out of the
way. Replay only works while the paths that sandbox bound still exist —
BuildStream's staging roots are removed as the build proceeds — so it is
a tool for the failure you are chasing now, and it says which path is
gone rather than failing obscurely.

One thing to check before the first capture: if any element declares a
`local` source spanning the project root (or you open a workspace there),
BuildStream stages `.bga/` — a running capture's scratch included — into
that element's cache key and sandbox. There is no ignore mechanism, so
every capture churns the key. Scope such sources below the root, or
expect the churn; `bga doctor` warns when it finds one.

### If you interrupt it

A multi-hour capture is interrupted more often than it fails, so Ctrl-C
is a supported way to end one rather than an accident.

`bga snapshot` exits **130**. Whatever the build completed is kept and
analyzed, and the report says the build did not finish — so no figure
in it is presented as a measurement of a whole build, and a later
comparison against that snapshot refuses for the same reason any
unfinished build does. Interrupting *before* the build starts (the hook
compile, the census walk) leaves nothing behind and says so, rather
than leaving a snapshot that looks like a capture.

An interrupt during the post-build extraction is the one case with a
next step: `build.log` is complete, and the printed notice names the
`bga extract` line that re-runs just the step that was cut off.

The build gets a grace period to stop on its own before `bga`
escalates, because a big build's `queue_summary` — which the whole
comparison is built from — is written during that shutdown. Five
minutes by default; raise it with `BGA_INTERRUPT_GRACE_SECONDS` if your
build's own teardown is slower than that.

A snapshot scales with process count, so a big project's store grows
quickly — `--list` shows a size per snapshot and a total, and

```bash
bga snapshot prune --keep 5            # delete all but the newest five
bga snapshot prune --older-than 30     # or by age, in days
bga snapshot prune --keep 5 --dry-run  # say what would go, delete nothing
```

deletes them. `@last` and `@prev` are never deleted, and neither is the
newest *healthy* run when both of those record builds that did not
finish — that one is the baseline the next comparison walks back to.
Snapshots with no run directory at all go first under any criterion,
and are counted separately in what `prune` reports.

Two things stay sticky per project, in `.bga/config`: `--trace-opens`
and `--trace-spine`. Decide them once (`bga snapshot --trace-spine=off
-- bst build ...`) and every later snapshot of that project uses them.
Every report still records what actually ran, so a sticky flag cannot
make a capture *claim* something it did not do.

`.bga/` gitignores itself the first time it is written. Snapshots are
build artifacts: delete any of them whenever you like, nothing else
refers to them.

The rest of this guide is the plumbing underneath — worth knowing when
you need a capture somewhere other than the project directory, when the
log came from elsewhere, or when you are wiring CI, where the store's
laptop-shaped answer is replaced by published refs (`UX-96`).

---

## What you get, and what it costs

| step | what it answers | needs a live `bst`? |
|---|---|---|
| 0. `bga doctor` | Can this machine capture this project at all | yes, and that is the point |
| 0a. `bga cache-logs` | What has this project been spending time on already | no — **and no capture either** |
| 1–2. Capture and extract | — | **yes** |
| 3. `bga analyze` | Where is the time, what is worth fixing, and what after that | no |
| 4. Floors and the two efficiency signals | Is this a scheduler problem, a graph problem, or a work problem | no |
| 5. `bga capture report` | Inside one element, what was it actually doing | no (the capture needed one) |
| 6. `bga correlate` | Which of those inside-facts matter, ranked by whole-build impact | no |
| 7. `bga compare` | Did my change actually help | no |

Steps 3–7 read finished artifacts. You can capture on a build machine
and analyse anywhere, including from a tarball someone hands you.

Step 0a is different from all of them: it reads logs BuildStream already
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
bga cache-logs /path/to/your/project
```

Real output, from a freedesktop-sdk log tree:

```text
Sandbox tax: 13.0s of 4409.0s element time (0.3%) across 23 build log(s) went to
staging, integrating and caching rather than to the build itself
  Who paid it (by tax seconds, not by share):
    components/libffi.bst                4.0s tax of 49.0s (8%)
    components/bison.bst                 3.0s tax of 137.0s (2%)

Configure tax (Plane 3, self-reported): 35.5s of 4409.0s element time (0.8%),
reported by 3 of 23 build log(s)
  5 element(s) have traced configure work and no self-report - an autotools or
  meson build system, and the case the self-report alone is blind to
```

**What to do with it.** Three questions it answers that no capture can:

- *Is any element paying more to be an element than to build?* That is
  the sandbox tax. A high tax share on a short element is the signal
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
pip install /path/to/bga-checkout     # into your project's venv (UX-150)
bga doctor /path/to/your/project
```

`bga` is installed *into the venv that has your BuildStream*, from
wherever this repository happens to sit; it does not need to be in or
near the project it analyzes, and the capture is exercised in exactly
that shape by CI. `pip install -e ".[bst]"` from inside the checkout is
the contributor mode.

Plane 1 (the whole-project analysis) needs only Python. Plane 2 — the
tracer that looks *inside* an element's sandbox — needs a real `bst` and
a working `bubblewrap`, because it captures by injecting an `LD_PRELOAD`
hook into the processes the sandbox execs.

`bga doctor` (`UX-125`) checks that list, and this project against it,
in a second or two: `bst`, a real `bwrap` sandbox it actually builds and runs
in, a C compiler, whether the project loads and its plugins resolve,
what its sources stage, and whether Plane 3 has logs for it. Every check
that is not `ok` prints its own remedy, and it exits non-zero only on a
genuine failure — a static blind spot and an empty log tree are things
to read, not to block on. It changes nothing it inspects.

Real output, from this repository's `examples/01-resource-contention`
(a busybox project, which is the interesting case — everything it stages
is static):

```text
  [ok  ] bwrap-works: bwrap builds a sandbox and runs in it
  [ok  ] staged-sources: 50 executable(s) staged by this project's own sources
  [warn] static-blind-spot: 10 element(s) stage a statically-linked executable,
         which the LD_PRELOAD hook structurally cannot see
           all.bst / runtime.bst / work-a.bst / …
         -> capture with `--trace-spine=auto` - it pays the ptrace cost only for
            the elements the census says the hook is blind for (UX-105/UX-113)

  Everything a capture needs is here. 2 warning(s) worth reading first.
```

Full dependency list and its known limits:
[`docs/spec/ingestion-pipeline.md`](../spec/ingestion-pipeline.md).

### When a capture fails on a build that `bst` completes

Start here, before instrumenting the real build:

```bash
bga doctor --capture
```

That runs the whole chain — `bst` → `buildbox-run` → the `$PATH` shim →
the rewritten argv → the recorders inside the sandbox — on a canned
one-element build that takes seconds, and reports **per link, in chain
order** (`UX-149`):

```text
  [ok  ] chain-shim-exec: the bwrap shim is executable and answers its probe
  [ok  ] chain-build: bst ran 1 sandboxed task(s)
  [ok  ] chain-shim-reached: buildbox-run reached the shim 1 time(s) through $PATH
  [warn] chain-records: 3 process(es) recorded, none by the LD_PRELOAD hook (3 spine-only)
```

The first link that says `FAIL` is the one to fix, and it carries its own
remedy. Plain `bga doctor` checks the *parts*; this checks that they are
joined.

`bga doctor` checks the environment. It does not check *this* capture —
a real capture rewrites BuildStream's own generated `bwrap` argv, which
doctor never sees. When `bst build` works and `bga snapshot` does not
(typically `buildbox-run failed with returncode 1`, which is
BuildStream's summary of something it also could not see), `--diagnose`
records what the shim received and what it exec'd, one line per sandbox
(`UX-146`):

```bash
bga snapshot --diagnose -- bst build <your-target>
```

The count leads, because **zero is a different problem**: BuildStream
resolves `bwrap` through `buildbox-run`, one process layer below its own
Python, so the shim is reached through `$PATH`. Zero invocations means
that never happened and the build ran unmodified — not that the sandbox
failed. (A fully cached build also launches no sandbox, and the summary
says so.)

Then bisect:

```bash
bga snapshot --no-inject -- bst build <your-target>
```

which installs the shim and injects nothing. Succeeding here and failing
without it blames the argv rewrite; failing both ways blames the `$PATH`
shadow or the exec. Either answer names the next thing to look at, and
the diagnostics file is the thing to attach to a bug report.

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
- **The spine's price is 0.3 to 1.1 ms per process** — a measured range,
  not a constant, and why it is a range is
  [in the design doc](../design/architecture.md#plane-2-knows-the-size-of-its-own-blind-spot).
  Invisible on a compile-bound build, dominant on a process-dense one.
- **So prefer `--trace-spine=auto`** (`UX-113`): it pays that cost only
  for the elements the pre-build census says the hook is blind for, plus
  any it could not assess. On an all-dynamic project that is no elements
  at all; on a busybox one it is all of them. It is what `bga snapshot`
  uses by default.
- **Plane 2 costs real overhead.** `--trace-opens` in particular runs on
  a hot path. Capture it deliberately, not by default.

---

## Step 1 — capture both planes from one build

> Steps 1 and 2 are what `bga snapshot` runs for you, into the project's
> own store. They are spelled out here because you will need them for a
> build you cannot run from inside the project directory — a CI runner,
> or a log somebody else captured.

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
  components/_private/cmake-stage1.bst, components/doxygen.bst (2 elements, 14-43% of
  the critical path each, 513.5-1569.8s apiece, 2083.3s together):
    - already compute-bound at 3.4-3.6 cores busy - nothing to gain from their
      parallelism; shortening them means less work
    - its largest single process peaked at 1902 MB resident - multiply by however many
      elements build concurrently before raising `builders` (the capture recorded no
      host memory, so this cannot do it for you)
    - it pays 186.7s for an operation 8 other elements also run (15x in total):
      sh -c -e OPTS=()
    - opened no file staged by 1 declared build dependencies each (2 edges across the 2)
      - worth checking whether those edges are needed at build time; this is evidence,
      not a verdict (a runtime-only dependency looks identical here). Per-element lists
      are in --format json
    (80-84% of each element's processes were measured)
  components/openssl.bst:
    - holds 19% of the critical path and fixing it is worth 522.5s (14.5% of the build) -
      already compute-bound at 1.61 cores busy, so there is nothing to gain from its
      parallelism; shortening it means less work
```

Two elements share one block because they are one story (`UX-89`):
grouping happens when the findings match, and the figures collapse to
ranges rather than being averaged into something the measurement does
not say.

**On the memory line's parenthetical.** This capture predates the host
memory field, so the join says what it *cannot* do rather than dropping
the row. Where the capture does record it — anything `bga snapshot`
takes today — that line is replaced by a computed envelope at the top of
the report:

```text
  Memory envelope: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%);
  9 would still fit, so memory is not what binds first here
```

(from `examples/06`, since the retained fdsdk capture cannot produce it).

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

Make one change, then take another snapshot — the comparison against the
previous one is automatic:

```bash
bga snapshot -- bst build <your-target>     # from inside the project
bga compare /tmp/run-before /tmp/run-after  # or explicitly, on any two runs
```

You get a signed delta for every certified floor, both efficiency
signals, and each attribution category, plus a verdict gated on
confidence.

If the two runs are not comparable — too few shared element UIDs, or one
cold and the other incremental — `bga compare` **refuses** with exit 6
rather than guessing, and names the check that failed. Why that is its
own exit code, and what the others mean:
[`cli.md`](cli.md#exit-codes). `--allow-mismatch` compares anyway.

**One capture is not a baseline.** Run-to-run noise on this real build,
measured across **five** captures of the *same commit* with nothing
changed, is **33%** against a default significance rule of 1% (3614.2s,
3434.4s, 3405.8s, 3261.2s, 2712.4s, taken by the scheduled capture
workflow). Earlier readings over two and then three of those captures
gave 2.9% and 5.8% — the same lesson each time with less of the spread
visible, which is the argument for planning against the widest figure
you have and re-checking it as the history grows. If you are gating CI,
build a baseline set instead of trusting a single pair:

```bash
bga baseline --glob 'captures/<project>/<commit>-incremental-b4j4-*' -n 3 \
    --candidate runs/candidate
```

That fetches the newest three published captures, refuses a set whose
members are not comparable to each other, and band-compares in one
command (`UX-96`). It composes this, which is what to run when the runs
are already on disk:

```bash
bga compare baseline/run candidate/run \
    --baseline-run baseline/run-2 --baseline-run baseline/run-3 --band-k 3.0
```

Either way the fixed threshold is replaced by a median ± k·MAD band over
the baseline set — a minimum of three runs, because a "band" over two
points just restates them. Strictly better than the fixed rule, and not
yet enough: over those five same-commit captures the band absorbs the
−5.8% and −9.8% pairs and still calls the widest one `IMPROVED
(-25.0%)`, because the *fastest* run falls below the lower edge of the
band its own presence helped compute
([`UX-170`](../backlog/scenarios/UX-0170-the-noise-band-still-calls-a-same-commit-pair-a-25-percent-win.md)).
Use more baseline runs than the minimum where you can. The whole CI
sequence is [`ci-comment.md`](ci-comment.md).

## One repository, many elements: the monorepo question

If your project's elements are fed by one repository, the first thing
to know is what BuildStream keys their cache on — because two ways of
consuming the same repo differ by an order of magnitude in what a
commit costs.

A **`git` source keys on its ref.** `directory:` says where the
checkout is *staged* in the sandbox; it does not narrow what the key
covers. Twenty elements pointing at one url with twenty different
`directory:` values all take a new cache key from *any* commit to that
repository, including one that touched nothing they stage. A **`local`
source keys on content**, so only the elements whose files actually
changed rebuild. That single difference is the whole of this section.

`bga` measures it rather than asserting it. The analysis report grows a
`Shared Sources` block for any resource more than one element uses, and
a Key Findings line when one repository's ref decides most of the
graph:

```bash
bga analyze @last                  # the table, and the headline
bga blast https://…/monorepo.git   # what a commit to it rebuilds
bga blast components/lib-a         # what a commit to one directory does
bga blast lib-a.bst                # and the element's own closure
```

`bga blast` is a question, not a gate: it always exits 0, and it says
which reading of the target it used (url, then path, then element).

### The four patterns, and what each costs

| pattern | blast | price |
|---|---|---|
| One `git` url for every element | every consumer, on every commit | simplest to declare; the widest blast, and the one the headline measures |
| A repository or ref per component | only that component's consumers | smallest blast; the most repositories and refs to maintain |
| `local` sources over a checkout CI already has | per-directory, by content | the practical monorepo answer; needs the checkout to exist before `bst` runs |
| Junction pinning | at junction granularity | coarse but explicit; a junction bump rebuilds its whole subproject |

Read the table, not the taste: `bga analyze` gives each of these a
measured cost on *your* graph, and `bga blast` prices a change before
you make it. A pattern that is right for a 40-element project is often
wrong for a 4,000-element one, which is why this page does not
recommend one.

### What this does not tell you

It reads *declared* sources — what the `.bst` files say. Tracking
behaviour (`bst track` cadence, how often refs are bumped, whether a
branch or a tag is pinned) decides *when* rebuilds happen; the blast
figures here decide *what one costs when it does*. Both matter, and
only the second is measurable from the project on disk.

Elements from a junctioned subproject are counted as unreadable rather
than as sourcing nothing: their `.bst` files live in that project, not
this one, and the report says how many it could not speak for.

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

The same three configurations, gated: a duration gate fires on all of them including pure noise, and the efficiency gate fires on the two that are real. The measured table is in [`cli.md`](cli.md#ci-efficiency-gate---fail-on-efficiency-regression---min-efficiency).

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
- [`docs/audits/case-study-06-macro-micro.md`](../audits/case-study-06-macro-micro.md) — the same cycle on a small project, written up as a case where the tool did *not* guide well
- [`docs/backlog/scenarios/README.md`](../backlog/scenarios/README.md) — every behaviour above, with the evidence that produced it
