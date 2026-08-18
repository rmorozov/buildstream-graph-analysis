# BuildStream Build Efficiency Analyzer (bga)

`bga` reads a BuildStream build trace and tells you three things: **how much faster this build could possibly be** (a proven lower bound, not a guess), **exactly where the time actually went** (per-element attribution, not aggregate stats), and **what to fix first** (ranked by how many other elements depend on it).

It works in two complementary modes: a **whole-project** analysis of one build's element-level log (the core of the tool, below), and an **intra-element** tracer that looks *inside* a single element's own sandbox at its native build system's real process tree (`make -jN`, `cmake --build`, ...) — see [Advanced: looking inside one element](#advanced-looking-inside-one-element-plane-2) further down.

## Install

```bash
pip install -e .
```

## Quick Start (30 seconds, no BuildStream needed)

```bash
bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics
```

Or `make dev-run` (same thing) / `make dev-run ARGS=--large` for a bigger, more realistic sample. That larger sample looks like this (trimmed):

```
Key Findings:
  Confidence: 0.99 (high)
  Biggest Opportunity: 5.6% of wall-clock time is IDLE (8.00s)
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
  Efficiency Score:            0.83 (worth checking Certified Headroom for real scheduling gains)
  Dispatch Occupancy:          45.1% of available slot-time used

Attribution Breakdown:
  Execution On Chain Us       134.00s ( 94.4%)
  Idle Us                       8.00s (  5.6%)
  ...

Critical Path Length: 4 elements
  Path: core-utils.bst:libcore.bst → ui-toolkit.bst:libwidgets.bst → ui-toolkit.bst:libui.bst → app.bst
```

## Reading the report

- **Confidence** — how much to trust the numbers below (data completeness/quality of this specific trace). Below "high"? Fix the underlying trace before acting on anything else.
- **Certified Headroom** — a *proven* lower bound, not a guess: given the work this build actually did, the build cannot possibly finish faster than `T∞`/`LB` (whichever is larger) without changing that work. Headroom above zero means there's real room to improve scheduling/parallelism *without touching any element's own build steps*.
- **Efficiency Score and Dispatch Occupancy** — deliberately two numbers, because one cannot do the job. **Efficiency Score** asks *"did the scheduler pack this graph well?"*, and everything it is built from comes from the graph this run actually had — so a build whose independent elements were accidentally chained scores a perfect 1.00, correctly and uselessly. **Dispatch Occupancy** asks *"how much of the available slot-time did the run actually use?"* and never consults the graph, so serializing work that could have run concurrently pushes it down. Read them together: a high score with low occupancy means the scheduler did fine and the *graph* is the problem. (Real measured pair: three one-line fixes made a build 30.5% faster while Efficiency Score fell 1.00 → 0.83 and Dispatch Occupancy rose 27.8% → 63.0%. See [`docs/scenarios/UX-27`](docs/scenarios/UX-27-efficiency-score-certifies-the-graph-it-was-given.md).)
- **Critical Path** — the one chain of elements that determines total build time. Speeding up anything *not* on this path doesn't shorten the build at all — this is always where to look first for reducing the work itself, not just rescheduling it. The full chain is printed, with each link's real duration and share of the path, so the longest link is visible without cross-referencing anything.
- **Biggest Opportunity / Attribution Breakdown** — where wall-clock time actually went, by category (execution, waiting on a dependency, waiting on a resource, waiting on the scheduler, idle, retries). Every category sums to exactly the total build time — nothing is hidden or double-counted.
- **Elements Most Worth Optimizing First** — ranked by blast radius (how many other elements depend on it): fixing a slow element near the root of your graph helps every downstream element too. On a build the *chain* constrains, this becomes a **"Where the time is"** table instead, ranked by what a fix would actually recover rather than by size — the two disagree on a dense graph, and the table shows both.
- **What to do after that** — the report projects the next few fixes from the same capture: what the build drops to after each, whether the recommended set's savings *add* (a property of your graph, simulated rather than assumed), and which heavy elements are sitting off the critical path worth nothing to fix today. Without it, finding the second thing to fix costs another full build. See [`docs/scenarios/UX-74`](docs/scenarios/UX-74-one-capture-one-finding.md).
- If a hard gate fails (e.g. `critical_path_coverage`), the violation now names the specific missing element(s) and, where known, whether it's a structural element (`stack`/`import`/...) that never had a real compute task or a genuine gap worth investigating — no need to cross-reference the critical-path list by hand.

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

This reports a signed delta for every certified floor, both efficiency signals, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) - gated on confidence, with a warning if the two runs don't look like the same project.

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

The `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` subcommands are narrower slices of the same `analyze` report — reach for one of them instead of grepping `analyze`'s output for a single question. They are also genuinely cheaper: each runs only the pipeline stages its own section renders (`UX-47`), so on a 1200-element run `bga graph` costs ~1s against `analyze`'s ~3s. Full reference: [`docs/cli.md`](docs/cli.md).

## Advanced: looking inside one element (Plane 2)

Everything above answers *"across the whole build, where did the time go and what's the ceiling on making it faster?"* — that's as deep as a BuildStream log itself goes: one start/end timestamp per element, nothing about what happened *inside* its sandbox. A second, separate tool answers *"inside this one element, is its own native build system (`make -jN`, `cmake --build`, ...) actually parallelizing well, or silently serializing / doing redundant work?"* — real per-process tracing via an `LD_PRELOAD` hook inside the sandbox, not a guess from timing alone:

```bash
bga capture run /path/to/your/project report.json -- bst build <target>
```

It reports, per element, the parallelism its native build system **actually achieved** against the `-jN` it asked for — the one number that separates "this element is legitimately 13 seconds of work" from "this element is 4 seconds of work stretched to 13 by a one-line `notparallel: True`":

```
Per-element native parallelism (real compiler/assembler/linker processes only):
  element                  peak  req  achieved     span work
  core.bst                    2    1      200%   14.22s   32  <- pinned to -j1 while the rest of this build ran higher
  lib-a.bst                   3    4       75%    2.46s   22
```

It also reports **real CPU time per element** (`getrusage`, measured in-process — the only genuine CPU measurement anywhere in `bga`), which answers the question timing alone cannot: *was this element compute-bound, or waiting?*

```
Real CPU time (getrusage): 45.56s across 663 of 822 traced processes (159 exited abnormally and are unmeasured)
  core.bst        10.70s CPU over  12.35s wall =  0.87 cores busy   <- waiting, not compute-bound
  lib-a.bst        4.56s CPU over   2.68s wall =  1.70 cores busy
```

And with `--trace-opens` it answers the last macro-level question — **which declared build dependencies did an element never actually read?** — by recording the files each sandbox opened and matching them against each dependency's own artifact contents:

```
Declared build dependencies never read: 24 candidate(s) across 7 element(s); 9 edge(s) confirmed used
  lib-b.bst    never read: codegen.bst, core.bst, lib-a.bst
```

These are candidates with evidence, not verdicts: an element whose processes the hook could not see is reported as *uncovered* rather than as having unused dependencies.

### Joining the two planes

Capture both from one build, then join them on element UID — the only contract between the planes:

```bash
bga capture run --wrapped-log /tmp/plane1.log \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga correlate /tmp/run /tmp/plane2.json
```

This answers what neither plane can alone — not *"`core.bst` is 25% of your critical path"* and not *"`core.bst` runs at 0.85 cores busy"*, but what to do about it:

```
What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 25% of the critical path but runs at only 0.85 cores busy - it is waiting,
      not computing, and its native build asked for -j1: remove `notparallel` / raise
      its job count before touching its sources
```

The negative result matters too: an element reported as *already compute-bound* is one to stop looking inside. It also detects real operations repeated independently across *multiple* elements' sandboxes (e.g. the same compiler-ABI probe re-run once per element, scored in recoverable wall-clock rather than summed process time) and can export a [Chrome Trace](https://ui.perfetto.dev)-viewable timeline, standalone or combined with the whole-project view above into one file. Full picture, real evidence, and every command: [`docs/architecture.md`](docs/architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — **start here** to orient in this codebase: what `bga` does today as one coherent system (both planes), with a full table of every extension beyond the original spec
- [CLI Reference](docs/cli.md) — every `bga` command and flag
- [Optimization Walkthrough](docs/optimization-walkthrough.md) — a real, worked example of iteratively finding and fixing build-efficiency problems with `bga`
- [Optimization Walkthrough (macro → micro)](docs/optimization-walkthrough-06.md) — the harder companion walkthrough: a real project with a badly-shaped graph *and* a badly-parallelized element, and an honest account of which of those `bga` helps you find today
- [Design Directions](docs/design-directions.md) — where the tool is going, argued separately for the two real ways it gets used: a local optimization helper, and a CI analytics/regression gate
- [Ingestion Pipeline](docs/ingestion-pipeline.md) — how `tools/bst_extract_run.py` turns a real BuildStream project + log into `bga` input, and its known limitations
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
