# BuildStream Build Efficiency Analyzer (bga)

A comprehensive tool for analyzing BuildStream build efficiency based on the v9 specification. This tool implements certified floors, dependency attribution, replay scheduling, and advanced diagnostics to help optimize build pipelines.

## Features

- **Certified Floors**: Computes $T_\infty$ (critical path), Lower Bound ($LB$), and Certified Headroom
- **Dependency Attribution**: Blame chain analysis showing exactly where time is spent
- **Replay Scheduler**: Deterministic simulation of optimal scheduling under resource constraints
- **CPU Utilization**: Multi-resource utilization tracking (CPU, IO, network)
- **Advanced Diagnostics**: Blast radius, criticality probability, and wall-clock shares
- **Cold Structural Analysis**: Historical trend detection and bottleneck identification

## Installation

```bash
pip install -e .
```

## Testing

The project uses pytest for testing. Run all tests using the Makefile:

```bash
make test          # Run all tests with verbose output
make test-e2e      # Run end-to-end tests only
```

Or run pytest directly:

```bash
pytest             # Run all tests
pytest -v          # Verbose output
pytest --cov=bga   # With coverage report
```

Clean build artifacts and temporary files:

```bash
make clean         # Remove __pycache__, *.pyc, *.egg-info, and other temp files
```

## Quick Start

`bga` reads a directory containing `run-context.json`/`graph.json`/`trace.json` (the run-context/v9, graph/v9, and trace/v9 schemas, Part 32) - it does **not** read a raw BuildStream cache/artifacts path directly. The fastest way to see a real report, with zero BuildStream install needed:

```bash
pip install -e .
bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics
```

(`make dev-run` does the same thing, plus `make dev-run ARGS=--large` for a bigger, more realistic sample.)

To analyze a real BuildStream project, produce a run directory in the shape `bga` expects from your own project + build log in one step:

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/ingestion-pipeline.md
bst -C /path/to/your/project build <targets> > build.log 2>&1
PYTHONPATH=. python tools/bst_extract_run.py /path/to/your/project build.log /tmp/my-run   # run from the repo root
bga analyze /tmp/my-run --diagnostics
```

Generate a JSON report, or simulate different hardware capacities:

```bash
bga analyze /tmp/my-run --format json > report.json
bga analyze /tmp/my-run --capacity 16 --replay
```

## Documentation

- [CLI Reference](docs/cli.md) - Complete command-line interface documentation
- [Ingestion Pipeline](docs/ingestion-pipeline.md) - How `tools/bst_extract_run.py` and friends turn a real BuildStream project + log into `bga` input
- [v9 Specification](docs/specification.md) - The underlying analysis specification

## Example Output

Real output (trimmed) from `bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics`:

```
============================================================
Build Efficiency Report
============================================================
Total Duration: 0.0s

Key Findings:
  Confidence: 0.88 (high)
  Biggest Opportunity: 14.3% of wall-clock time is UNTRACKED TAIL (0.00s)
  Elements Most Worth Optimizing First (by blast radius):
    1. base.bst (2 downstream elements)
    2. lib.bst (1 downstream elements)
    3. app.bst (0 downstream elements)

Certified Floors:
  T∞ (observed critical path): 0.01s
  LB (resource lower bound):   0.01s
  Certified Headroom:          0.00s

Attribution Breakdown:
  Execution On Chain Us         0.01s (100.0%)
  Dependency Wait Us            0.00s (  0.0%)
  ...

Critical Path Length: 3 elements
  Path: base.bst → lib.bst → app.bst
```

## Project Structure

```
bga/
├── ingest/          # Data loaders for v9 schemas
├── normalize/       # Timestamp quantization and ordering
├── occupancy/       # Sweep-line occupancy engine
├── graph/           # Dependency graph analysis
├── attribution/     # Blame chain computation
├── replay/          # Deterministic replay scheduler
├── diagnostics/     # Advanced signals and metrics
├── structural/      # Cold structural analysis
└── analyzer.py      # Main orchestration
```

## License

MIT