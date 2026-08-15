# BuildStream Build Efficiency Analyzer (bga)

`bga` reads a BuildStream build trace and tells you three things: **how much faster this build could possibly be** (a proven lower bound, not a guess), **exactly where the time actually went** (per-element attribution, not aggregate stats), and **what to fix first** (ranked by how many other elements depend on it).

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

## Use it on your real project

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/ingestion-pipeline.md
bst -C /path/to/your/project build <targets> > build.log 2>&1
PYTHONPATH=. python tools/bst_extract_run.py /path/to/your/project build.log /tmp/my-run   # from the repo root
bga analyze /tmp/my-run --diagnostics
```

Then iterate: make a change, rebuild, extract a new run, and compare it against the baseline:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

This reports a signed delta for every certified floor, the efficiency score, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) - gated on confidence, with a warning if the two runs don't look like the same project.

Other useful commands:

```bash
bga analyze /tmp/my-run --format json > report.json      # machine-readable, for CI/tracking over time
bga sweep /tmp/my-run --resource PROCESS --min-capacity 1 --max-capacity 16  # "how many builders is enough?"
bga replay /tmp/my-run --capacity 16                      # simulate a hardware upgrade
```

## Documentation

- [CLI Reference](docs/cli.md) — every command and flag
- [Ingestion Pipeline](docs/ingestion-pipeline.md) — how `tools/bst_extract_run.py` turns a real BuildStream project + log into `bga` input, and its known limitations
- [v9 Specification](docs/specification.md) — the underlying analysis specification (ground truth for what every number means)
- [`docs/scenarios/`](docs/scenarios/README.md) — active backlog of usability/workflow gaps

## Development

```bash
make test     # run the full suite
make lint     # ruff
make dev-run  # sample report, fast smoke check
```

## License

MIT
