# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

## Installation

Ensure the package is installed in your environment:
```bash
pip install -e .
```

## Basic Usage

### Analyze a Build Run

The primary command analyzes a directory containing BuildStream run data (specifically `run-context/v9`, `graph/v9`, and `trace/v9` artifacts).

```bash
bga analyze /path/to/buildstream/cache/artifacts/run-<uuid>
```

**Output:**
By default, `bga` prints a human-readable summary to stdout, including:
- **Certified Floors**: $T_\infty$, Lower Bound ($LB$), and Certified Headroom.
- **Efficiency Metrics**: Parallelism, Utilization, and Attribution breakdown.
- **Critical Path**: The sequence of tasks determining the minimum build time.
- **Bottlenecks**: Elements with high blast radius or criticality probability.

### Options

#### Output Format
Control the output format using `--format` (or `-f`):
- `text` (default): Human-readable summary.
- `json`: Machine-readable JSON object (suitable for piping to `jq`).
- `csv`: Comma-separated values for attribution data.

```bash
bga analyze /path/to/run --format json > report.json
```

#### Resource Capacity
Override the detected system capacity (useful for simulating different hardware):
```bash
bga analyze /path/to/run --capacity 16
```
*Note: This affects the calculation of the Lower Bound ($LB$) and Replay Makespan ($T_C$).*

#### Replay Simulation
Run the deterministic replay scheduler to compute the optimal makespan ($T_C$) under perfect scheduling:
```bash
bga analyze /path/to/run --replay
```
You can specify the scheduling heuristic:
- `lpt` (Longest Processing Time first) - Default, often optimal.
- `spt` (Shortest Processing Time first).
- `fifo` (First In First Out).
- `depth` (Dependency depth priority).

```bash
bga analyze /path/to/run --replay --heuristic lpt
```

#### Diagnostics
Enable advanced diagnostic signals (adds computation time):
```bash
bga analyze /path/to/run --diagnostics
```
This computes:
- **Blast Radius**: Number of downstream dependents for each element.
- **Criticality Probability**: Likelihood an element appears on the critical path under duration variance.
- **Wall-Clock Shares**: Attribution of wall-clock time to specific elements.

#### Output File
Save the report to a file instead of stdout:
```bash
bga analyze /path/to/run --output report.txt
```

#### Cold Structural Floor (advisory)
Compute the advisory cold structural floor (`T∞,cold`) using prior runs' observed durations as an estimate source. Off by default - never affects `LB`, `certified_headroom`, primary `confidence`, or measured attribution:
```bash
bga analyze /path/to/run --cold --history-dir /path/to/prior-run-1 --history-dir /path/to/prior-run-2
```
- `--cold` alone (no `--history-dir`) reports `T∞,cold` as unavailable - there's nothing to estimate from.
- By default, if any element on the resolved cold critical path has no resolvable historical duration, `T∞,cold` reports as unavailable rather than a misleading partial number.
- `--allow-partial-cold` (only meaningful together with `--cold`; a no-op with a warning if passed alone) instead publishes a value with `partial=true`/`confidence=low` in that case.

## Advanced Commands

### Version
Check the installed version:
```bash
bga --version
```

### Verbose Logging
Enable debug logging to troubleshoot ingestion or normalization issues:
```bash
bga analyze /path/to/run --verbose
```

## Section Subcommands

`analyze` is the primary command and produces the full report (every section together). `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` are thin aliases over the same analysis pipeline - each restricts output to just its own section, so you don't have to grep a full report or a `jq` filter out of `--format json` for a narrow question. They accept the same relevant `analyze` flags (`--format`/`--output`/`--capacity`/`--verbose`/`--quiet`/`--log-file`, plus each subcommand's own natural options) and the same exit-code contract.

```bash
bga graph /path/to/run          # static dependency graph, critical path, structural metrics
bga floors /path/to/run --cold  # certified/advisory floors (T-infinity, LB, certified headroom, cold floor)
bga replay /path/to/run --heuristic spt   # deterministic replay makespan (T_C)
bga sweep /path/to/run --resource PROCESS --min-capacity 1 --max-capacity 16  # capacity sweep (Part 19)
bga utilisation /path/to/run    # CPU utilisation accounting
bga diagnostics /path/to/run    # blast radius, criticality probability, wall-clock shares
```

`floors` accepts the same `--cold`/`--allow-partial-cold`/`--history-dir` flags as `analyze` (matching the spec's own `bga floors RUN --cold` example). `replay` accepts `--heuristic`; `sweep` has its own `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags and isn't a slice of `analyze`'s output at all - it runs a series of replay simulations across a capacity range and reports predicted `T_C`, normalized improvement, and the diminishing-returns "knee" point per capacity value.

## Example Workflows

### 1. Quick Efficiency Check
Get a quick overview of build efficiency:
```bash
bga analyze ~/.buildstream/cache/artifacts/run-12345
```

### 2. Generate JSON Report for CI
Integrate into a CI pipeline to track metrics over time:
```bash
bga analyze ~/.buildstream/cache/artifacts/run-12345 --format json --output metrics.json
# Then process with jq, e.g.:
# jq '.floors.certified_headroom_us' metrics.json
```

### 3. Simulate Hardware Upgrade
Estimate build time improvement if moving from 4 to 16 cores:
```bash
# Current 4-core simulation
bga analyze ~/.buildstream/cache/artifacts/run-12345 --capacity 4 --replay

# Hypothetical 16-core simulation
bga analyze ~/.buildstream/cache/artifacts/run-12345 --capacity 16 --replay
```

### 4. Deep Dive into Bottlenecks
Identify which elements to optimize for maximum speedup:
```bash
bga analyze ~/.buildstream/cache/artifacts/run-12345 --diagnostics --format json | \
  jq '.signals.criticality_probability | sort_by(.probability) | reverse | .[0:10]'
```

## Exit Codes

- `0`: Success.
- `1`: General error (e.g., invalid arguments, missing files).
- `2`: Data ingestion failure (e.g., malformed v9 artifacts).
- `3`: Analysis failure (e.g., graph cycles detected).

## See Also

- [Project README](../README.md)
- [v9 Specification](../docs/specification.md)
