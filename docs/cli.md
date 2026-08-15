# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

## Installation

Ensure the package is installed in your environment:
```bash
pip install -e .
```

## Basic Usage

### Analyze a Build Run

The primary command analyzes a directory containing `run-context.json`, `graph.json`, and `trace.json` (the run-context/v9, graph/v9, and trace/v9 schemas, Part 32) - **not** a raw BuildStream cache/artifacts path directly; nothing in a live BuildStream cache is already in this shape.

```bash
bga analyze /path/to/run-directory
```

To produce a real run directory in this shape from an actual BuildStream project and build log in one step, see `tools/bst_extract_run.py` (`docs/ingestion-pipeline.md`) - or try the CLI right now against a checked-in sample fixture with no BuildStream install needed at all: `bga analyze tests/fixtures/golden/mixed_task_kinds` (see the README's Quick Start).

**Output:**
By default, `bga` prints a human-readable summary to stdout, leading with a synthesized **Key Findings** block (confidence headline, the single largest wait-category opportunity, the top elements by blast radius/criticality probability when `--diagnostics` ran, and certified headroom in plain language) before the detailed sections:
- **Confidence & Violations**: Overall confidence score, any failed hard gates, and a one-line summary per violation - previously only visible via `--format json`.
- **Certified Floors**: $T_\infty$, Lower Bound ($LB$), Certified Headroom, and an Efficiency Score ($LB$ / total duration, 0.0-1.0) - measures scheduling efficiency of the observed work, not whether that work itself is minimal; see Critical Path for the latter. $LB$/Efficiency Score certify against this run's *recorded* resource capacities (`--builders`/`--fetchers`/`--pushers`), not real host CPU cores - a native build system's own internal parallelism (`--max-jobs`, e.g. `make -jN`) is a separate axis `bga` does not model here, and the two can genuinely compete for the same cores (see `docs/scenarios/UX-09-builders-max-jobs-joint-optimization.md`'s real evidence). A one-line note to this effect always accompanies the Certified Floors block, naming this run's own real numbers when a `resource_oversubscription` violation was detected for it (see `docs/scenarios/UX-12-capture-native-max-jobs-and-host-cores.md`). When the run declares its own CPU budget (`--cpu-budget` at extraction time, e.g. because a cgroup CPU quota isn't visible to raw host-core detection), that declared budget - not the detected host core count - governs this check (see `docs/scenarios/UX-15-declared-cpu-budget-overrides-host-detection.md`).
- **Efficiency Metrics**: Parallelism, Utilization, and Attribution breakdown.
- **Critical Path**: The sequence of tasks determining the minimum build time.
- **Bottlenecks**: Elements with high blast radius or criticality probability.

The Key Findings/Confidence blocks are presentation-only, shown for the full `analyze` report - `--format json`/`csv` and the section subcommands (`graph`/`floors`/`replay`/`utilisation`/`diagnostics`) are unaffected.

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
Run the deterministic replay scheduler to compute a feasible makespan ($T_C$) under the chosen scheduling heuristic - a counterfactual model for scheduler comparison, capacity sweeps, and model slack (Part 18), not a claim that $T_C$ is the mathematically optimal schedule:
```bash
bga analyze /path/to/run --replay
```
You can specify the scheduling heuristic:
- `lpt` (Longest Processing Time first) - Default; a common, reasonable heuristic, not guaranteed optimal.
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

`floors` accepts the same `--cold`/`--allow-partial-cold`/`--history-dir` flags as `analyze` (matching the spec's own `bga floors RUN --cold` example). `replay` accepts `--heuristic`; `sweep` has its own `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags and isn't a slice of `analyze`'s output at all - it runs a series of replay simulations across a capacity range and reports predicted `T_C`, normalized improvement, and the diminishing-returns "knee" point per capacity value. Every replay/task duration in that sweep is fixed to what was actually observed - the model does not account for real CPU contention as concurrent `PROCESS` usage rises (`docs/scenarios/UX-09-builders-max-jobs-joint-optimization.md`'s own real evidence: raising `--builders` can make a real build *slower*, not just plateau, once cores are oversubscribed), so `bga sweep`'s own text/JSON output always carries an explicit caveat to this effect (`docs/scenarios/UX-14-sweep-replay-blind-to-contention-slowdown.md`) - treat the predicted curve as a shape, not an exact runtime prediction (Part 19). `graph` has its own `--by-kind` flag (P4-12, non-spec additive signal): `bga graph /path/to/run --by-kind` also shows aggregate stats (count, total/avg observed duration) grouped by each element's real BuildStream plugin kind (`import`/`manual`/`junction`/`stack`/...) - off by default, since it's extra detail beyond the base graph section.

## `bga compare` — Run-to-Run Comparison

Not a spec-mandated command (`docs/scenarios/UX-01`) - compares a baseline run against a candidate run and reports signed deltas in certified floors, efficiency score, and attribution, plus a verdict:

```bash
bga compare /path/to/before-run /path/to/after-run
bga compare /path/to/before-run /path/to/after-run --format json | jq '.verdict'
```

The verdict is one of `improved`/`regressed`/`no significant change` (a >=1% change in total build duration, relative to the baseline, is the significance threshold), always followed by an explicit caveat when either run's confidence is below the "high" band, and a warning when the two runs' graphs share fewer than half their element UIDs (they may not even be the same project). Exit code is always 0 for a successful comparison regardless of verdict - comparing is not itself a failure condition (a CI gate that fails the pipeline on regression is a separate, not-yet-built concern, `docs/scenarios/UX-03`). `--capacity`, if given, applies symmetrically to both runs.

## Example Workflows

### 1. Quick Efficiency Check
Get a quick overview of build efficiency:
```bash
bga analyze /path/to/run-directory
```

### 2. Generate JSON Report for CI
Integrate into a CI pipeline to track metrics over time:
```bash
bga analyze /path/to/run-directory --format json --output metrics.json
# Then process with jq, e.g. (certified_headroom, not certified_headroom_us -
# confirmed against a real --format json run):
# jq '.floors.certified_headroom' metrics.json
```

### 3. Simulate Hardware Upgrade
Estimate build time improvement if moving from 4 to 16 cores:
```bash
# Current 4-core simulation
bga analyze /path/to/run-directory --capacity 4 --replay

# Hypothetical 16-core simulation
bga analyze /path/to/run-directory --capacity 16 --replay
```

### 4. Deep Dive into Bottlenecks
Identify which elements to optimize for maximum speedup:
```bash
# criticality_probability is a JSON *object* keyed by element UID
# (confirmed against a real --format json run), not an array - to_entries
# converts it to an array of {key, value} pairs before sorting.
bga analyze /path/to/run-directory --diagnostics --format json | \
  jq '.signals.criticality_probability | to_entries | sort_by(.value.probability) | reverse | .[0:10]'
```

## Exit Codes

- `0`: Success.
- `1`: General error (e.g., invalid arguments, missing files).
- `2`: Data ingestion failure (e.g., malformed v9 artifacts).
- `3`: Analysis failure (e.g., graph cycles detected).

## See Also

- [Project README](../README.md)
- [v9 Specification](../docs/specification.md)
