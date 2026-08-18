# BuildStream Build Efficiency Analyzer (`bga`)

`bga` reads a BuildStream build and answers the four questions a build owner actually has:

- **Where did the time go?** — per-element attribution, every category summing to exactly the wall clock, not aggregate stats.
- **How much faster could this build possibly be?** — a *proven* lower bound, not an estimate. When there is nothing to win from rescheduling, it says so, which saves you the week you would have spent tuning `--builders`.
- **What should I fix first, and what is it actually worth?** — ranked by how much the build would really lose if that element were free, which on a dense graph is a very different number from how big it is.
- **And then what?** — the next few fixes, what the build drops to after each, and whether their savings add — projected from the capture you already have, instead of costing you another full build per finding.

It works in two complementary planes: a **whole-project** analysis of one build's element-level log, and an **intra-element** tracer that looks *inside* a single element's sandbox at its native build system's real process tree (`make -jN`, `cmake --build`, …) — see [Advanced: looking inside one element](#advanced-looking-inside-one-element-plane-2).

**New here?** [`docs/real-project-guide.md`](docs/real-project-guide.md) is the full end-to-end walkthrough on a real project, with real output at every step.

## Install

```bash
pip install -e .
```

## Quick start (30 seconds, no BuildStream needed)

```bash
bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics
```

Or `make dev-run` (same thing) / `make dev-run ARGS=--large` for a bigger, more realistic sample:

```
Key Findings:
  Confidence: 0.99 (high)
  Biggest Opportunity: 5.6% of wall-clock time is IDLE (8.00s)
    -> nothing was dependency-ready at all - likely a critical-path/graph-shape issue,
       not a capacity one; check Critical Path
  Elements Most Worth Optimizing First (by blast radius):
    1. core-utils.bst:libcore.bst (7 downstream elements)
    2. ui-toolkit.bst:libwidgets.bst (2 downstream elements)
    3. data-format.bst:libjson.bst (2 downstream elements)
  Certified Headroom: up to 24.00s available (T∞=118.00s, LB=118.00s)
  Efficiency Score: 0.83 (worth checking Certified Headroom for real scheduling gains)

Certified Floors:
  T∞ (observed critical path): 118.00s
  LB (resource lower bound):   118.00s
  Certified Headroom:          24.00s
  T_C (replay makespan):       118.00s
  Dispatch Occupancy:          45.1% of available slot-time used

Critical Path Length: 4 elements
  Path: core-utils.bst:libcore.bst → ui-toolkit.bst:libwidgets.bst → ui-toolkit.bst:libui.bst → app.bst
```

### At a thousand elements, still no BuildStream needed

```bash
python3 -m tools.gen_synthetic_scale_run /tmp/scale --seed 1   # 1202 elements, 14 levels, 16 builders
bga analyze /tmp/scale --diagnostics                            # ~3.8s
```

```
  Biggest Opportunity: 70.1% of wall-clock time is RESOURCE WAIT (250.25s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a
       higher N, or `bga sweep` to find the real knee point
  Elements Most Worth Optimizing First (by blast radius):
    1. toolchain.bst (1201 downstream elements) [structural: import, may not reflect real compute work]
    2. layer00/mod037.bst (753 downstream elements)
    3. layer00/mod003.bst (753 downstream elements)
  Highest Criticality Elements:
    1. layer01/mod098.bst (70% probability of being on critical path)
  Certified Headroom: up to 9.09s available (T∞=85.65s, LB=346.06s)
```

A different shape from the sample above, and the report says so: this run is **resource-bound**, so the ceiling is `LB` (346.06s) rather than the critical path (85.65s) — more builders, not a shorter chain. The fixture is byte-reproducible from its `--seed`; it exists because a second audit round found four defects invisible at eleven elements.

## On a real project

Below is `bga analyze` on a real 3614-second [`freedesktop-sdk`](https://gitlab.com/freedesktop-sdk/freedesktop-sdk) build (4-core runner, `--builders 4 --max-jobs 4`), verbatim:

```
Key Findings:
  Incremental run (caches on): BuildStream skipped elements it had already built, 2 of
  them on the critical path. Coverage and the floors below describe the work this run
  actually did, not the whole project - compare against another incremental run, not
  against a caches-off nightly
  Confidence: 1.00 (high)
  Biggest Opportunity: this build is execution-bound - no wait category exceeds 1% of
  wall-clock time, so there is no scheduling gap to close
  Where the time is: 4 element(s) are 94.0% of the 3610.5s critical path - this build is
  chain-bound, not scheduler-bound
    components/_private/cmake-stage1.bst    1569.8s (43.5% of path)  -> fixing it saves 1569.8s (43.4% of the build)
    components/openssl.bst                   672.1s (18.6% of path)  -> fixing it saves 522.5s (14.5% of the build)
    components/python3.bst                   639.8s (17.7% of path)  -> fixing it saves 114.1s (3.2% of the build)
    components/doxygen.bst                   513.5s (14.2% of path)  -> fixing it saves 513.5s (14.2% of the build)
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so
    savings on one element are often capped by the next chain rather than by its own duration
  Together, the top 3 are worth 2605.8s (72% of the build) - exactly the sum of their
  individual savings, so they are three separate pieces of work that do not overlap
  Work them in this order (by what a fix is worth, not by size), with what the build drops
  to: cmake-stage1.bst (2041s) -> openssl.bst (1518s) -> doxygen.bst (1005s)
  Waiting off the critical path, worth nothing to fix today:
  components/_private/git-minimal.bst (548s), components/icu.bst (431s) (+2 more)
```

Three things in that block are worth pointing at, because they are the difference between a report and an answer:

- **`python3.bst` is the third-largest element on the chain and worth 3.2% of the build to fix.** Share of the path and value of a fix are different numbers, and on a mesh graph they disagree by 5×. Ranking by size would have sent you after a week's work for a minute's gain.
- **The top three are worth 72% *together*, and that equals their sum** — so they are three independent pieces of work, and three people can take one each. Whether savings compose is a property of your graph, simulated rather than assumed.
- **`git-minimal.bst` is the fourth-heaviest element in the entire build and is worth nothing to fix today.** It appears in no ranking, correctly — and you still need to know it is there, because it is the floor your chain-shortening is heading towards.

Then the same build, seen from inside the sandboxes and joined back to whole-build impact (`bga correlate`):

```
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
    (84% of this element's processes were measured)
```

That is one report telling you: the element that is 43% of your build is a C++ template problem, not a scheduling one; there is a 138-second serialization point inside it that no `-j` value touches; and four concurrent builders of that shape need ~7.6 GB. **Full step-by-step walkthrough, every command and every output: [`docs/real-project-guide.md`](docs/real-project-guide.md).**

## Reading the report

- **Confidence** — how much to trust the numbers below (data completeness/quality of this specific trace). Below "high"? Fix the underlying trace before acting on anything else. A build that *failed* is called out even louder, before any efficiency figure.
- **Certified Headroom** — a *proven* lower bound, not a guess: given the work this build actually did, it cannot possibly finish faster than `T∞`/`LB` (whichever is larger) without changing that work. Headroom above zero means real room to improve scheduling *without touching any element's build steps*; zero means rescheduling cannot help at all.
- **Efficiency Score and Dispatch Occupancy** — deliberately two numbers, because one cannot do the job. **Efficiency Score** asks *"did the scheduler pack this graph well?"*, and everything it is built from comes from the graph this run actually had — so a build whose independent elements were accidentally chained scores a perfect 1.00, correctly and uselessly. **Dispatch Occupancy** asks *"how much of the available slot-time did the run actually use?"* and never consults the graph, so serializing work that could have run concurrently pushes it down. Read them together: a high score with low occupancy means the scheduler did fine and the *graph* is the problem. (Real measured pair: three one-line fixes made a build 30.5% faster while Efficiency Score fell 1.00 → 0.83 and Dispatch Occupancy rose 27.8% → 63.0%. See [`docs/scenarios/UX-27`](docs/scenarios/UX-27-efficiency-score-certifies-the-graph-it-was-given.md).)
- **Where the time is** — on a build the chain constrains, the headline is one table: each heavy element's duration, its share of the critical path, and what fixing it would actually recover. The rows are ordered by duration because that is what "where is the time" means; the fix order is named separately, because on a dense graph the two disagree.
- **What to do after that** — the next few fixes projected from the same capture: what the build drops to after each, whether the recommended set's savings *add*, and which heavy elements sit off the critical path worth nothing to fix today. Without it, finding the second thing to fix costs another full build. ([`UX-74`](docs/scenarios/UX-74-one-capture-one-finding.md))
- **Elements Most Worth Optimizing First** — on a build the *graph* constrains rather than the chain, this ranks by blast radius instead: fixing a slow element near the root helps every downstream element too.
- **Biggest Opportunity / Attribution Breakdown** — where wall-clock time went, by category (execution, dependency wait, resource wait, scheduler wait, idle, retries). Every category sums to exactly the total build time — nothing is hidden or double-counted.
- **Critical Path** — the chain that determines total build time, printed in full with each link's duration and share.
- If a hard gate fails (e.g. `critical_path_coverage`), the violation names the specific missing element(s) and whether each is a structural element (`stack`/`import`/…) that never had a real compute task or a genuine gap worth investigating.

Everything in that block is also published as **data**, with a stable `id`, a `severity` and the numbers behind each sentence — so a CI job acts on `.findings[]` rather than re-deriving a threshold or grepping prose:

```bash
bga analyze /tmp/run --format json | jq '.findings[] | select(.id == "time-concentration") | .evidence'
# { "path_us": 3610500000, "share_of_path": 0.94035, "chain_bound": true }
```

## Use it on your real project

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/ingestion-pipeline.md
# Capture through the wrapper: it records the real invocation on its own first
# line, which is where `--max-jobs` lives - without it bga's capacity checks
# have nothing to check against and say so.
bga wrap /path/to/your/project /tmp/build.log -- bst build <targets>
bga extract --format wrapped /path/to/your/project /tmp/build.log /tmp/my-run
bga analyze /tmp/my-run --diagnostics
```

Then iterate: make a change, rebuild, extract a new run, and compare it against the baseline:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

This reports a signed delta for every certified floor, both efficiency signals, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) — gated on confidence. If the two runs don't look like the same project, or one is a caches-off run and the other incremental, it **refuses** — exit 6, distinct from the gates' 4 and 5, so a CI job cannot mistake a wrong-artifact-path bug for a regression. `--allow-mismatch` compares anyway.

> **One capture is not a baseline.** Measured run-to-run noise on a real project, across two captures of the *same commit*, is **2.9%** against a default significance rule of 1%. For CI, build a baseline *set* and use the band: `--baseline-run A --baseline-run B --band-k 3.0` (minimum three runs).

The full narrative version of this — capture, read, go inside, join, act, gate — is [`docs/real-project-guide.md`](docs/real-project-guide.md).

## Gating a CI pipeline

Two independent gates, because "the build got slower" and "the build got less efficient" are different verdicts:

```bash
bga compare runs/baseline runs/candidate --fail-on-regression              # exit 4: slower
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression   # exit 5: less efficient
bga compare runs/baseline runs/candidate --min-efficiency 0.45             # exit 5: below an absolute floor
```

The second is the one worth reaching for on a growing project. Adding three new elements makes the build slower, and a wall-clock gate cannot tell that apart from a real regression — so the only remedy is raising the threshold, which blinds it to everything else. The efficiency gate asks the question a build owner actually has: **adding work is allowed; adding work *inefficiently* is not.** Measured on one real project:

| change | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| two more well-parallelized elements | +2.5% | **fails** | 60.0% → 73.8% | passes |
| graph serialized, one element pinned to `-j1` | +44% | fails | 63.0% → 27.8% | **fails** |
| oversubscribed (`8×8` on 4 cores) | +19% | fails | 63.0% → 48.6% | **fails** |
| nothing changed (repeat capture) | −7.4% noise | fires on ±1% noise | 60.0% → 59.0% | passes |

Full flags, thresholds and how the default was derived: [`docs/cli.md`](docs/cli.md#ci-efficiency-gate---fail-on-efficiency-regression---min-efficiency).

Other useful commands:

```bash
bga analyze /tmp/my-run --format json > report.json      # machine-readable, for CI/tracking over time
bga sweep /tmp/my-run --resource PROCESS --min-capacity 1 --max-capacity 16  # "how many builders is enough?"
bga replay /tmp/my-run --capacity 16                      # simulate a hardware upgrade
```

The `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` subcommands are narrower slices of the same `analyze` report — reach for one of them instead of grepping `analyze`'s output for a single question. They are also genuinely cheaper: each runs only the pipeline stages its own section renders (`UX-47`), so on a 1200-element run `bga graph` costs ~1.2s against `analyze`'s ~3.7s. Full reference: [`docs/cli.md`](docs/cli.md).

## Advanced: looking inside one element (Plane 2)

Everything above answers *"across the whole build, where did the time go and what's the ceiling on making it faster?"* — that's as deep as a BuildStream log itself goes: one start/end timestamp per element, nothing about what happened *inside* its sandbox. A second, separate tool answers *"inside this one element, is its own native build system actually parallelizing well, or silently serializing / doing redundant work?"* — real per-process tracing via an `LD_PRELOAD` hook inside the sandbox, not a guess from timing alone:

```bash
bga capture run /path/to/your/project report.json -- bst build <target>
```

**Real CPU time per element** (`getrusage`, measured in-process — the only genuine CPU measurement anywhere in `bga`) answers what timing alone cannot: *was this element compute-bound, or waiting?* On the real `freedesktop-sdk` capture, on a 4-core runner:

```
Real CPU time (getrusage): 11744.07s across 119492 of 127627 traced processes
  components/_private/cmake-stage1.bst 5351.14s CPU over 1567.12s wall =  3.41 cores busy  [84% measured]
  components/doxygen.bst               1825.48s CPU over  512.62s wall =  3.56 cores busy  [80% measured]
  components/bison.bst                  130.42s CPU over  142.97s wall =  0.91 cores busy  [100% measured]
```

The first two are genuinely compute-bound — nothing to win from their parallelism. `bison.bst` at 0.91 is the outlier: one core busy is the signature of a build that never overlapped any work, and that is a job-count setting, not a rewrite.

**Where that CPU went**, ranked by time rather than by invocation count — which is the difference between finding the problem and finding the most frequent process:

```
  components/_private/cmake-stage1.bst
    cc1plus           4352.6 CPU s (81.3%)     885 process(es), 5525.6s wall
    as                 397.5 CPU s ( 7.4%)    1918 process(es), 5929.8s wall
    dwz                137.0 CPU s ( 2.6%)       1 process(es), 138.6s wall
    NOTE: dwz is a SINGLE process holding 138.6s of wall time - a serialization
    point that more parallelism cannot help
```

**Peak memory per element**, which is how you decide whether `--builders` can go up at all — `1901.9 MB` in a single process means four concurrent builders of that shape need ~7.6 GB.

**Achieved parallelism against the `-jN` it asked for** — the number that separates "this element is legitimately 13 seconds of work" from "this element is 4 seconds stretched to 13 by a one-line `notparallel: True`" (from a small local project, where that case exists):

```
Per-element native parallelism (real compiler/assembler/linker processes only):
  element                  peak  req  achieved     span work
  core.bst                    2    1      200%   14.22s   32  <- pinned to -j1 while the rest of this build ran higher
  lib-a.bst                   3    4       75%    2.46s   22
```

And with `--trace-opens`, **which declared build dependencies an element never actually read** — by recording the files each sandbox opened and matching them against each dependency's own artifact contents. These are candidates with evidence, never verdicts: a runtime-only dependency is indistinguishable from an unused one from here, and a dependency that stages almost nothing of its own (a `stack` stages one marker file) is set aside rather than reported.

### Joining the two planes

Capture both from one build, then join them on element UID — the only contract between the planes:

```bash
bga capture run --wrapped-log /tmp/plane1.log \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga correlate /tmp/run /tmp/plane2.json
```

This produces what neither plane can alone — see [the real example above](#on-a-real-project). Rows are ordered by evidence strength, strongest measurement first and explicitly hedged ones last; every row states its own measurement coverage; and a Plane 2 name that is not a declared element is excluded and listed rather than quietly recommended. The negative result matters too: an element reported as *already compute-bound* is one to stop looking inside.

It also detects real operations repeated independently across *multiple* elements' sandboxes (`autoconf` probes, `m4` runs — scored in recoverable wall-clock for the worst-affected element rather than summed across elements that ran concurrently) and can export a [Chrome Trace](https://ui.perfetto.dev)-viewable timeline, standalone or combined with the whole-project view into one file.

## Documentation

- [**Real-project guide**](docs/real-project-guide.md) — **start here to use the tool**: capture → read → go inside → join → act → gate, end to end on a real project with real output at every step
- [`docs/architecture.md`](docs/architecture.md) — **start here to work on the codebase**: what `bga` does today as one coherent system (both planes), with a table of every extension beyond the original spec
- [CLI Reference](docs/cli.md) — every `bga` command and flag
- [Optimization Walkthrough](docs/optimization-walkthrough.md) — a worked example of iteratively finding and fixing build-efficiency problems
- [Optimization Walkthrough (macro → micro)](docs/optimization-walkthrough-06.md) — the harder companion: a project with a badly-shaped graph *and* a badly-parallelized element, and an honest account of which of those `bga` helps you find
- [Design Directions](docs/design-directions.md) — where the tool is going, argued separately for its two real usage scenarios
- [Ingestion Pipeline](docs/ingestion-pipeline.md) — how a real BuildStream project + log becomes `bga` input, and its known limitations
- [v9 Specification](docs/specification.md) — the underlying analysis specification (ground truth for what every number means)
- [`docs/scenarios/`](docs/scenarios/README.md) — full backlog (done + active) of usability/workflow extensions, each with real before/after evidence

## Development

```bash
make test     # run the full suite
make lint     # ruff
make dev-run  # sample report, fast smoke check
```

## License

MIT
