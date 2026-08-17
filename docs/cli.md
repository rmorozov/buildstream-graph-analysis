# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

This covers the `bga` command itself — the whole-project analysis plane. For real per-process tracing *inside* one element's own sandbox (a separate tool, `tools/bst_native_build_tracer.py`, with its own Chrome Trace export), see [`docs/architecture.md`](architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

## One entry point (`UX-67`)

`bga` dispatches to the producer programs in `tools/` as well as running
its own analysis subcommands, so a session reads as one tool:

```bash
bga wrap    PROJECT build.log -- bst build TARGET   # capture a log bga can read
bga extract PROJECT build.log run/                  # log + project -> run directory
bga analyze run/                                    # the analysis
bga capture run PROJECT native.json -- bst build T  # Plane 2, inside the sandboxes
bga correlate run/ native.json                      # join the two planes
```

Before this, the same workflow alternated between `bga <cmd>` and
`python3 -m tools.<module>` at nearly every step — 74 occurrences across
the docs and CI.

**The tools are still separate programs**, and deliberately so: the
analyzer is a library with a stable contract, and each tool in `tools/`
is independently useful and independently testable. Every one of them
remains runnable directly, unchanged:

```bash
python3 -m tools.bst_extract_run PROJECT build.log run/   # still works
```

`bga --help` lists each alias with the module it wraps, so a script that
wants the underlying program can find it. Dispatch is lazy — only the
module actually invoked is imported, so `bga analyze` does not pay to
import the native tracer and the trace converters on every run.

| alias | wraps |
|---|---|
| `bga wrap` | `tools.bst_run_wrapped` |
| `bga extract` | `tools.bst_extract_run` |
| `bga capture` | `tools.bst_native_build_tracer` |
| `bga rebuild-set` | `tools.bst_rebuild_set` |
| `bga checkout-cost` | `tools.bst_checkout_cost` |
| `bga run-context` | `tools.bst_run_context` |
| `bga graph-from-show` | `tools.bst_show_to_graph` |
| `bga log-to-chrome` | `tools.bst_log_to_chrome_trace` |
| `bga chrome-to-trace` | `tools.chrome_trace_to_bga_trace` |
| `bga native-to-chrome` | `tools.native_trace_to_chrome_trace` |
| `bga cross-check` | `tools.bga_cross_check` |
| `bga gen-synthetic` | `tools.gen_synthetic_scale_run` |

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

The verdict is one of `improved`/`regressed`/`no significant change` (a >=1% change in total build duration, relative to the baseline, is the significance threshold), always followed by an explicit caveat when either run's confidence is below the "high" band, and a warning when the two runs' graphs share fewer than half their element UIDs (they may not even be the same project). Exit code is 0 for a successful comparison regardless of verdict by default - comparing is not itself a failure condition. `--capacity`, if given, applies symmetrically to both runs.

### CI Regression Gate (`--fail-on-regression`)

Not spec-mandated (`docs/scenarios/UX-03`) - opt-in gating mode for a CI pipeline that wants to actually *fail* on a genuine regression, not just report it:

```bash
bga compare /path/to/baseline-run /path/to/candidate-run --fail-on-regression
```

Exits `4` (a distinct code from 1/2/3, which all mean "`bga` itself failed" - see Exit Codes below) when the candidate run's real total duration (Part 4.3) regressed beyond the threshold - by default, the same >=1% significance band the verdict already uses, i.e. it fails exactly when the report's own verdict says `REGRESSED`, not a second, silently-different definition. Override the threshold with `--regression-threshold PCT` (e.g. `--regression-threshold 5` to only fail on a regression of 5% or more). `total_duration_us` is the one primary gating metric - deliberately not an ambiguous multi-metric combination.

A low-confidence comparison (either run's confidence below the "high" band) **fails open**: exits `0` with a warning printed to stderr, rather than blocking a pipeline on a possibly-noisy signal. The comparison report itself is always printed to stdout/`--output` regardless of the gate outcome, so a failing pipeline still shows *why*.

Worked GitHub Actions example - extract two runs and gate on the comparison:

```yaml
- name: Extract baseline and candidate runs
  run: |
    bga extract "$PROJ" baseline-build.log runs/baseline
    bga extract "$PROJ" candidate-build.log runs/candidate

- name: Fail if the candidate build regressed
  run: |
    bga compare runs/baseline runs/candidate --fail-on-regression
```

The job fails (exit `4`) only on a real, high-confidence regression; a genuine improvement, a change within tolerance, or a low-confidence comparison all let the job continue.

Pass `--fail-on-low-confidence` (`docs/scenarios/UX-40`) to treat "this comparison was too low-confidence to gate on" as a failure rather than failing open - a gate that silently stops gating still reports green, and some pipelines would rather see that.

### CI Efficiency Gate (`--fail-on-efficiency-regression`, `--min-efficiency`)

Not spec-mandated (`docs/scenarios/UX-39`). The duration gate above answers *"did the build get slower"*. That is the wrong question when a project is legitimately growing: adding three new elements makes the build slower, and a duration gate cannot tell that apart from a real regression. The question a build owner actually wants gated is **"adding work is allowed; adding work *inefficiently* is not."**

```bash
# fail if the build became meaningfully less efficient than the baseline
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression

# ...or state an absolute floor, with no baseline needed at all
bga compare runs/baseline runs/candidate --min-efficiency 0.45
```

Exits `5` - a code distinct from `4`, so a pipeline can warn on "slower" and fail on "less efficient", or vice versa. Gates on **Dispatch Occupancy** (`floors.occupancy_ratio`, `docs/scenarios/UX-27`), which is invariant to how much work the build does: adding well-parallelized elements barely moves it, adding serialized ones moves it sharply.

Real, measured illustration on one project (`examples/06-macro-micro-optimization`), same runner:

| change | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| two more fan-out libraries added | 25.98s → 26.64s (+2.5%) | **fails** (exit 4) | 60.0% → 73.8% | passes |
| graph serialized + one element pinned to `-j1` | 27.50s → 39.57s | fails | 63.0% → 27.8% | **fails** (exit 5) |
| `--builders 8 --max-jobs 8` on a 4-core host | 27.50s → 32.66s | fails | 63.0% → 48.6% | **fails** (exit 5) |
| nothing changed (repeat capture) | 25.98s → 24.07s | fires on ±1% noise | 60.0% → 59.0% | passes |

Two knobs:

- `--max-efficiency-drop PP` - how many **percentage points** of occupancy may be lost before failing. Default `5.0`, derived rather than guessed: three repeat captures of an unchanged project on one real runner spread **1.0pp** of occupancy (and 7.4% of wall-clock, which is why the duration gate's own 1% default fires on noise). Re-derive it the same way on your own runner rather than trusting the default.
- `--min-efficiency RATIO` - an absolute floor (`0.0`-`1.0`) on the candidate run's own occupancy, consulting no baseline. This is what makes *"we accept 55%, we do not accept 30%"* expressible on a first run, and what stops a slow drift that no single delta ever trips. No default: what counts as acceptable is a statement about your project, not a universal constant.

The efficiency gate inherits the same low-confidence fail-open rule as the duration gate, and the same `--fail-on-low-confidence` opt-out.

## `bga correlate` — Join the Two Planes

```bash
bga correlate RUN_DIRECTORY NATIVE_REPORT.json [-f text|json]
```

Joins this run's whole-project analysis (Plane 1) with a native trace report of the *same build* (Plane 2, from `tools/bst_native_build_tracer.py run`) on **element UID** — the only contract between the planes.

It answers what neither plane can alone. Plane 1 knows an element dominates the critical path; Plane 2 knows what happened inside it; only the join says what to do:

```
What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 25% of the critical path but runs at only 0.85 cores busy - it is waiting,
      not computing, and its native build asked for -j1: remove `notparallel` / raise
      its job count before touching its sources
    (81% of this element's processes were measured)
```

Capture both artifacts from one build:

```bash
bga capture run --wrapped-log /tmp/plane1.log \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga correlate /tmp/run /tmp/plane2.json
```

Notes on reading it:

- **Ranking is Plane 1's.** Plane 2 explains the top of that list and never reorders it — the question "what should I optimize" is answered by whole-project impact.
- **A negative result is a result.** "Already compute-bound — nothing to gain from its parallelism" tells you to stop looking inside that element.
- **Coverage is carried through.** A recommendation built on 81% of an element's processes says so (`UX-45`), and elements Plane 1 ranks that Plane 2 never traced are named rather than passed over.
- The two planes' timelines are **not** merged and cannot be — see [`docs/architecture.md`](architecture.md). This is a join, and is deliberately named as one.

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
- `4`: `bga compare --fail-on-regression` only - the analyzed build itself regressed beyond the threshold. Distinct from 1/2/3, which all mean `bga` itself failed to run - this means `bga` ran successfully and is reporting a real regression (`docs/scenarios/UX-03`).
- `5`: `bga compare --fail-on-efficiency-regression`/`--min-efficiency` only - the build became meaningfully *less efficient*, whether or not it also got slower. Deliberately distinct from `4`: "slower" and "less efficient" are different verdicts and often different teams' problems (`docs/scenarios/UX-39`).

## See Also

- [Project README](../README.md)
- [Architecture Overview](architecture.md) — both analysis planes, and every extension beyond the original spec
- [v9 Specification](../docs/specification.md)
