# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

This is the reference. If you are pointing `bga` at a real project for the first time, read [`docs/guides/real-project.md`](real-project.md) instead — it walks the whole cycle end to end with real output at every step, and links back here for flags.

This covers the `bga` command itself — the whole-project analysis plane. For real per-process tracing *inside* one element's own sandbox (a separate tool, `tools/bst_native_build_tracer.py`, with its own Chrome Trace export), see [`docs/design/architecture.md`](../design/architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

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
`python3 -m tools.<module>` at nearly every step — 74 occurrences across  <!-- docs-style: allow-direct-module -->
the docs and CI.

**The tools are still separate programs**, and deliberately so: the
analyzer is a library with a stable contract, and each tool in `tools/`
is independently useful and independently testable. Every one of them
remains runnable directly, unchanged:

```bash
python3 -m tools.bst_extract_run PROJECT build.log run/   # still works (docs-style: allow-direct-module)
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
| `bga cache-logs` | `tools.bst_cache_logs` |
| `bga baseline` | `tools.bst_baseline_set` |

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

To produce a real run directory in this shape from an actual BuildStream project and build log in one step, see `tools/bst_extract_run.py` (`docs/spec/ingestion-pipeline.md`) - or try the CLI right now against a checked-in sample fixture with no BuildStream install needed at all: `bga analyze tests/fixtures/golden/mixed_task_kinds` (see the README's Quick Start).

**Output:**
By default, `bga` prints a human-readable summary to stdout, leading with a synthesized **Key Findings** block (confidence headline, the single largest wait-category opportunity, the top elements by blast radius/criticality probability when `--diagnostics` ran, and certified headroom in plain language) before the detailed sections:
- **Confidence & Violations**: Overall confidence score, any failed hard gates, and a one-line summary per violation - previously only visible via `--format json`.
- **Certified Floors**: $T_\infty$, Lower Bound ($LB$), Certified Headroom, and an Efficiency Score ($LB$ / **horizon**, 0.0-1.0 — the horizon is first-task-start to last-task-finish, *not* total duration, which also contains the untracked head and tail; on `tests/fixtures/golden/mixed_task_kinds` the two give 1.00 and 0.875) - measures scheduling efficiency of the observed work, not whether that work itself is minimal; see Critical Path for the latter. $LB$/Efficiency Score certify against this run's *recorded* resource capacities (`--builders`/`--fetchers`/`--pushers`), not real host CPU cores - a native build system's own internal parallelism (`--max-jobs`, e.g. `make -jN`) is a separate axis `bga` does not model here, and the two can genuinely compete for the same cores (see `docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md`'s real evidence). A one-line note to this effect always accompanies the Certified Floors block, naming this run's own real numbers when a `resource_oversubscription` violation was detected for it (see `docs/backlog/scenarios/UX-0012-capture-native-max-jobs-and-host-cores.md`). When the run declares its own CPU budget (`--cpu-budget` at extraction time, e.g. because a cgroup CPU quota isn't visible to raw host-core detection), that declared budget - not the detected host core count - governs this check (see `docs/backlog/scenarios/UX-0015-declared-cpu-budget-overrides-host-detection.md`).
- **Efficiency Metrics**: Parallelism, Utilization, and Attribution breakdown.
- **Critical Path**: The sequence of tasks determining the minimum build time.
- **Bottlenecks**: Elements with high blast radius or criticality probability.

The Key Findings/Confidence blocks are shown for the full `analyze` report only - the section subcommands (`graph`/`floors`/`replay`/`utilisation`/`diagnostics`) and `--format csv` do not render them. They are **not** presentation-only: since `UX-75` every conclusion in them is computed once in `bga/findings.py` and published to `--format json` as the `findings` array described below, so the two formats cannot disagree.

### Options

#### Output Format
Control the output format using `--format` (or `-f`):
- `text` (default): Human-readable summary.
- `json`: Machine-readable JSON object (suitable for piping to `jq`).
- `csv`: Comma-separated values for attribution data.

```bash
bga analyze /path/to/run --format json > report.json
```

The JSON carries a **`findings` array** — the same conclusions the text report's `Key Findings` block renders, as data. Each entry has a stable `id` (what a CI gate keys on, and what a run-to-run diff joins on — it does not change when the wording does), a `severity` (`critical`/`high`/`medium`/`info`), the `elements` it concerns, and an `evidence` object with the raw numbers behind the sentence. Both formats render from this one list, so they cannot disagree, and a consumer never has to re-derive a threshold from `bga/report/text.py`:

#### The full `findings[].id` set

`id` is the contract — it does not change when the wording does, so a CI gate keys on it. Every id `bga` can emit, and nothing else:

`bga analyze --format json` → `.findings[].id` (all defined in `bga/findings.py`; the set is test-enforced against this table):

| id | severity | what it says |
|---|---|---|
| `build-failed` | critical | one or more elements ended in FAILURE; every figure below describes an incomplete build |
| `failed-task-time` | high | how much of the measured chain was work that was thrown away |
| `confidence` | varies | the confidence headline and any failed hard gates |
| `run-mode-incremental` | info | this run was incremental, so its durations are not a cold-build baseline |
| `cache-hit-ratio` | varies | how much of the project the cache reused, and for the requested target's own closure. On a caches-off run it reports the fact at `info` rather than banding it (`UX-86`) |
| `cache-transfer-cost` | medium | this build spent a notable share of wall-clock moving artifacts rather than making them |
| `wait-category` | varies | the single largest non-execution wait category, when it clears the 1% floor |
| `execution-bound` | info | no wait category clears the floor — the time is in the work itself |
| `certified-headroom` | varies | proven room to improve scheduling without changing any element |
| `efficiency-score` | varies | how close the scheduler got to the certified floor |
| `time-concentration` | varies | which elements the critical path's duration is actually in |
| `mesh-graph` | info | the critical path is a small share of total duration — the graph, not the chain, is the constraint |
| `blast-radius-ranking` | varies | elements worth fixing first by downstream reach (needs `--diagnostics`) |
| `criticality` | varies | elements most likely to be on the critical path under duration variance (needs `--diagnostics`) |
| `optimization-horizon` | varies | what the build drops to after each of the next few fixes |
| `joint-saving` | varies | whether the recommended set's savings add up or overlap |
| `latent-heavies` | info | heavy elements off the critical path, worth nothing to fix today |

`bga correlate --format json` → `.actionable[].recommendations[].id` (9) and `.restructuring[].id` (1):

| id | severity | what it says |
|---|---|---|
| `pinned-to-one-job` | high | waiting rather than computing, and its native build asked for `-j1` |
| `underachieved-requested-jobs` | high | waiting rather than computing despite asking for more jobs |
| `waiting-not-computing` | high | waiting rather than computing, cause not named by Plane 2 |
| `already-compute-bound` | high | a negative result: nothing to gain from its parallelism |
| `cpu-concentration` | high | one binary is most of its measured CPU |
| `serialization-point` | high | a single process holds a material share of its wall time |
| `peak-memory` | medium | its largest process's peak RSS, to multiply by concurrency |
| `redundant-operation` | medium | it pays for an operation other elements also run |
| `declared-not-used` | info | opened no file staged by a declared build dependency — evidence, not a verdict |
| `unread-gating-chain` | high | a *group* of never-read edges chains elements along the critical path (`UX-82`) |

`bga cache-logs --format json` → `.findings[].id` (1), built in `tools/bst_cache_logs.py` rather than `bga/findings.py` because it reads BuildStream's own logs and, optionally, a Plane 2 report — neither of which the run-directory analyzer has:

| id | severity | what it says |
|---|---|---|
| `configure-tax` | varies | how much of this log tree's element time went to the build system configuring itself, who paid the most, and — with `--native-report` — the same figure measured from the traced process tree (`UX-102`) |

`bga cache-trend --format json` → `.findings[].id` (1):

| id | severity | what it says |
|---|---|---|
| `cache-trend-regression` | high | a trended cache metric on the newest run left the band its trailing window describes — the metric, both values and the band are in `evidence` (`UX-103`) |

A finding not in the run's output simply did not fire; ids are never emitted with an empty or placeholder value.

```bash
# Is this build chain-bound, and which elements is its time in?
bga analyze /path/to/run --format json \
  | jq '.findings[] | select(.id == "time-concentration") | .evidence'

# Anything critical or high, as a gate condition
bga analyze /path/to/run --format json \
  | jq -e '[.findings[] | select(.severity == "critical")] | length == 0'
```

#### Conditioning capacity advice on Plane 2 (`--plane2`) — `UX-83`

```bash
bga analyze /path/to/run --plane2 /path/to/native-report.json
bga sweep   /path/to/run --resource PROCESS --plane2 /path/to/native-report.json
```

The `RESOURCE WAIT` hint and `sweep`'s knee point are both replay-model answers, and the replay model does not know about CPU (`UX-09`/`UX-14`). Measured once on a real dual-plane capture: `analyze` said *"31.9% of wall-clock is RESOURCE WAIT — try `--capacity N` with a higher N"* and `sweep` put the knee at capacity 5, on a 4-core host — while `correlate` on the **same capture** named the real fix, an element pinned to `-j1`, worth −32.4% and costing no extra capacity.

With `--plane2`, both consult what was actually measured inside the sandboxes:

- a host Plane 2 measured as already CPU-saturated is told **not** to raise capacity, with the measurement quoted;
- an element pinned to `-j1` is named **first**, because intra-element parallelism is capacity you already have and, unlike `--builders`, it cannot contend with itself.

Without `--plane2` every line is byte-identical to before.

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
- `--cold` alone (no `--history-dir`) has nothing to estimate from. In `--format json` the cold fields are present and null; the **text report prints no cold line at all** rather than a line saying "unavailable" — absence is the report's way of saying a number was not computed, and it is the same in both formats in the sense that neither fabricates one.
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

`floors` accepts the same `--cold`/`--allow-partial-cold`/`--history-dir` flags as `analyze` (matching the spec's own `bga floors RUN --cold` example). `replay` accepts `--heuristic`; `sweep` has its own `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags and isn't a slice of `analyze`'s output at all - it runs a series of replay simulations across a capacity range and reports predicted `T_C`, normalized improvement, and the diminishing-returns "knee" point per capacity value. Every replay/task duration in that sweep is fixed to what was actually observed - the model does not account for real CPU contention as concurrent `PROCESS` usage rises (`docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md`'s own real evidence: raising `--builders` can make a real build *slower*, not just plateau, once cores are oversubscribed), so `bga sweep`'s own text/JSON output always carries an explicit caveat to this effect (`docs/backlog/scenarios/UX-0014-sweep-replay-blind-to-contention-slowdown.md`) - treat the predicted curve as a shape, not an exact runtime prediction (Part 19). `graph` has its own `--by-kind` flag (P4-12, non-spec additive signal): `bga graph /path/to/run --by-kind` also shows aggregate stats (count, total/avg observed duration) grouped by each element's real BuildStream plugin kind (`import`/`manual`/`junction`/`stack`/...) - off by default, since it's extra detail beyond the base graph section.

## `bga compare` — Run-to-Run Comparison

Not a spec-mandated command (`docs/backlog/scenarios/UX-01`) - compares a baseline run against a candidate run and reports signed deltas in certified floors, efficiency score, and attribution, plus a verdict:

```bash
bga compare /path/to/before-run /path/to/after-run
bga compare /path/to/before-run /path/to/after-run --format json | jq '.verdict'
```

The verdict is one of `improved`/`regressed`/`no significant change`/`not comparable (baseline has no measurable duration)` (a >=1% change in total build duration, relative to the baseline, is the significance threshold), always followed by an explicit caveat when either run's confidence is below the "high" band, and a **refusal** (`UX-78`) when the two runs are not comparable at all — either their graphs share fewer than half their element UIDs (they may not even be the same project) or one is a caches-off run and the other incremental. A refusal prints the failing check to stderr, prints no comparison, and exits **6** — deliberately not 4 or 5, so a CI job keying on the gates cannot read a wrong-artifact-path bug as a regression. `--allow-mismatch` restores the older behaviour: the warning is printed above the comparison and the exit code is the gates' own. Otherwise the exit code is 0 for a successful comparison regardless of verdict — comparing is not itself a failure condition. `--capacity`, if given, applies symmetrically to both runs.

### CI Regression Gate (`--fail-on-regression`)

Not spec-mandated (`docs/backlog/scenarios/UX-03`) - opt-in gating mode for a CI pipeline that wants to actually *fail* on a genuine regression, not just report it:

```bash
bga compare /path/to/baseline-run /path/to/candidate-run --fail-on-regression
```

Exits `4` (a distinct code from 1/2/3, which all mean "`bga` itself failed" - see Exit Codes below) when the candidate run's real total duration (Part 4.3) regressed beyond the threshold - by default, the same >=1% significance band the verdict already uses, i.e. it fails exactly when the report's own verdict says `REGRESSED`, not a second, silently-different definition. Override the threshold with `--regression-threshold PCT` (e.g. `--regression-threshold 5` to only fail on a regression of 5% or more). `total_duration_us` is the one primary gating metric - deliberately not an ambiguous multi-metric combination.

A refused comparison (`--allow-mismatch` not given, exit 6) is checked before any gate, since "these runs are not comparable" is not a verdict about the build. A low-confidence comparison (either run's confidence below the "high" band) **fails open**: exits `0` with a warning printed to stderr, rather than blocking a pipeline on a possibly-noisy signal. The comparison report itself is always printed to stdout/`--output` regardless of the gate outcome, so a failing pipeline still shows *why*.

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

Pass `--fail-on-low-confidence` (`docs/backlog/scenarios/UX-40`) to treat "this comparison was too low-confidence to gate on" as a failure rather than failing open - a gate that silently stops gating still reports green, and some pipelines would rather see that.

### CI Efficiency Gate (`--fail-on-efficiency-regression`, `--min-efficiency`)

Not spec-mandated (`docs/backlog/scenarios/UX-39`). The duration gate above answers *"did the build get slower"*. That is the wrong question when a project is legitimately growing: adding three new elements makes the build slower, and a duration gate cannot tell that apart from a real regression. The question a build owner actually wants gated is **"adding work is allowed; adding work *inefficiently* is not."**

```bash
# fail if the build became meaningfully less efficient than the baseline
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression

# ...or state an absolute floor, with no baseline needed at all
bga compare runs/baseline runs/candidate --min-efficiency 0.45
```

Exits `5` - a code distinct from `4`, so a pipeline can warn on "slower" and fail on "less efficient", or vice versa. Gates on **Dispatch Occupancy** (`floors.occupancy_ratio`, `docs/backlog/scenarios/UX-27`), which is invariant to how much work the build does: adding well-parallelized elements barely moves it, adding serialized ones moves it sharply.

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

### Flags reachable only from `--help`

Documented here because they exist and nothing user-facing said so:

- `bga sweep --calibration-dir DIR` (`UX-14` tier 2) — replaces the sweep's fixed-duration model with a contention-aware one calibrated from real runs in `DIR`. Without it the sweep's own caveat applies: the predicted curve is a shape, not a runtime prediction, because the replay model does not know about CPU.
- `bga capture run --invocation-log PATH` / `--argv-log PATH` / `--raw-log PATH` — where Plane 2 writes its own capture logs. `--invocation-log` defaults to a path beside the report (`UX-80`); `--no-invocation-log` turns it off.
- `bga cache-trend RUN...` — a series, oldest first: per-run hit ratio, transfer seconds and seconds per artifact, churn against the predecessor (with `UX-93`'s labels), and a finding when the newest run leaves the band its trailing window describes (`UX-103`). The noise model is `bga compare`'s, widened to the fixed rule when the measured band is narrower. Four runs minimum — three trailing plus the one being judged — and it says so rather than trending fewer.
- `bga baseline --glob 'captures/<project>/<commit>-<mode>-b<N>j<M>-*' -n 3 --candidate RUN` — assembles a baseline set from published capture refs and band-compares against it in one command (`UX-96`). Fetches the newest N, untars the refs that predate the uncompressed `run/`, refuses a set whose captures are not comparable (exit 6), and warns when the set was produced by more than one `bga` revision. Every member supplies the band, the newest is also the positional baseline — with three refs that is exactly the `MIN_BASELINE_RUNS` the band needs.
- `bga cache-logs [LOG_ROOT] --project NAME --native-report PLANE2.json` — Plane 3, BuildStream's own persisted element logs (`UX-91`). Needs no capture at all: it reads what BuildStream already wrote, defaulting to `$XDG_CACHE_HOME/buildstream/logs`. Reports the per-element phase breakdown, the sandbox tax (`UX-99`) and the configure tax (`UX-102`); `--native-report` adds the traced configure measurement from a Plane 2 report of the same build, beside the build tool's self-reported one.

## `bga correlate` — Join the Two Planes

```bash
bga correlate RUN_DIRECTORY NATIVE_REPORT.json [-f text|json]
```

Joins this run's whole-project analysis (Plane 1) with a native trace report of the *same build* (Plane 2, from `tools/bst_native_build_tracer.py run`) on **element UID** — the only contract between the planes.

It answers what neither plane can alone. Plane 1 knows an element dominates the critical path; Plane 2 knows what happened inside it; only the join says what to do:

```
What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 25% of the critical path and fixing it is worth 18.4s (24.1% of the build),
      but runs at only 0.85 cores busy - it is waiting, not computing, and its native
      build asked for -j1: remove `notparallel` / raise its job count before touching
      its sources
    - 81% of its measured CPU is one binary, `cc1plus` (885 process(es), 4353 CPU s) -
      this element is a `cc1plus` problem, so look there before anywhere else
    - `dwz` is a SINGLE process holding 138.6s of wall time - a serialization point no
      job count can help; it has to get faster or go away
    - its largest single process peaked at 1902 MB resident - multiply by however many
      elements build concurrently before raising `builders`
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
- **A restructuring finding comes first, when there is one** (`UX-82`). When a *group* of declared build edges was measured never-read *and* those edges chain elements along the critical path, the join names the chain as one finding and replays this run with those edges removed — same durations, same capacity — to say what removing them would be worth. Five per-element rows saying "`lib-b` never read `lib-a`" are five bricks; this is the wall. The hedge is unchanged: it recommends *checking* the edges, and says the projection is a replay, not a re-capture.
- **Rows are ordered by evidence strength.** A measured CPU concentration or a single-process serialization point leads; the declared-vs-used candidate, which the producer itself calls "evidence, not a verdict", comes last. Dependency pairs `UX-68` set aside as *aggregating* — a `stack` stages almost nothing of its own, so "nobody opened it" says nothing about it — are counted under the coverage line rather than mixed into the findings.
- **The ranking metric is `UX-70`'s realizable saving** — what the build would actually lose if the element became instant, which is the same number `bga analyze` ranks on, so the two commands cannot name different elements first. Share of the critical path is reported beside it because they routinely disagree: an element can hold a large share of a mesh graph and be worth very little to fix. If the metric saturates (every candidate carrying the same value), the report says so rather than presenting the alphabetical tiebreak as an impact order.
- **A negative result is a result.** "Already compute-bound — nothing to gain from its parallelism" tells you to stop looking inside that element.
- **Elements with identical findings share one block** (`UX-89`). Six sibling libraries that are all compute-bound and all `cc1plus`-dominated are one story, not six; the block names them, collapses their figures to ranges, and carries the total worth, while `--format json` still publishes every element separately. A group takes the position of its strongest member, so grouping never reorders what leads, and a finding whose figures do not generalize (peak RSS, a redundant operation's own element list) keeps its own per-element words rather than being averaged into something the measurement does not say.

```
app.bst, lib-a.bst..lib-f.bst (7 elements, 6-9% of the critical path each, 2.0-3.0s apiece, 19.7s together):
  - already compute-bound at 1.4-1.8 cores busy - nothing to gain from their parallelism;
    shortening them means less work
  - `cc1plus` is 72-78% of each one's measured CPU - they are all the same problem, so look
    there before anywhere else
  (81% of each element's processes were measured)
```

- **A serialization point has to be material** (`UX-89`). `ar` and `ranlib` are single processes by construction, so before this rule had a bar every element that linked a static library earned a "SINGLE process holding 0.2s" line. The bar is `max(1.0s, 1% of the element's realizable saving)` — the same shape the redundancy rule already used — so a 12s `ld` still reports and a 0.2s `ranlib` does not.
- **Coverage is carried through.** A recommendation built on 81% of an element's processes says so (`UX-45`), and elements Plane 1 ranks that Plane 2 never traced are named rather than passed over.
- The two planes' timelines are **not** merged and cannot be — see [`docs/design/architecture.md`](../design/architecture.md). This is a join, and is deliberately named as one.

## Example Workflows


### CI Marginal Gate (`--fail-on-inefficient-additions`) — `UX-79`

The gate above reads dispatch occupancy, which is a **whole-build average**, so its sensitivity is inversely proportional to project size. Measured on fixtures at two scales, with the *same* two maximally-mis-added elements:

| project size | whole-build occupancy | that gate | marginal stretch |
|---|---|---|---|
| 11 elements | −14.6pp | **fails** | 1.00 |
| 1201 elements | −0.5pp | passes (blind) | **1.00** |

A gate that weakens as the project grows is weakest exactly where CI matters most, and a growing project approaches the blind spot with every element added.

```bash
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions --max-addition-stretch 0.3
```

**Stretch** is `added critical-path time / added work time`, over the elements this change *added* — so it mentions nothing about the rest of the repository and does not dilute:

- **0.0** — the additions were fully absorbed by existing parallelism; they cost wall-clock nothing.
- **1.0** — every second of added work extended the chain; the additions are perfectly serial.

`--max-addition-stretch` defaults to **0.5** — "at most half of what you added may land on the chain" — which sits in the wide, scale-invariant gap the measurement above found between a well-added set (0.00) and a serialized one (1.00). Exit code is `5`, the same "less efficient" family as the gate above.

Two deliberate limits:

- **A change that adds no elements is an empty check, and says so** rather than reporting green. The whole-build gate is what catches an *existing* element that got worse.
- **The per-element diff is published either way**, in `element_diff` (`new`/`removed`/`moved_onto_critical_path`) and `marginal_efficiency`, so a CI comment can render "New this change: … 8.0s added, 8.0s of it on the critical path" without running any gate at all.

### When the efficiency gates cannot run

Both efficiency gates read `occupancy_ratio`, which needs a
`resource_capacities.PROCESS` in `run-context.json`. Any legacy or
hand-built run directory may have none, and both gates then pass —
correctly, since a verdict must not be fabricated from missing data, but
for a long time silently. A pipeline that believed it was gating on
efficiency saw exit `0`, an empty stderr, and JSON indistinguishable
from a run that had really passed.

Fail-open is still the default. It is no longer silent (`UX-87`):

- stderr carries `Efficiency gate NOT APPLIED: … the baseline run has no
  \`occupancy_ratio\` signal …`, naming the gate and the run.
- `--format json` publishes `efficiency_gate_evaluated` — `true` (asked
  for and evaluated), `false` (asked for, could not run), or `null`
  (no efficiency gate was requested), plus `efficiency_gate_signal` with
  `missing_occupancy_in` and `gates_not_applied`.
- `--require-efficiency-signal` turns it into a failure, exit `7`, for
  pipelines that would rather break than not gate.

The two gates are reported separately because they need different
things: `--min-efficiency` is a statement about the candidate run alone,
so a baseline with no occupancy does not stop it; only
`--fail-on-efficiency-regression` needs both.

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
- `4`: **not "slower" alone.** `bga compare` returns it for any of three things, and a CI job that triages it as a duration regression will mis-read two of them:
  - `--fail-on-regression` and the build's total duration really did regress beyond the threshold (`docs/backlog/scenarios/UX-03`);
  - the **build-failure gate** (`UX-54`) - either run describes a build in which an element FAILED, so no scheduling verdict is meaningful. This fires whenever *any* gate was requested, including when only the efficiency gates were;
  - `--fail-on-low-confidence` and a run's confidence is below the "high" band.

  Read the stderr line, which names which of the three fired. All three are distinct from 1/2/3, which mean `bga` itself failed to run.
- `5`: `bga compare --fail-on-efficiency-regression`/`--min-efficiency`/`--fail-on-inefficient-additions` only - the build became meaningfully *less efficient*, whether or not it also got slower. Deliberately distinct from `4`: "slower" and "less efficient" are different verdicts and often different teams' problems (`docs/backlog/scenarios/UX-39`).
- `6`: `bga compare` refused - the two runs are not comparable (they share fewer than half their element UIDs, or one is a caches-off run and the other incremental). Not a verdict about the build at all, which is why it does not share a code with one (`docs/backlog/scenarios/UX-78`). `--allow-mismatch` overrides.
- `7`: `bga compare --require-efficiency-signal` only - an efficiency gate was requested but could not be evaluated, because a run has no `occupancy_ratio`. Like `6`, not a verdict about the build: `4` would say it got slower and `5` would say it got less efficient, and neither was determined (`docs/backlog/scenarios/UX-87`). Without `--require-efficiency-signal` the same situation exits `0`, prints an `Efficiency gate NOT APPLIED` line to stderr, and publishes `efficiency_gate_evaluated: false`.

## See Also

- [Project README](../../README.md)
- [Architecture Overview](../design/architecture.md) — both analysis planes, and every extension beyond the original spec
- [v9 Specification](../spec/specification.md)
