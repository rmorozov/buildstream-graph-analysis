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

Certified Floors:
  T∞ (observed critical path): 118.00s
  LB (resource lower bound):   118.00s
  Certified Headroom:          24.00s
  T_C (replay makespan):       118.00s

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
- **Critical Path** — the one chain of elements that determines total build time. Speeding up anything *not* on this path doesn't shorten the build at all — this is always where to look first for reducing the work itself, not just rescheduling it.
- **Biggest Opportunity / Attribution Breakdown** — where wall-clock time actually went, by category (execution, waiting on a dependency, waiting on a resource, waiting on the scheduler, idle, retries). Every category sums to exactly the total build time — nothing is hidden or double-counted.
- **Elements Most Worth Optimizing First** — ranked by blast radius (how many other elements depend on it): fixing a slow element near the root of your graph helps every downstream element too.
- If a hard gate fails (e.g. `critical_path_coverage`), the violation now names the specific missing element(s) and, where known, whether it's a structural element (`stack`/`import`/...) that never had a real compute task or a genuine gap worth investigating — no need to cross-reference the critical-path list by hand.

## Use it on your real project

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/ingestion-pipeline.md
bst -C /path/to/your/project build <targets> > build.log 2>&1
python3 -m tools.bst_extract_run /path/to/your/project build.log /tmp/my-run   # from the repo root
bga analyze /tmp/my-run --diagnostics
```

Then iterate: make a change, rebuild, extract a new run, and compare it against the baseline:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

This reports a signed delta for every certified floor, the efficiency score, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) - gated on confidence, with a warning if the two runs don't look like the same project. `bga compare --fail-on-regression` turns this into a CI gate (exit code 4 on a real regression) — see `docs/cli.md`.

Other useful commands:

```bash
bga analyze /tmp/my-run --format json > report.json      # machine-readable, for CI/tracking over time
bga sweep /tmp/my-run --resource PROCESS --min-capacity 1 --max-capacity 16  # "how many builders is enough?"
bga replay /tmp/my-run --capacity 16                      # simulate a hardware upgrade
```

The `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` subcommands are thin, narrower slices of the same full `analyze` report — reach for one of them instead of grepping `analyze`'s output for a single question. Full reference: [`docs/cli.md`](docs/cli.md).

## Advanced: looking inside one element (Plane 2)

Everything above answers *"across the whole build, where did the time go and what's the ceiling on making it faster?"* — that's as deep as a BuildStream log itself goes: one start/end timestamp per element, nothing about what happened *inside* its sandbox. A second, separate tool answers *"inside this one element, is its own native build system (`make -jN`, `cmake --build`, ...) actually parallelizing well, or silently serializing / doing redundant work?"* — real per-process tracing via an `LD_PRELOAD` hook inside the sandbox, not a guess from timing alone:

```bash
python3 -m tools.bst_native_build_tracer run /path/to/your/project report.json -- bst build <target>
```

This also detects real operations repeated independently across *multiple* elements' sandboxes (e.g. the same compiler-ABI probe re-run once per element) and can export a [Chrome Trace](https://ui.perfetto.dev)-viewable timeline, standalone or combined with the whole-project view above into one file. Full picture, real evidence, and every command: [`docs/architecture.md`](docs/architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

## Documentation

- [`docs/architecture.md`](docs/architecture.md) — **start here** to orient in this codebase: what `bga` does today as one coherent system (both planes), with a full table of every extension beyond the original spec
- [CLI Reference](docs/cli.md) — every `bga` command and flag
- [Optimization Walkthrough](docs/optimization-walkthrough.md) — a real, worked example of iteratively finding and fixing build-efficiency problems with `bga`
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
