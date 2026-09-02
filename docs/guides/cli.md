# BuildStream Build Efficiency Analyzer (bga) - CLI Reference

The `bga` command-line interface provides access to the BuildStream Build Efficiency Analyzer, allowing you to analyze build traces, generate efficiency reports, and export data.

This is the reference. If you are pointing `bga` at a real project for the first time, read [`docs/guides/real-project.md`](real-project.md) instead — it walks the whole cycle end to end with real output at every step, and links back here for flags.

This covers the `bga` command itself — the whole-project analysis plane. For real per-process tracing *inside* one element's own sandbox (a separate tool, `tools/bst_native_build_tracer.py`, with its own Chrome Trace export), see [`docs/design/architecture.md`](../design/architecture.md#plane-2-intra-element-native-build-system-tracing-ux-11).

## One entry point (`UX-67`)

`bga` dispatches to the producer programs in `tools/` as well as running
its own analysis subcommands, so a session reads as one tool:

```bash
bga doctor  PROJECT                                 # can this machine capture at all?
bga wrap    PROJECT build.log -- bst build TARGET   # capture a log bga can read
bga extract PROJECT build.log run/                  # log + project -> run directory
bga analyze run/                                    # the analysis
bga capture run PROJECT native.json -- bst build T  # Plane 2, inside the sandboxes
bga correlate run/ native.json                      # join the two planes
bga blast https://…/monorepo.git                    # what rebuilds if I touch this
```

For the local loop specifically, those are the plumbing: `bga snapshot`
runs the capture, the extraction and the analysis together and compares
against the previous one. See
[`bga snapshot`](#bga-snapshot--the-local-loop-ux-126) below.

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
| `bga release-notes` | `tools.bga_release_notes` |
| `bga gen-synthetic` | `tools.gen_synthetic_scale_run` |
| `bga snapshot` | `tools.bga_snapshot` |
| `bga doctor` | `tools.bga_doctor` |
| `bga cache-logs` | `tools.bst_cache_logs` |
| `bga baseline` | `tools.bst_baseline_set` |

## `bga snapshot` — the local loop (`UX-126`)

```bash
cd /path/to/your/project
bga snapshot -- bst build target.bst   # capture + extract + analyze
# ...edit...
bga snapshot -- bst build target.bst   # ...and compare against the previous one
```

That is the whole local workflow. It replaces three commands and five
paths the user has to invent:

```bash
bga capture run --wrapped-log /tmp/plane1.log --trace-opens \
    /path/to/project /tmp/plane2.json -- bst build target.bst
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga analyze /tmp/run --plane2 /tmp/plane2.json
```

`snapshot` composes exactly those commands — it does not reimplement
them — so every number, every refusal and every hedge is the one the
explicit form produces. In particular a cross-mode pair (a caches-off
run against a caches-on one) is refused with exit 6, as it is when the
paths are typed out (`UX-78`).

Captures go to `.bga/runs/<UTC-stamp>/` under the project, holding
`run/`, `plane2.json`, the wrapped log and a `capture-context.txt` — the
same layout the published capture refs use, so nothing downstream learns
a second shape. `.bga/` gitignores itself.

### Naming runs: `@last`, `@prev`, `@<stamp-prefix>`

Every argument that names a run directory takes one of these instead —
and so does every argument that names a Plane 2 report, since a snapshot
holds both halves of the capture (`UX-134`):

```bash
bga analyze @last
bga compare @prev @last
bga cache-trend @prev @last
bga analyze @20260819                          # by stamp prefix, if unambiguous
bga analyze @last                              # the Plane 2 report beside it is found
bga analyze @last --no-plane2                  # ...unless you say not to
bga compare @prev @last --baseline-plane2 @prev --candidate-plane2 @last
bga cache-logs . --native-report @last
```

`bga analyze` finds the `plane2.json` beside a snapshot on its own
(`UX-329`), as `bga correlate` and `bga view` always have — before that
the same run published `plane2_coverage: null` in the terminal and the
full coverage in the page, which `bga view --help` promises can never
happen. `--plane2` still names a different report; `--no-plane2`
declines the sibling and the report says it declined.

**When Plane 2 is not in a report, the report says which absence it
is** — never captured, captured with its raw log not kept (so no
timeline), or declined. One sentence pair in `bga/plane2.py`, printed by
the terminal, published as `plane2_absence`, and shown by the page and
the export, so the three cannot describe one absence differently.

**One alias is one snapshot**, whichever of its files is being asked
for, so `bga correlate @prev @last` means a run from one and a report
from another *because you said so* rather than by accident.

And the join does not need to be told twice at all:

```bash
bga correlate @last          # the report beside that run is the one it came from
```

The Plane 2 report is optional whenever there is one sitting beside the
run directory, which is true of every snapshot and of anything
`bga capture run --run-dir` wrote. That is read off the filesystem, not
off whether an alias was used, so an explicit path to a snapshot's `run/`
behaves identically; the inferred path is printed. Where there is
nothing to infer the argument is still required, and says so.

The store is *resolution* and nothing else: an explicit path means what
it always meant, no run directory format changed, and comparability
rules are untouched. Outside a project an alias fails by name rather
than as a missing path, with exit 2:

```text
Error: @last is a snapshot alias, and there is no BuildStream project here to
resolve it against (no project.conf in this directory or any parent). Run it
from inside a project, or pass a path.
```

`@prev` with only one snapshot on disk gets its own message — *"@prev
needs two snapshots and PROJECT has one"* — because that is a different
problem from a typo'd path. So does an alias whose snapshot recorded
Plane 1 and not Plane 2: *"@prev resolves to 20260819T183424Z, which has
no plane2.json"*, which is a fact about that capture rather than about
your typing.

### Sticky flags

`--trace-opens` and `--trace-spine` are recorded in `.bga/config` and
reused until changed, so they are decided once per project rather than
retyped per capture:

```bash
bga snapshot --trace-spine=off -- bst build target.bst   # and stays off
```

A new project starts at `--trace-opens --trace-spine=auto`. Stickiness
is safe because every report records what actually ran (`UX-95`,
`UX-113`), so a remembered flag cannot make a capture *claim* something
it did not do.

### Other flags

| flag | what it does |
|---|---|
| `--list` | List this project's snapshots with their sizes, showing which are `@last`/`@prev` |
| `--no-compare` | Take the snapshot and report on it; skip the comparison |
| `--project PATH` | Snapshot a project other than the enclosing one |
| `prune --keep N` / `--older-than DAYS` / `--max-store SIZE` | Delete old snapshots; `--dry-run` says what would go |

`bga snapshot` exits with **the wrapped build's own exit code**. A
failed build is not a successful snapshot; equally, a comparison verdict
does not change the exit code — the CI gates live on `bga compare`
(`--fail-on-regression` and friends), which is what CI should call.

The one thing it will not do is start. If the build command's executable
is not runnable — no `bst` on `PATH` being the case that matters —
`bga snapshot` **refuses before it writes anything**, exits `2` like its
other refusals, and prints one sentence with the remedy and a pointer to
`bga doctor`, which is the command that checks the whole machine
(`UX-324`). No snapshot directory is created on that path, so there is
no debris to describe, resolve or prune afterwards. The check is
`bga doctor`'s own rather than a second copy of it.

Snapshots are build artifacts and `.bga/runs` entries can be deleted at
any time. Every capture now **says what it weighed and what the store
holds** (`UX-300`), and `bga` still warns once the store passes 2 GB.
What `prune` will never delete is `@last`, `@prev`, and — when both of
those record builds that did not finish — the newest *healthy* run,
because that is the baseline the next comparison walks back to
(`UX-167`).

```bash
bga snapshot prune --max-store 20G --dry-run   # oldest-first, under a budget
```

`--max-store` is the question a disk actually asks. Age and count are
proxies for it: a nightly capture that grew from 4 MB to 2 GB makes
`--keep 5` mean something different every month, and `--max-store 20G`
means the same thing forever. Combined with the others it is the
stricter of the two, never an override, and a store it cannot reach
without deleting `@last`/`@prev` says so rather than emptying itself.

`bga snapshot --aggregate` reports what the store weighs as a
distribution — the median capture against the p95 is what names the run
worth looking at — and its total counts *every* snapshot, including
captures excluded from the timing distributions for failing: a failed
run is not a sample, and still occupies its disk. See [the real-project
guide](real-project.md) for the store at big-project scale.

### Carrying a capture to another machine (`UX-520`)

**`run/` is not the capture.** It holds Plane 1 — `graph.json`,
`trace.json`, `run-context.json` — and the Plane 2 report, the raw
per-process trace, the host samples, the published analysis and the
build log all sit *beside* it. A `tar` of `run/`, which is the directory
every command's help names, arrives with Plane 2 missing; the far side
then says so rather than lying, but that is a poor substitute for
packing the right set:

```bash
bga bundle --export @last -o run.tar.gz
scp run.tar.gz laptop:
ssh laptop 'cd myproject && bga bundle --load run.tar.gz && bga analyze @last'
```

`--export` takes a stamp, `@last`/`@prev`, or a path, and writes one
archive holding every member `capture-layout/v1` names that exists for
that snapshot — derived from the contract, so a member added to the
layout travels without anyone remembering it. Members the contract calls
`derived` are skipped: that word means "absent means nothing; it is
rebuilt on demand", so leaving them out cannot make the far report
quieter.

```console
$ bga bundle --export @last -o run.tar.gz
Wrote run.tar.gz
  snapshot 20260902T101112Z: 7 member(s), 56.3K before compression
  load it with: bga bundle --load run.tar.gz
```

**`--load` unpacks under the bundle's own stamp**, not a new one. The
stamp is the capture's identity, so a run carried from a runner to a
laptop keeps the name it was compared under at home — and `UX-186`'s
host manifest rides inside `run-context.json` untouched, so `bga
compare` on the far machine caps confidence and refuses exactly as it
would have at the other end.

**It refuses rather than half-loads.** Every member carries its contract
version in the bundle's manifest, so a bundle packed by a newer `bga` is
recognised and declined with nothing written:

```console
$ bga bundle --load newer.tar.gz
Error: this bundle carries contract(s) this bga does not read: graph/v10.
It was packed by bga 9.9.9; upgrade to read it. Nothing was written.
```

It refuses the same way when the stamp is already in the store and its
contents differ — two different captures cannot share one identity.
Loading the *same* bundle twice is a re-send, not a collision, and
succeeds.

**Everything ships by default.** `--no-plane2` trades the large member
for a small bundle, says what it left out, and records the omission in
the manifest so `--load` says so too — because "why is Plane 2 missing
over there" is a worse question than a large file:

```console
$ bga bundle --export @last --no-plane2 -o small.tar.gz
Wrote small.tar.gz
  snapshot 20260902T101112Z: 6 member(s), 10.8K before compression
  left out (--no-plane2): plane2.json
```

For the CI direction — publishing to a git ref rather than one file —
see `bga baseline` and the capture-ref scheme below.

### The same job in CI

Use published capture refs (`bga baseline`, `UX-96`) rather than the
store. The store is the laptop's analogue of them, and a CI runner has
no persistent project directory to keep one in.

## Installation

```bash
pip install ./buildstream-graph-analysis   # or the git URL directly
```

That is **user mode**, and it is what the README teaches. `pip install
-e .` from inside a checkout is **contributor** mode — the two differ in
ways that have shipped bugs (`UX-77`, `UX-203`, `UX-325`: an editable
install has the repository root on `sys.path`, a wheel does not), so
this guide names which one it means rather than showing one and
describing the other (`UX-327`).

Add `bga[bst]` for a real BuildStream in the same environment,
`bga[completion]` for tab completion, `bga[all]` for both; `pip install
-e '.[dev]'` is the contributor set that `make test` needs.

## Basic Usage

### Analyze a Build Run

The primary command analyzes a directory containing `run-context.json`, `graph.json`, and `trace.json` (the run-context/v9, graph/v9, and trace/v9 schemas, Part 32) - **not** a raw BuildStream cache/artifacts path directly; nothing in a live BuildStream cache is already in this shape.

```bash
bga analyze RUN/
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
bga analyze RUN/ --format json > report.json
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
| `mesh-graph` | info | most elements have zero slack **and some are off the critical path** — several chains of equal length, so a saving on one is capped by the next (`UX-475`) |
| `graph-width` | info | how many dependency stages the graph has and how many elements its widest holds — the ceiling on concurrency the shape imposes, read from the dependencies alone and from no duration (`UX-478`) |
| `chain-graph` | info | most elements have zero slack and all of them are on the critical path — one chain, so a saving on any of them is worth its own duration (`UX-475`) |
| `blast-radius-reach` | medium | elements a change to which rebuilds something else, named with their downstream count. Published whatever the diagnosis says — a chain-bound build has a blast radius too (`UX-479`) |
| `blast-radius-ranking` | varies | elements worth fixing first by downstream reach (needs `--diagnostics`) |
| `blast-radius-structural` | info | elements whose reach is the graph's shape rather than a task — a base image, a toolchain, a stack. Reported, not ranked (`UX-258`) |
| `criticality` | varies | elements most likely to be on the critical path under duration variance (needs `--diagnostics`) |
| `optimization-horizon` | varies | what the build drops to after each of the next few fixes |
| `joint-saving` | varies | whether the recommended set's savings add up or overlap |
| `latent-heavies` | info | heavy elements off the critical path, worth nothing to fix today |
| `capacity-recommendation` | varies | the joint `--builders` × `--max-jobs` answer (`UX-116`): the sweep's scheduling knee, Plane 2's measured cores-busy, the `UX-104` memory ceiling and the host's cores, intersected, with the **binding** constraint named and the others shown beneath it. `high` when the run is configured above what its own measurements support, `medium` when there is room to grow, `info` when it is already at its ceiling. Needs `--plane2` |
| `memory-envelope` | varies | what this build's measured per-element peak RSS implies for `--builders` against the host's RAM — `high` when the current builders count does not fit, `medium` when one more would not, `info` otherwise. Needs `--plane2` and a capture that recorded the host's memory (`UX-104`) |
| `shared-source-blast` | medium | one repository's ref decides most of this build's rebuilds: any commit to it rebuilds N of M elements, because its direct elements key on its ref rather than on the files they stage (`UX-171`). Needs a run whose `sources.json` the extraction wrote |

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
| `merge-candidate` | medium | sibling elements spending at least half their time on sandbox toll rather than building — needs `--cache-logs` (`UX-100`) |
| `merge-not-indicated` | info | no element pays more sandbox tax than it builds, and how far the worst one is from the line |
| `split-candidate` | info | an element holding a material share of the critical path with real internal parallelism — evidence, never a projection (`UX-100`) |

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
bga analyze RUN/ --format json \
  | jq '.findings[] | select(.id == "time-concentration") | .evidence'

# Anything critical or high, as a gate condition
bga analyze RUN/ --format json \
  | jq -e '[.findings[] | select(.severity == "critical")] | length == 0'
```

#### Before anything else: `bga doctor` — `UX-125`

```bash
bga doctor                 # the environment
bga doctor PROJECT_DIR     # and whether this project can be captured
bga doctor --format json   # findings-style ids per check, for scripting
```

`bga doctor --capture` goes further (`UX-149`): it runs the whole capture
chain — `bst` → `buildbox-run` → the `$PATH` shim → the rewritten argv →
the recorders inside the sandbox — on a canned one-element build, and
reports per link in chain order. Seconds, and it needs a staged runtime
(`examples/stage_runtimes.sh`); it skips rather than building one. This
is the check to run when a capture fails on a build plain `bst`
completes — the first `FAIL` names the broken link, where `--diagnose`
would need the real failing build to say the same thing.

Read-only, one line per check, and a concrete remedy on every failure. It invents no check — each one fronts a failure that really happened while standing this project up, and the remedy quoted is the one that actually fixed it: a virtualenv for `pluginbase` under a distro-patched setuptools, `buildstream-plugins` for the `cmake` kind, the `apparmor_restrict_unprivileged_userns` sysctl for bwrap's loopback, `build-essential` for the hook and spine compile, `stage_runtimes.sh`/`stage_cpp_toolchain.sh` for a sandbox with no shell.

Two details worth knowing:

- **bwrap is probed, not just found.** Presence is not the check that matters — bwrap's namespace setup succeeds and then the sandbox fails to bring up loopback, deep inside a build. `doctor` runs the same trivial sandboxed command CI's `bst-smoke` job does.
- **"No element plugin registered for kind" gets two different remedies**, because it has two different causes: the package is missing, or the project has not declared it. Telling a user to install what they already have is how a diagnostic loses its reader.
- **A stale `buildbox-casd` is checked before the build, not guessed at afterwards** (`UX-161`). Any plain `bst` command leaves a daemon holding the cache directory, and a capture that starts under one fails in a way the summary could previously only speculate about. `doctor` reads `/proc` for a casd already holding this project's cache — the directory `bst` itself would use, `buildstream2.conf` before `buildstream.conf` (`UX-166`) — and prints the remedy.

Exit `1` only on a failure. A static-binary blind spot (`--trace-spine=auto` is the answer) and an empty Plane 3 log tree are **warnings**: facts to read, not broken environments. `bst-tests` runs it as a step, so its checks cannot drift from what CI actually installs.

#### Conditioning capacity advice on Plane 2 (`--plane2`) — `UX-83`

```bash
bga analyze RUN/ --plane2 PLANE2.json
bga sweep   RUN/ --resource PROCESS --plane2 PLANE2.json
```

The `RESOURCE WAIT` hint and `sweep`'s knee point are both replay-model answers, and the replay model does not know about CPU (`UX-09`/`UX-14`). Measured once on a real dual-plane capture: `analyze` said *"31.9% of wall-clock is RESOURCE WAIT — try `--capacity N` with a higher N"* and `sweep` put the knee at capacity 5, on a 4-core host — while `correlate` on the **same capture** named the real fix, an element pinned to `-j1`, worth −32.4% and costing no extra capacity.

With `--plane2`, both consult what was actually measured inside the sandboxes:

- a host Plane 2 measured as already CPU-saturated is told **not** to raise capacity, with the measurement quoted;
- an element pinned to `-j1` is named **first**, because intra-element parallelism is capacity you already have and, unlike `--builders`, it cannot contend with itself.

- the four constraints on the joint (`--builders` × `--max-jobs`) choice are **intersected** into one
  recommendation naming the binding one (`UX-116`), instead of four blocks a reader has to reconcile:

```text
Capacity: builders 4 x max-jobs unrecorded on 4 core(s): graph binds at 6 - there is room for 2 more builder(s)
  graph allows 6: the sweep's knee is at 6 builder(s)
  CPU allows 7: 2.11 of 4 core(s) busy at builders=4, i.e. 0.53 core(s) per concurrent element
  memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peak(s), so it says nothing above 9)
  Free capacity you already have: core.bst asked its native build for -j1 - a builder slot drawing one core.
```

  The CPU ceiling is derived, not assumed: `cores_busy / builders` is what one concurrently-building element
  actually drew, and the ceiling is how many of those the host's cores can feed. A constraint nothing measured
  is omitted rather than treated as unbounded, and the whole block declines to appear at all when Plane 2 has
  no `cores_busy` — the same bar `UX-83` uses.

Without `--plane2` every line is byte-identical to before — including `UX-09`/`UX-15`'s standing "native
build-system parallelism is a separate, currently unmodeled axis" note, which is retired **only** in captures
where the block above actually ran.

#### Resource Capacity

Override the detected system capacity (useful for simulating different hardware):

```bash
bga analyze RUN/ --capacity 16
```

*Note: This affects the calculation of the Lower Bound ($LB$) and Replay Makespan ($T_C$).*

#### Replay Simulation

Run the deterministic replay scheduler to compute a feasible makespan ($T_C$) under the chosen scheduling heuristic - a counterfactual model for scheduler comparison, capacity sweeps, and model slack (Part 18), not a claim that $T_C$ is the mathematically optimal schedule:

```bash
bga analyze RUN/ --replay
```

You can specify the scheduling heuristic:

- `lpt` (Longest Processing Time first) - Default; a common, reasonable heuristic, not guaranteed optimal.
- `spt` (Shortest Processing Time first).
- `fifo` (First In First Out).
- `depth` (Dependency depth priority).

```bash
bga analyze RUN/ --replay --heuristic lpt
```

#### Diagnostics

Enable advanced diagnostic signals (adds computation time):

```bash
bga analyze RUN/ --diagnostics        # -d is the short form
```

This computes:

- **Blast Radius**: Number of downstream dependents for each element.
- **Criticality Probability**: Likelihood an element appears on the critical path under duration variance.
- **Wall-Clock Shares**: Attribution of wall-clock time to specific elements.

#### Output File

Save the report to a file instead of stdout:

```bash
bga analyze RUN/ --output report.txt
```

#### Cold Structural Floor (advisory)

Compute the advisory **cold floor** (`T∞,cold`) using prior runs' observed durations as an estimate source. *Two unrelated "cold"s meet here* (`UX-138`): this structural floor, and the **cold capture mode** (caches off) that `run-mode-incremental` above is about. This flag is the floor; nothing here changes how a build was captured. Off by default - never affects `LB`, `certified_headroom`, primary `confidence`, or measured attribution:

```bash
bga analyze RUN/ --cold --history-dir PRIOR-RUN-1/ --history-dir PRIOR-RUN-2/
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
bga analyze RUN/ --verbose
```

## Section Subcommands

`analyze` is the primary command and produces the full report (every section together). `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` are thin aliases over the same analysis pipeline - each restricts output to just its own section, so you don't have to grep a full report or a `jq` filter out of `--format json` for a narrow question. They accept the same relevant `analyze` flags (`--format`/`--output`/`--capacity`/`--verbose`/`--quiet`/`--log-file`, plus each subcommand's own natural options) and the same exit-code contract.

```bash
bga graph RUN/          # static dependency graph, critical path, structural metrics
bga floors RUN/ --cold  # certified/advisory floors (T-infinity, LB, certified headroom, cold floor)
bga replay RUN/ --heuristic spt   # deterministic replay makespan (T_C)
bga sweep RUN/ --resource PROCESS --min-capacity 1 --max-capacity 16  # capacity sweep (Part 19)
bga utilisation RUN/    # CPU utilisation accounting
bga diagnostics RUN/    # blast radius, criticality probability, wall-clock shares
```

`floors` accepts the same `--cold`/`--allow-partial-cold`/`--history-dir` flags as `analyze` (matching the spec's own `bga floors RUN --cold` example). `replay` accepts `--heuristic`; `sweep` has its own `--resource`/`--min-capacity`/`--max-capacity`/`--step` flags and isn't a slice of `analyze`'s output at all - it runs a series of replay simulations across a capacity range and reports predicted `T_C`, normalized improvement, and the diminishing-returns "knee" point per capacity value. Every replay/task duration in that sweep is fixed to what was actually observed - the model does not account for real CPU contention as concurrent `PROCESS` usage rises (`docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md`'s own real evidence: raising `--builders` can make a real build *slower*, not just plateau, once cores are oversubscribed), so `bga sweep`'s own text/JSON output always carries an explicit caveat to this effect (`docs/backlog/scenarios/UX-0014-sweep-replay-blind-to-contention-slowdown.md`) - treat the predicted curve as a shape, not an exact runtime prediction (Part 19). `graph` has its own `--by-kind` flag (P4-12, non-spec additive signal): `bga graph RUN/ --by-kind` also shows aggregate stats (count, total/avg observed duration) grouped by each element's real BuildStream plugin kind (`import`/`manual`/`junction`/`stack`/...) - off by default, since it's extra detail beyond the base graph section.

## Tab completion (`UX-191`)

```bash
pip install "bga[completion]"
eval "$(register-python-argcomplete bga)"          # bash/zsh, in your rc
register-python-argcomplete --shell fish bga | source
```

What it completes:

| where | what |
|---|---|
| `bga <TAB>` | every subcommand **and** every `UX-67` alias |
| any run argument — `bga compare @<TAB>` | `@last`, `@prev`, and this project's own snapshot stamps |
| `bga blast <TAB>` | element names, read from the project's `.bst` files |
| any `--flag` with choices | its choices |

Without the shell hook it is completely inert, and without `argcomplete`
installed the import is skipped — the CLI behaves exactly as it did.

**Why not `click`.** The feedback suggested migrating; `argcomplete`
completes an argparse program as it stands, while a rewrite would touch
every subcommand, re-litigate the help formatting `UX-158` measured, and
buy nothing beyond what completion already gives. Recorded as considered
and declined, revisitable if argcomplete cannot complete something users
need.

## `bga timeline` — one trace, both planes (`UX-188`, `UX-298`)

```bash
bga timeline @last              # -> <snapshot>/timeline.perfetto-trace.gz
bga timeline @last --format chrome          # -> <snapshot>/timeline.json
bga timeline @last -o /tmp/t.gz --anchor-element components/openssl.bst
bga timeline @last --planes 1               # no process lanes
bga timeline @last --only-element core.bst  # one element's process lanes
```

Plane 1's element schedule always; Plane 2's process lanes underneath it
when the snapshot kept its raw trace log — which `bga snapshot` does by
default (gzipped, **8% of its size**, measured on two real captures).
`--no-keep-raw` opts out.

**The default is Perfetto's own format** (`UX-298`): protobuf
TrackEvent, gzipped, written packet by packet as the records are paired
rather than assembled in memory. That is what [Perfetto](https://ui.perfetto.dev)
and `trace_processor` read natively, and it is a stream — a capture too
big to hold is no longer a capture too big to render. Measured on a
40,000-process trace: 4.83 MB of packets, 1.14 MB gzipped, and bytes on
disk 10,000 slices before the writer closes.

`--format chrome` writes the legacy JSON instead, for `chrome://tracing`
and for a pipeline that already parses it. Both read the same two logs
and align on the same anchor, so the choice is about what will open the
file, not about what is in it.

**When the trace is too big to open** (`UX-430`): Perfetto draws a row
per track, and the process lanes are where that count grows — one per
element plus one per traced pid. Measured on the seeded scale run
(`bga gen-synthetic --seed 1`, 1,202 elements, twelve processes each):

```text
                  tracks   slices     bytes
  both planes     16,832   15,628   486,167
  --planes 1       1,205    1,204    72,080
  --only-element   1,219    1,216    73,017
```

`--planes 1` leaves the process lanes out; `--only-element` keeps one
element's, and narrows its exec arrows and the concurrency counter with
them, so the lanes and the counter agree about what is being shown. The
byte size never noticed: 486 KB is an eighth of the 4 MiB the handoff
bounds transfer at.

The two planes are aligned on one element that appears in both; without
`--anchor-element` that is the longest-running element **both planes
know** — Plane 2's longest alone can name one Plane 1 never built, and
the merge then refuses a question that should not have been asked.

Without a raw log it renders Plane 1 and **says what is missing** rather
than silently producing half a timeline.

This composes `bga log-to-chrome` and `bga native-to-chrome combined`,
which still work on their own. Feeding either a file with no parseable
trace lines is now a **refusal**, not `Wrote 0 trace events` and exit 0 —
the usual cause is a `plane2.json` report where a raw log belongs. Every
converter's status line goes to stderr; the payload is the file.

## A capture that meets a laptop lid (`UX-185`)

The hook and the spine stamp `CLOCK_MONOTONIC`, which **does not advance
while the machine is suspended**; the Plane 1 wrapper stamps wall clock.
So a suspend mid-capture leaves Plane 2 under-reporting the elements it
crossed and Plane 1 over-reporting them, and nothing about the run looks
wrong.

**Detection is not optional.** Every capture records both clocks at both
ends; wall time running ahead of monotonic time is how long the machine
slept. Past five seconds the run declares itself incomplete, and
`UX-156`'s grammar does the rest — `bga analyze` banners it and `bga
compare` refuses the verdict, with exit 6 under a gate:

```text
This capture spans a suspend: the machine slept for about 45 minutes
while it ran. ... Re-run with `--inhibit`, or on mains power with the
lid open.
```

**Prevention is.** `--inhibit` wraps the build in `systemd-inhibit
--what=sleep:shutdown` (and `gnome-session-inhibit --inhibit idle` when
present), which is not the default because taking a lock on your power
management uninvited is not `bga`'s call:

```bash
bga snapshot --inhibit -- bst build all.bst
```

With neither inhibitor installed it says so in one line and runs anyway.
`bga doctor` warns when the machine has a sleep policy that could fire.

The spans are **not** corrected — which processes were mid-flight at the
suspend is recorded nowhere, so there is nothing to correct them with.
Refusal is the honest output.

## Long reports (`UX-187`)

On a build whose critical path is hundreds of elements, the path alone
used to be **405 of the report's 498 lines** — 81% of it, with every
section a reader acts on below the fold. The list-shaped sections now
render their two ends and fold the middle:

```text
    layer10/mod003.bst                          7.90s (  0.3% of path)
    ... 382 more element(s) (--full-path to print all)
    layer393/mod005.bst                         4.60s (  0.2% of path)
```

A chain's two ends are where an optimizer starts — the root everything
waits on, and the last link before the build finishes — so the middle
is what goes.

| flag | restores |
|---|---|
| `--full-path` | every element of the critical path |
| `--full-sources` | every row of the Shared Sources table |

**Nothing is cut silently**: every elision names its own count and the
flag that undoes it. **JSON never truncates** — the caps are a
text-rendering concern, `--format json` carries the whole thing, and
the `--full-*` flags do not change one byte of it.

## The JSON outputs, and their schemas (`UX-190`)

Every machine-readable output declares its own shape as its **first
key**:

```bash
bga analyze RUN/ --format json | head -2      # "schema": "analyze/v5"
bga compare A B --format json                 # "schema": "compare/v2"
bga blast TARGET --format json                # "schema": "blast/v2"
bga correlate RUN/ --format json              # "schema": "correlate/v2"
bga whatif RUN/ --element E --format json     # "schema": "whatif/v1"
```

`--schema` prints the JSON Schema of an output and exits 0. It needs no
run directory — it answers about a shape, not about a run:

```bash
bga analyze --schema
bga compare --schema | jq '.required'
```

**The versioning rule**: a field rename or removal bumps the version; an
addition does not. Pin `analyze/v5` and your consumer keeps working
while the tool grows.

A section subcommand (`bga floors`, `bga graph`, …) emits the same
`analyze/v5` document restricted to its own keys, with a `section` key
naming the restriction — so a missing key can be told from a removed
one.

### What a build here costs (`UX-234`)

A store of captures is a measured distribution, and `--aggregate`
reads it as one:

```bash
bga snapshot --aggregate                 # text
bga snapshot --aggregate --format json   # a `store-aggregate/v1` document
```

```text
Store: /home/you/project
  5 measured run(s) of 6 snapshot(s)
  1 excluded:
    1 x interrupted

  Ryzen 9 7950X · 32 cores · 64000 MB - 5 run(s)
    Duration: min 10.0s, median 12.0s, p95 30.0s, max 30.0s (MAD 2.0s, n=5)
```

Three rules decide what it will and will not say:

- **An unfinished capture is not a sample.** A failed, interrupted or
  suspended run is excluded from every distribution and *counted* where
  it was excluded — "we had nine runs" and "we had nine and threw two
  away" are different claims.
- **A mix of machines is not a distribution.** Runs are grouped by the
  host class `UX-186`'s compared fields distinguish (CPU model, core
  count, memory), and a blended figure across classes is refused: exit
  6, the same code a cross-host `bga compare` refuses with. `--blend`
  prints it anyway, which is you taking the claim rather than the tool
  making it. A capture with no host manifest is its own class.
- **Fewer than three finished runs define no distribution.** The class
  publishes a shortfall naming what is missing instead of a p95 of two
  samples.
- **A mix of contract sets is named, not refused** (`UX-253`).
  `contract_composition` lists each set of contracts the aggregated
  runs were written under, commonest first, with runs carrying no
  producer stamp counted separately as an explicit unknown. Unlike a
  host class, two contract sets are not two populations: what decides
  whether runs can be pooled is movement in the contracts this document
  *reads* (`analyze/v5`, `store/v1`), never the package version — the
  rule `bga compare` already applies to a pair.

Percentiles are **nearest-rank**: for `n` sorted samples, `p` is the
value at index `ceil(p × n) − 1`. No interpolation, so every figure is
a duration some build actually took.

`bga view`'s store trend draws the median–p95 band behind its points
from this document, and nothing at all when the store mixes host
classes — it prints the refusal instead.

### Choosing the fixes (`UX-230`)

`bga whatif` projects the build for a set of fixes you choose:

```bash
bga whatif RUN/ --element core.bst --element lib.bst
```

```text
What if these were fixed: core.bst, lib.bst
  Makespan 0.014s -> 0.004s (saves 0.010s)
  Their individual savings add up to 0.011s, which is not what they are
  worth together (0.010s) - what one fix is worth depends on the others.
```

That last line is the whole point. **Savings do not add.** One
longest-path recompute with every chosen element zeroed is the answer;
summing what each is worth alone is wrong the moment two share a chain,
and on the golden fixture the two figures already differ.

"Fixed" means the element becomes instant, over this run's measured
durations, with nothing else assumed to change — an upper bound, not a
forecast. The convention travels in every answer. A selection with an
element the run does not know, one with no measured duration, or an
empty one is **refused by name** rather than projected, and a refusal
still exits 0: it is the answer, not a failure.

The page has the same thing with checkboxes. A prefix of the published
plan is read straight from `optimization_horizon`; any other
subset is asked of the server, which runs this same projection. In an
export there is no server, so the section shows the command instead of
a control that cannot answer.

**The payload: `whatif/v1`** (`UX-295`). `--format json` stamps this
shape as its first key, and a consumer holding one reads:

| key | what it is |
|---|---|
| `run_id` | the run this projection is over |
| `selected` | the element uids you asked about, as given |
| `total_duration_us` | the run's own wall-clock, for scale |
| `convention` | the sentence every figure here depends on, carried in the payload rather than left to the reader (`UX-244`) |
| `refusals` | why no projection was made, when one was not — a list of `{check, elements, sentence}` |
| `projected` | the projection, or `null` when `refusals` is non-empty |

and inside `projected`:

| key | what it is |
|---|---|
| `baseline_makespan_us` | this run's longest path, unchanged |
| `makespan_after_us` | that path recomputed with every selected element zeroed |
| `joint_saving_us` | the difference — what the set is worth **together**, and the answer |
| `sum_of_individual_us` | what each element is worth alone, summed; published *because* it can differ, never as the answer |

Measured on the golden fixture for `base.bst`: baseline 14,000 µs,
after 8,000 µs, joint saving 6,000 µs, sum of individuals 6,000 µs —
equal here because one element cannot disagree with itself; the two
figures separate as soon as two selected elements share a chain.

A refusal is a populated answer rather than an error, and the command
still exits 0 — which is why a consumer reads `refusals` before
`projected` rather than after, and why `projected` being `null` is a
statement rather than a missing field.

`bga whatif --schema` prints the whole shape without needing a run.

### Why this one is ranked first (`UX-227`)

Each top action in the decision panel carries a **Why #n** fold: the
rule that ranked it (read from that finding's `provenance` record), what
this run measured about the element, the findings that name it, and how
it has moved across the store.

Every value in the fold carries the path it was read from in
`data-field` — for example
`critical_path_detail[element_uid=core.bst].share_of_path` — in
the same grammar `provenance.evidence[].path` uses. Nothing in the fold
is derived; it is the document, gathered under one question.

### The chain behind every claim (`UX-229`)

Every claim the report makes — the diagnosis, each finding, each top
action — carries a **provenance record**: the published fields it was
read from, the rule that fired, and the trace query that deepens it.

```text
claim -> evidence (field refs) -> rule -> trace query
```

`--explain` prints the chain under each claim in the terminal:

```bash
bga analyze RUN/ --explain
```

```text
  This build is scheduler-bound, not chain-bound: the critical path is
  88% of wall-clock, so the time is going somewhere other than the chain.
    why: The critical path is 87.5% of wall-clock, which is < the 90% at
         which the chain rather than the scheduler is called the
         constraint - so scheduler_bound.
    rule: CHAIN_BOUND_RATIO = 0.9 (<, bga/findings.py)
      floors.t_infinity_observed = 14000
      total_duration_us = 16000
      headline.chain_share = 0.875
    deeper: trace query `element-time`
```

The same object is in the JSON at `headline.provenance` and
`findings[].provenance`, and the page renders it folded under each
claim:

- `evidence[]` — each entry is a `path` **into this same document** plus
  the `value` found there, so a reader follows the reference rather than
  trusting the quote. Paths are dotted keys, `[i]` for a list index and
  `[key=value]` for the one list entry matching it.
- `rule` — the constant that decided the claim, read live: change
  `CHAIN_BOUND_RATIO` and `rule.threshold` changes with it. `name` is
  `null` where a claim has no threshold, which is a different statement
  from a threshold of zero.
- `trace_query` — the `bga timeline` question that deepens it, or
  `null`. This mapping used to live only in the viewer.
- `unpublished_inputs` — fields a claim was genuinely drawn from that
  this document does not carry. Named rather than omitted: silence
  would read as no gap.
- `document` — which schema the paths walk. Load-bearing when a record
  travels: `bga compare --format json` carries the candidate run's
  chain at `candidate_diagnosis`, and its paths resolve against that
  run's `analyze/v5`, not against the comparison.

A top action's provenance is a **pointer** (`see`) at the finding's
record, because the action is already a reference to that finding.

`bga compare --format ci-comment` cites the same record in a folded
*Why the candidate looks like this* block, so a reviewer asking "why do
you say that" gets the answer in the comment rather than in another
command's output.

### The two-plane join, published (`UX-215`)

`bga correlate --format json` has emitted the join since `UX-51`. It
was unversioned until round 25 — no `schema` stamp, no view-hints,
served by nothing — so the one place where *"this element is on the
path, is worth 12.05s, and was pinned to one job on four cores"* is a
single row was invisible to `bga view`, to CI and to every external
consumer. It is `correlate/v2` now, with no change to what it computes.

```bash
bga correlate @last --schema | jq '.properties.elements["bga:columns"]'
bga correlate @last --format json | jq '.elements[] | select(.on_critical_path)'
```

One row per element, from both planes:

| | |
| --- | --- |
| Plane 1 | `on_critical_path`, `critical_path_share`, `potential_saving_us`, `saving_share`, `blast_radius` |
| Plane 2 | `cores_busy`, `cpu_coverage`, `requested_jobs`, `peak_rss_kb`, `dominant_binary`, `serial_binary` |

`bga analyze --plane2 PLANE2.json` now carries the same rows as
`element_join`, from the same function — so the report and the command
cannot describe an element differently. Without `--plane2` the key is
**absent**, not empty: with one plane there is no join, and its Plane 1
half is already in `signals`.

Two refusals the document keeps rather than smoothing over:

- An element Plane 2 never saw is a row with its Plane 1 half and no
  Plane 2 numbers — not zeros, which would read as *"measured, and
  idle"*.
- An element Plane 2 named that Plane 1 never declared (`declared:
  false`) is listed, because hiding it would hide a real disagreement
  between the planes, and it never carries a recommendation (`UX-66`).

## Progress on a long run (`UX-183`)

The phases that take minutes — parsing a 200k-process trace, pairing it,
the census walk, `bst show`, measuring the store — draw a single
self-overwriting line on **stderr**:

```text
  parsing trace: 120000/480000
```

**Only when stderr is a terminal.** Redirect it to a log file or a pipe
and the output is exactly what it was before: `UX-159`'s whole phase
lines, and nothing else. No carriage returns, no partial lines.

**stdout is never touched.** `bga analyze --format json | jq .` produces
the same bytes whether or not anything is being drawn, and there is a
guard asserting exactly that.

Turn it off on a terminal with `BGA_NO_PROGRESS=1`, or
`bga snapshot --no-progress`.

## `bga view` — the report in a browser (`UX-193`)

```bash
bga view                 # @last, opens a tab
bga view @prev --no-browser      # prints the url instead
```

A local page over one run's published JSON. `127.0.0.1`, a port the
kernel picks, and a fixed allowlist of documents — nothing else in the
run is reachable, there is no directory listing, and no write method is
answered.

**It moves between runs** (`UX-394`). Three of those documents take a
parameter:

| | |
| --- | --- |
| `blast.json?target=…` | what one element rebuilds |
| `whatif.json?elements=…` | what fixing a set would be worth |
| `?run=<stamp>` | **which snapshot the whole page is of** |

`bga view` is started on one run, but it serves any snapshot in that
project's store: `?run=20260101T000000Z` builds that run's documents on
demand and the page renders them. The rail draws a picker when the
store holds **two or more** — below that there is no choice to offer,
so there is no control. `?run=` naming a stamp the store does not have
falls back to the run the server was started on, rendered whole rather
than an error page.

The stamp is in the URL, so a link to a run is a link somebody else can
open, and the browser's back button moves between runs.

An **export has no store** — it is one file over one run — so it
renders no picker at all.

**It renders the schema, not the report.** The page asks
`schemas.json` what each key *is* — a duration, a share, a findings
array, a table with these columns — and renders from that. Two things
follow, and both are deliberate:

- A field added to `analyze/v5` appears in the viewer with **no change
  to the viewer**.
- Anything the viewer should show has to enter the published schema
  first, where `--format json`, CI and every external consumer get it
  too.

The page is a handful of files checked into the repository under
`bga/viewer/` — HTML, one stylesheet and a few ES modules — with no
bundler, no npm and no build step. A richer TypeScript app is a welcome *consumer* of these
payloads rather than a replacement: the view-hints below exist so one
can be written without this project blessing a frontend stack.

### Three views that draw (`UX-196`)

The page carries three things a table could not say:

- **The band.** Compare's noise band as a strip, the baseline runs as
  dots, the candidate as a marker. `UX-170`'s **disputed region** — a
  candidate outside the band but inside the range the baselines
  themselves spanned — took a paragraph in prose and read like a
  paradox; drawn, the marker simply sits between the strip's edge and
  the dots' extent.
- **The store trend.** `--list` made visual. Snapshots that are not
  measurements (failed, interrupted, suspended) are drawn as squares
  rather than dropped — they are on the disk, so they are on the chart.
- **The blast explorer.** A box taking a url, a path or an element
  name, answered by `blast.json?target=…`, which calls the same
  function `bga blast` calls. The served answer is byte-identical to
  `bga blast --format json` (`--no-cost`, because a page should not
  block on the full pipeline).

Exactly two custom SVGs, no library behind either, and nothing
recomputed in the browser — the payloads already carry the band edges,
the observed extent and the verdict.

```bash
bga snapshot --list --format json     # store/v1, what the trend draws
```

The text listing and this JSON render from the same rows, so the
drawing and the terminal cannot disagree about what is on disk.

### What the page leads with (`UX-202`)

Above the sections, two things a list of tables could not say:

- **The evidence header** — confidence and its band, Plane 2's
  coverage, the host line, and the run's incompleteness. `UX-156`'s
  tone: what this capture can and cannot support, stated *before* any
  number is believed. A failed, interrupted or suspended run says so
  here rather than in a banner floating above an otherwise ordinary
  report.
- **The overview waterfall** — the real duration, down through the
  attribution gaps to the certified floors, each segment labelled with
  its published number and linked to the section that explains it.

**Every number in both is read from a published field.** Nothing is
computed in the browser; the one division in the waterfall is a CSS
width. A gap the JSON does not carry enters `analyze/v5` first, where
`--format json`, CI and every other consumer get it too — which is why
`confidence.band`, `run_instance.incomplete_reason` and
`plane2_coverage` are fields rather than viewer logic.

### Finding your way around it (`UX-199`)

Every section carries an `id`, a generated table of contents sits at the
top, sections collapse (and remember it), and a jump box finds an
element by name. An exported report keeps all of it, plus the questions
page inlined and the blast search box hidden — it asks a server, and an
export does not have one.

### What the page opens with (`UX-207`)

The first screen is a **decision**, and everything below it is the
evidence for that decision. `analyze/v5` publishes a `headline` block —
the diagnosis (`chain_bound`, `scheduler_bound` or `inconclusive`), the
ratio it was decided by, what the opportunity is worth, and the three
elements to look at first, each pointing at the finding that reasons
about it. The panel renders that block; it derives nothing, so the
terminal, CI and the page cannot disagree about what should be fixed
first.

### Sections named as questions, and a rail (`UX-209`)

Sections are titled by the question they answer — *"Where did the
wall-clock go?"*, *"How much faster could this build possibly be?"* —
with the schema key kept as a muted subtitle so an anchor pasted into
an issue still reads. The question is a schema declaration
(`bga:question`), not a viewer table, so it reaches the text renderer
too.

The contents groups those sections into a rail rather than listing them
in payload order:

```text
decide       what this run concluded, and what to fix first
act          where the wall-clock went, which elements bind
prove        the floors, the capacity verdict, what did not add up
investigate  the graph's shape, one resource's blast radius
raw          the capture's own identity
```

A section whose schema declares no rail lands in `raw` — never nowhere.

### One click from investigation (`UX-208`)

- A column can declare that it holds element uids (`role: "element"`),
  and every row of such a table earns the same **Inspect** — jump to
  that element elsewhere in the report, and open it in Perfetto where
  there is a timeline. One loop in the renderer, no per-table code.
- Critical-path boxes carry a popover with the element, its kind, its
  duration and its share, read from the published entry.
- Every SQL block has a **Copy** button.
- Tables get a `Top 10 ▾` preset over any declared quantity column; the
  badge still says `10 of 1,202`, because a reader who cannot see the
  denominator cannot tell a filtered table from a small one.
- The blast box opens with the payload's top-ranked targets as chips.

### What to run next (`UX-218`)

The report ends with the next commands, chosen by what this run
measured, with the run path and the element already filled in:

```text
Next:
  core.bst is the first thing to fix, worth 12.1s - this is what changing it rebuilds.
    bga blast core.bst examples/06-…/.bga/runs/20260821T170127Z/run
  Plane 2 measured this run, so the join can say whether core.bst is compute-bound…
    bga correlate examples/06-…/.bga/runs/20260821T170127Z/run
  Make the change, then capture it the same way.
    bga snapshot --project examples/06-macro-micro-optimization -- bst build all.bst
  Whether it helped, judged against this store's noise - run it in examples/06-macro-micro-optimization.
    bga compare @prev @last
```

Every line under a reason is a command as `bga` would receive it, and
`UX-326` is why that is worth saying: for six rounds the last two were
not. `bga snapshot <project>` put the project where the *build command*
goes and crashed; `bga compare … --project` named a flag `bga compare`
does not have. Both are now parsed by the parser that would receive
them, in
[`tests/unit/test_the_printed_sentences_are_contracts.py`](../../tests/unit/test_the_printed_sentences_are_contracts.py).

Same list in `--format json` as `next_steps`, and in the page's
decision panel with a Copy button beside each — one function, so the
terminal, CI and the page cannot advise differently.

**Which** step is right depends on the run, so it is decided in the
pipeline rather than by whatever is reading the report. A chain-bound
build is not told to add builders. A run outside a store is not told to
compare against a previous one it does not have. A run with no Plane 2
report is not told to look inside its elements. Each step names the
published field it follows from, so the advice can be checked against
the number behind it.

### Findings show their evidence (`UX-217`)

Each finding renders the numbers it was drawn from, in the units the
schema declares them in:

```text
⚠ 12.5% of wall-clock is untracked tail
   category      untracked_tail_us
   category_us   2 ms
   share         12.5%
```

Those are published fields, in published units — `share: 0.125` is a
share and renders as a percentage; `category_us: 2000` is microseconds
and renders as a duration. A finding whose evidence key the schema does
not describe renders it raw rather than guessing at a unit.

### Everything about one element, in one place (`UX-216`)

Every element the report discusses gets its own section: what it holds
of the critical path, what a fix is worth, what it rebuilds, and —
where Plane 2 saw it — how busy the cores were, how many jobs it asked
for and what it peaked at. The findings that name it are there, and so
is what joins the critical path if you fix it.

Every mention of an element links to it: a table row's **Inspect**, a
critical-path box, a finding's element list, a top action, a blast-tree
row. A section says where else in the report the element appears, read
from what the page actually drew.

`bga view` before this shipped 19 Inspect affordances on `examples/06`
that resolved to nothing — the anchor scheme and the ids never matched.
The guard now resolves every one of them.

### A link that shows what you were looking at (`UX-211`)

**Copy link to this view**, beside the contents. The filter, the
thresholds, the sort, the Top-N, the collapsed sections and the folds
travel in the URL fragment, so what lands in the issue is the view you
built rather than the unfiltered wall. `#floors` still means exactly
what it meant; the state follows a `~`. The hash wins where it speaks
and your own remembered state stands where it is silent — and it works
from an exported `file://` report, where browser storage may not exist
at all.

### Verdicts without the palette (`UX-212`)

The trend's dots differ by **shape** as well as colour — one per
verdict kind, from a map the schema declares — and the band's noise
strip and observed extent differ by outline. Both survive a grayscale
print and a colour-blind reader.

### Interrogating the tables (`UX-205`)

Each table gets a filter box with a row-count badge (`12 of 1,202`) and,
on every quantity column, a threshold typed in that column's own unit:

```text
> 5s        on a duration column
>= 512mb    on a size column
< 10%       on a share column
```

The unit parses because the schema *declares* what the column is — and
the comparison runs against the published value, never the formatted
text. A cell copies on double-click as its raw value; **Copy shown
rows** puts the filtered rows on the clipboard as JSON that parses.

Measured at 4,000 rows: 146 ms to render, 20 ms to filter. There is no
windowed rendering, deliberately — machinery without a measured need is
how a thin viewer stops being one.

### Two drawings, and no DAG viewer (`UX-206`)

- **The chain, drawn** — the critical path as a sequence of boxes whose
  widths are the published `share_of_path`. Long chains fold in the
  middle (`UX-187`'s fold) and open in place.
- **The blast tree** — a blast answer as an indented hierarchy, direct
  consumers first, then the closure by depth, each row with its kind
  and measured work. The depth is published in `blast/v2` as
  `blast_tree`; the page does not walk a graph.

A general BuildStream DAG rendering stays deliberately unbuilt — it
answers no question anyone asks. The argument is in
[Direction 7](../design/directions.md).

### The report as one file (`UX-195`)

```bash
bga view @last --export report.html
```

The same page, as an attachment: the run's JSON inlined, the CSS and
both modules inlined, the timeline carried as a `data:` URL. No port, no
server, no network — it opens from a downloads folder, a CI artifact
viewer, or an email.

**What it weighs, in three parts.** A report is not "page plus data":
it also carries the JSON Schema for every document in it, so a reader
can ask what a number means with no network. That third part travels
whole whether or not a run has the rows it describes, which is why it
is counted separately (`UX-342`).

Measured in round 65 on a cold two-plane capture of `examples/06`
(38 s, `bga snapshot -- bst build all.bst` against an isolated
`XDG_CACHE_HOME`, then `bga view <run> --export report.html`):

```text
total       520,048 B   508 KiB
  source    283,979 B   54.6%   the modules and the stylesheet
  contract   81,623 B   15.7%   the embedded schemas
  data      154,446 B   29.7%   the payload and the inlined timeline
```

And on the 1,202-element synthetic run
(`bga gen-synthetic /tmp/scale --seed 1`), same round:

```text
total     1,197,665 B  1170 KiB
  source    283,922 B   23.7%
  contract   81,623 B    6.8%
  data      832,120 B   69.5%
```

**Source and contract are the same bytes on both runs** — they are the
page, and a bigger project does not make them bigger. What scales is
the data. On a small project the page is the larger half; on a real one
the data passes it and keeps going, which is the ratio the thinness
rule is about.

> Round 21 measured 638 KiB with the page at 6.0% on the same synthetic
> run, and round 23 measured 158 KiB with the page at 90,611 B on
> `examples/06`. Both are superseded by the figures above — kept
> because a dated measurement is evidence about when the page grew, and
> `UX-132`'s rule is to mark such a figure rather than to rewrite it.
> The page has roughly tripled across rounds 24–64 (the decision panel,
> the rails, the chapters, the table tools, the shape channel, the
> query library) and the embedded contract is new since round 51.

Three ceilings, and they are not all in the same unit. Two are byte
bounds on what is *carried*; the third is on what Perfetto has to
**draw**, which is what actually decides whether a big capture opens
(`UX-430`). None is enforced by refusing to write your report — a
report that large is still your report — and each says which one it
was:

| constant | the bound | measured against | when it is the one that bit |
| --- | --- | --- | --- |
| `EXPORT_BUDGET_B` | 8 MiB | the whole written file: source + contract + data | nothing to do; the note says an attachment may not survive it |
| `TRACE_BUDGET_B` | 4 MiB | the **gzipped trace** before it is base64-encoded — one part of the data half | the trace is left out and the page names the bound; `bga timeline` renders one beside the snapshot |
| `TRACE_TRACK_BUDGET` | 8,000 tracks | the rows Perfetto opens: one process track per element, one thread track per traced pid — **processes**, not slices, so the spine's second record of one process is not a second row (`UX-406`) | nothing, for an export: it renders again with `--planes 1` and the handoff sentence says it did (`UX-530`). For `bga timeline`, `--planes 1` or `--only-element` narrow what is *drawn* rather than what is carried |

The third is the one a reader is least likely to guess at, because the
byte figure looks fine when it bites: measured on the seeded scale run
at twelve processes an element, the trace is **491 KB against a 4 MiB
bound and 16,832 tracks**. `--planes 1` drops the process lanes and is
a 14x reduction there — and 26x at twenty-four processes an element,
since Plane 1's own track count does not move with the process
population (`UX-445`).

`TRACE_TRACK_BUDGET`'s value is one sample and says so — see its
docstring in `tools/bga_view.py`, and `UX-445` for what is still
unmeasured about it.

Since `UX-530` an export **degrades before it refuses**: it renders the
whole timeline, and if that is over either bound it renders again with
`--planes 1` and carries that instead, saying which step it took and
what the whole one would have drawn. Refusal is what is left when every
step `bga timeline` offers is still over. Measured on a capture of the
item's own shape — 8,140 processes over four elements:

```text
both planes    8,152 tracks   8,146 slices     over the 8,000 ceiling
--planes 1         7 tracks       6 slices     carried
```

For CI, put it beside the comment step — see
[`ci-comment.md`](ci-comment.md).

### The Perfetto handoff (`UX-194`)

```bash
bga view --perfetto      # skip the report, hand the timeline straight over
```

`bga view`'s page carries an **Open timeline in Perfetto** button when
the run has one, and `--perfetto` goes there directly. Below 4 MiB the
trace crosses **tab to tab**: the page opens `ui.perfetto.dev`, pings
until it answers, and `postMessage`s the bytes.

**Above 4 MiB compressed, Perfetto fetches it instead** (`UX-299`).
Carrying the trace costs at least two copies of it inside the report
tab — `arrayBuffer()` materialises the whole response and `postMessage`
structured-clones it — before Perfetto decompresses a third in its own;
the `?url=` deep link has none of them. The page finds out which case
it is in with a `HEAD` at the moment you click, because knowing the
size any earlier would mean rendering the trace, which is exactly what
`bga view`'s startup no longer does. The same 4 MiB decides whether
`--export` inlines the trace: above it the exported page says the
trace's size and carries this command instead of the bytes.

**Nothing is uploaded.** It looks exactly like an upload — a public URL
opens and your build data appears in it — so it is worth saying plainly:
ui.perfetto.dev is a static site, the trace is processed in your
browser, and there is nowhere for it to be sent.

The bytes go over gzipped, which Perfetto sniffs itself. Measured on a
real capture of `examples/06` (871 events, both planes merged):

```text
272,964 B  ->  24,782 B   (9.1%, 11x smaller)
```

`--perfetto` needs the server alive while the tab fetches the trace, so
it does not exit the moment the browser launches — Ctrl-C once Perfetto
has it. A run with no raw Plane 2 log has no timeline to hand over and
exits **7** rather than opening a page that would 404.

The handoff page also carries a list of **questions worth asking in
Perfetto** (`perfetto.html`, under the button that opens the trace they
ask about) — thirteen paste-ready PerfettoSQL queries, with a control
that swaps in whichever of this run's elements you are asking about.
They are docs, not a feature: the SQL engine is Perfetto's. `UX-373`
merged them in from the separate `sql.html`, whose URL still redirects
here.

**When to press the button.** The report has no time axis: every number
in it is a total, a per-element aggregate or a ranking. So a question
that needs *when*, or needs one individual **process** rather than the
element around it, is a question for the trace — and one that does not
is already answered on the page. Six of the thirteen canned questions
genuinely need the trip; seven are sharper instruments for something
the page has said already.
[`what-the-viewer-answers.md`](what-the-viewer-answers.md) sorts them,
names the three places the report holds the element's answer and the
trace holds the process's, and says which of the eight
[roles](../design/roles.md) the trip actually serves — R1 and R2 only.

**Format**: `bga timeline` writes **Perfetto's own TrackEvent protobuf**
by default, gzipped as a stream, with `--format chrome` for the legacy
Chrome JSON that `chrome://tracing` and any pipeline already parsing it
still want (`UX-298`). Direction 7 argued for the JSON and named its
revisit trigger; `UX-298` is that revisit, so the argument to read now
is the one in `UX-298` rather than the direction that preceded it.

### View-hints v1

Annotations in the JSON Schema, so a renderer does not have to guess
what a number means. JSON Schema ignores keywords it does not know, so
a hinted document validates exactly as before, and `UX-190`'s rule
applies — adding a hint is an addition; changing what one *means* is a
version bump.

| Hint | Says |
| --- | --- |
| `bga:quantity` | `duration_us`, `bytes`, `share`, `count`, `seconds`, `ratio` |
| `bga:severity` | this array is findings; that key carries the severity |
| `bga:columns` | column order for an array of objects |
| `bga:direction` | `lower_is_better` / `higher_is_better` / `neutral`, for signed deltas |

Read them straight out of the tool:

```bash
bga analyze --schema | jq '.properties.total_duration_us'
# { "bga:quantity": "duration_us" }
```

A quantity outside that closed set, or a hint on a key the document
does not declare, is refused when the schema is built — a mistyped hint
is invisible at the point of use, because the renderer just falls
through and prints a plausible-looking raw number.

## `bga blast` — what rebuilds if I touch this (`UX-172`)

The blast-radius question from whichever end you have it:

```bash
bga blast https://gitlab.example.com/org/monorepo.git @last   # a repository
bga blast components/lib-a                                    # a path in the project
bga blast lib-a.bst                                           # an element
bga blast gitlab.example.com/org/monorepo --no-cost           # structure only
```

The run defaults to `@last`. The target is resolved **url, then path,
then element**, and the answer says which reading it used and which
others also matched — a project can name an element after a directory,
and the command picks deterministically rather than silently.

An identity the run's `sources.json` already knows resolves *before*
those heuristics, so the resource cell the `Shared Sources` table
printed can be pasted straight back in (`UX-178`; `UX-192` stopped the
table eliding long identities, which had reopened it).

| flag | what it does |
|---|---|
| `--project PATH` | the project a relative path resolves against; defaults to the enclosing BuildStream project |
| `--no-cost` | skip the measured rebuild time. The direct set, the closure and the kind split come from the graph and the inventory alone, which on a project of thousands of elements is the difference between a lookup and a full analysis — **0.10s against 3.22s** on the 1,202-element synthetic run (`UX-182`). The answer then says `Cost: not measured` rather than reporting zero |
| `-f, --format` | `text` or `json` |
| `-o, --output` | write to a file instead of stdout |

**A question, not a gate**: `bga blast` exits 0 on an answer of zero the
same as on an answer of two hundred. Gating belongs in `bga compare`,
where the refusal grammar already lives.

The work it reports is the **sum of the blast elements' own durations**,
not wall clock — a build with any parallelism completes it in less.

## `bga compare` — Run-to-Run Comparison

Not a spec-mandated command (`docs/backlog/scenarios/UX-01`) - compares a baseline run against a candidate run and reports signed deltas in certified floors, efficiency score, and attribution, plus a verdict:

```bash
bga compare /path/to/before-run /path/to/after-run
bga compare /path/to/before-run /path/to/after-run --format json | jq '.verdict'
```

The verdict is one of `improved`/`regressed`/`no significant change`/`within the baseline set's own observed range` (`UX-170` — outside the band, but a duration the baseline runs themselves reached, so not evidence of a change)/`not comparable (baseline has no measurable duration)` (a >=1% change in total build duration, relative to the baseline, is the significance threshold), always followed by an explicit caveat when either run's confidence is below the "high" band, and a **refusal** (`UX-78`) when the two runs are not comparable at all — either their graphs share fewer than half their element UIDs (they may not even be the same project) or one is a caches-off run and the other incremental. A refusal prints the failing check to stderr, prints no comparison, and exits **6** — deliberately not 4 or 5, so a CI job keying on the gates cannot read a wrong-artifact-path bug as a regression. `--allow-mismatch` restores the older behaviour: the warning is printed above the comparison and the exit code is the gates' own. Otherwise the exit code is 0 for a successful comparison regardless of verdict — comparing is not itself a failure condition. `--capacity`, if given, applies symmetrically to both runs.

### CI Regression Gate (`--fail-on-regression`)

Not spec-mandated (`docs/backlog/scenarios/UX-03`) - opt-in gating mode for a CI pipeline that wants to actually *fail* on a genuine regression, not just report it:

```bash
bga compare /path/to/baseline-run /path/to/candidate-run --fail-on-regression
```

Exits `4` (a distinct code from 1/2/3, which all mean "`bga` itself failed" - see Exit Codes below) when the candidate run's real total duration (Part 4.3) regressed beyond the threshold - by default, the same >=1% significance rule the verdict uses **when no baseline set was supplied**. With `--baseline-run`s the two can diverge deliberately (`UX-180`): the verdict is judged against the noise band, and `UX-170`'s disputed region withholds a verdict the gate would still fail on. Neither is silent — the report names the rule it applied, and a pipeline that wants the band's judgement should read `verdict`, not only the exit code. Override the threshold with `--regression-threshold PCT` (e.g. `--regression-threshold 5` to only fail on a regression of 5% or more). `total_duration_us` is the one primary gating metric - deliberately not an ambiguous multi-metric combination.

`--format ci-comment` renders the same verdict as markdown for a pull-request comment — the band verdict, every gate with a one-sentence reason, the elements the change added or moved onto the critical path, and (with `--native-report`) which of their declared dependencies nothing read. Render-only: no number in it is computed there, and the gate verdicts come from the same predicates the exit code does. See [`ci-comment.md`](ci-comment.md) for the worked GitHub Actions wiring.

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

Exits `5` - a code distinct from `4`, so a pipeline can warn on "slower" and fail on "less efficient", or vice versa. Gates on **Dispatch Occupancy** (`floors.occupancy_share`, `docs/backlog/scenarios/UX-27`), which is invariant to how much work the build does: adding well-parallelized elements barely moves it, adding serialized ones moves it sharply.

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
- `bga capture run --diagnose` / `--no-inject` (`UX-146`) — what the bwrap shim received and what it exec'd, one JSON line per sandbox, written as `<output>.diagnostics.jsonl` with a summary that **leads with the invocation count**. Zero means the `$PATH` shadow never reached `buildbox-run` and the build ran unmodified, which is a different problem from a sandbox that failed; the two are otherwise the same silence. `--no-inject` runs the build with the shim installed and injecting nothing — it captures nothing and says so, and exists to bisect the argv rewrite against the shadowing itself. Both are on `bga snapshot` too, and neither is sticky.
- `bga capture run --invocation-log PATH` / `--argv-log PATH` / `--raw-log PATH` — where Plane 2 writes its own capture logs. `--invocation-log` defaults to a path beside the report (`UX-80`); `--no-invocation-log` turns it off.
- `bga correlate --cache-logs PLANE3.json` — adds the per-element sandbox tax from a Plane 3 report, which is what the merge half of the granularity findings is computed from (`UX-100`). Without it the split half still runs; the merge half is silent, because the toll is the whole basis for calling an element too small.
- `bga compare --baseline-plane2 A.json --candidate-plane2 B.json` — notes when the candidate's measured memory envelope grew (`UX-104`). Two flags, because reusing one report for both runs would compare a run against itself. A note, never a gate: peak RSS has no measured noise band.
- `bga cache-trend RUN...` — a series, oldest first: per-run hit ratio, transfer seconds and seconds per artifact, churn against the predecessor (with `UX-93`'s labels), and a finding when the newest run leaves the band its trailing window describes (`UX-103`). Refuses a verdict, with exit 6, over a series whose runs are not of the same project and targets — the band would describe neither (`UX-111`). The *commit* is deliberately allowed to vary: a cache-health trend across commits is the only kind there is. The noise model is `bga compare`'s, widened to the fixed rule when the measured band is narrower. Four runs minimum — three trailing plus the one being judged — and it says so rather than trending fewer.
- `bga baseline --glob 'captures/<project>/<commit>-<mode>-b<N>j<M>-*' -n 3 --candidate RUN` — assembles a baseline set from published capture refs and band-compares against it in one command (`UX-96`). Fetches the newest N, untars the refs that predate the uncompressed `run/`, refuses a set whose captures are not comparable (exit 6), and warns when the set was produced by more than one `bga` revision. Absence in a capture's context is read per field (`UX-114`): `trace_spine` and `trace_opens` have a defined default, so a ref published before the field existed is taken under it and mismatches a capture instrumented differently — the assumption is stated either way; `target` and the rest have none, so partial coverage is reported as **unverified** rather than passed over. A band member whose run mode differs from the candidate's is refused with exit 6 too, not the generic exit 2 it used to produce. Every member supplies the band, the newest is also the positional baseline — with three refs that is exactly the `MIN_BASELINE_RUNS` the band needs.
- `bga capture census PROJECT [--json]` — classifies every executable the project's `local` sources stage as static or dynamic, per element, without building anything (`UX-105`). A static ELF has no `PT_INTERP`, never invokes the dynamic linker, and so is invisible to Plane 2's `LD_PRELOAD` hook. `bga capture run` and `bga capture report --project-dir` run the same census and use it to replace the generic static-binary footnote with a named one — or with silence, when there is nothing to name.
- `bga capture run --trace-spine[=off|on|auto]` (`UX-106`/`UX-108`) — also runs a static ptrace process-event tracer inside the sandbox, which records every process whatever its linkage. It is what makes a static toolchain visible at all: `examples/01-resource-contention` traces **0 processes** without it and **24** with it. Each process then carries `spine+hook`, `spine-only` or `hook-only`, and the coverage line is a counted number rather than a disclaimer (`UX-107`). It costs **0.3–1.1 ms per process** — a measured range, not a constant ([why it is a range, with the raw figures](../design/architecture.md#plane-2-knows-the-size-of-its-own-blind-spot)) — which is below the run-to-run spread on a compile-bound build and plainly visible on a process-dense one. **`auto` is the setting to use** (`UX-113`, and what `bga snapshot` defaults to): it pays that cost only for the elements the pre-build census says the hook is blind for, plus any it could not assess — no elements on an all-dynamic project, all of them on a busybox one. The hook stays on either way, since opened paths need in-process interposition and the spine deliberately does not do that. Bare `--trace-spine` means `on`; write `--trace-spine=auto` with the `=`, because the value is optional and a following positional would otherwise be eaten by the flag.
- `bga cache-logs [PROJECT_DIR|LOG_ROOT] --graph RUN/graph.json --native-report PLANE2.json` — Plane 3, BuildStream's own persisted element logs (`UX-91`). Needs no capture at all: it reads what BuildStream already wrote, under `$XDG_CACHE_HOME/buildstream/logs`. **Hand it the project directory** (`UX-127`): it reads the name from `project.conf` and resolves the log root itself. A log root still works, `--list` (or a bare invocation) enumerates the tree — projects, log counts, time spans — and `--all` reports over every project at once. Given a project the tree has no logs for, the error names the project it derived, where it looked, and what is actually there. Reports the per-element phase breakdown, the sandbox tax (`UX-99`) and the configure tax (`UX-102`); `--native-report` puts the traced configure measurement beside the build tool's self-reported one, and `--graph` lets the developer-tax ranking (`UX-101`) tell a rebuild caused by an upstream key change from one whose own definition changed — the logs alone carry no dependency edges.

## `bga correlate` — Join the Two Planes

```bash
bga correlate RUN_DIRECTORY NATIVE_REPORT.json [-f text|json]
```

Joins this run's whole-project analysis (Plane 1) with a native trace report of the *same build* (Plane 2, from `tools/bst_native_build_tracer.py run`) on **element UID** — the only contract between the planes.

It answers what neither plane can alone. Plane 1 knows an element dominates the critical path; Plane 2 knows what happened inside it; only the join says what to do:

```text
Joined 9 element(s) on element UID (11 in Plane 1, 9 traced in Plane 2)
  Memory envelope: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%);
  9 would still fit, so memory is not what binds first here

What to do next (ranked by Plane 1 impact):
  core.bst:
    - holds 45% of the critical path and fixing it is worth 8.0s (20.2% of the build),
      but runs at only 0.89 cores busy - it is waiting, not computing, and its native
      build asked for -j1: remove `notparallel` / raise its job count before touching
      its sources
    - 82% of its measured CPU is one binary, `cc1plus` (10 process(es), 9 CPU s) -
      this element is a `cc1plus` problem, so look there before anywhere else
    (81% of this element's processes were measured)
```

(`examples/06-macro-micro-optimization`, one `bga snapshot`. The
freedesktop-sdk version of the same shape, at 1500× the scale, is in
[`real-project.md`](real-project.md).)

Inside a project this is one line, because `bga snapshot` already
captured both halves and kept them together:

```bash
bga correlate @last
```

Elsewhere, capture both artifacts from one build and name them:

```bash
bga capture run --wrapped-log /tmp/plane1.log --run-dir /tmp/run \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga correlate /tmp/run /tmp/plane2.json
```

Notes on reading it:

- **Ranking is Plane 1's.** Plane 2 explains the top of that list and never reorders it — the question "what should I optimize" is answered by whole-project impact.
- **A restructuring finding comes first, when there is one** (`UX-82`). When a *group* of declared build edges was measured never-read *and* those edges chain elements along the critical path, the join names the chain as one finding and replays this run with those edges removed — same durations, same capacity — to say what removing them would be worth. Five per-element rows saying "`lib-b` never read `lib-a`" are five bricks; this is the wall. The hedge is unchanged: it recommends *checking* the edges, and says the projection is a replay, not a re-capture.
- **Rows are ordered by evidence strength.** A measured CPU concentration or a single-process serialization point leads; the declared-vs-used candidate, which the producer itself calls "evidence, not a verdict", comes last. Dependency pairs `UX-68` set aside as *aggregating* — a `stack` stages almost nothing of its own, so "nobody opened it" says nothing about it — are counted under the coverage line rather than mixed into the findings.
- **The ranking metric is `UX-70`'s realizable saving** — what the build would actually lose if the element became instant, which is the same number `bga analyze` ranks on, so the two commands cannot name different elements first. Share of the critical path is reported beside it because they routinely disagree: an element can hold a large share of a mesh graph and be worth very little to fix. If the metric saturates (every candidate carrying the same value), the report says so rather than presenting the alphabetical tiebreak as an impact order.
- **A negative result is a result.** "Already compute-bound — nothing to gain from its parallelism" tells you to stop looking inside that element.
- **Elements with identical findings share one block** (`UX-89`). Six sibling libraries that are all compute-bound and all `cc1plus`-dominated are one story, not six; the block names them, collapses their figures to ranges, and carries the total worth, while `--format json` still publishes every element separately. A group takes the position of its strongest member, so grouping never reorders what leads, and a finding whose figures do not generalize (peak RSS, a redundant operation's own element list) keeps its own per-element words rather than being averaged into something the measurement does not say.

```text
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

## How many builders, and what stops you

Two Plane 2 numbers answer the `--builders` question, and they answer
different halves of it. Both need a Plane 2 report for the *same* run —
`bga snapshot` keeps one beside every capture, and `bga analyze` takes
one with `--plane2`:

```bash
bga analyze .bga/runs/<stamp>/run --plane2 .bga/runs/<stamp>/plane2.json
```

### The capacity recommendation (`UX-116`)

`capacity_recommendation` intersects every constraint on the joint
`--builders` × `--max-jobs` choice. Each one is already a measured
number in a capture; what was missing was the sentence that puts them
together. Below is one `bga snapshot` of
`examples/06-macro-micro-optimization`, committed at
[`tests/fixtures/macro_micro/`](../../tests/fixtures/macro_micro/) so
you can run it from a clone:

```bash
bga analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json
```


```text
  Capacity: builders 4 x max-jobs unrecorded on 4 core(s): graph binds at 2, below the 4 configured - more builders contend rather than overlap here
    graph allows 2: the sweep's knee is at 2 builder(s)
    CPU allows 9: 1.60 of 4 core(s) busy at builders=4, i.e. 0.40 core(s) per concurrent element
    memory allows 9: the 9-builder envelope fits in 15.7 GB (measured over 9 element peak(s), so it says nothing above 9)
    Free capacity you already have: core.bst asked its native build for -j1 - a builder slot drawing one core. Fix that before raising anything, then re-measure.
```

Three constraints, each with the measurement behind it, and the
**smallest one binds**. Here it is the graph: the capacity sweep's knee
is at 2, so the 4 builders configured are already more than this
dependency shape can use, and adding builders would make them contend
rather than overlap. The CPU ceiling is `host_cores × builders ÷
cores_busy` — measured draw per concurrently-building element, not an
assumption — and the memory ceiling comes from the envelope below.

**Reading it as data.** The block is a key of `analyze/v5`, so a CI job
asks for it the same way it asks for anything else:

```bash
bga analyze tests/fixtures/macro_micro/run \
    --plane2 tests/fixtures/macro_micro/plane2.json --format json \
  | jq '.capacity_recommendation | {binding_constraint, recommended_builders}'
```

```json
{
  "binding_constraint": "graph",
  "recommended_builders": 2
}
```

Absent, not empty, when the block declines — the table below says when
that is. Read `caveat` before acting on `recommended_builders`: it is a
hypothesis to time, not a setting to apply.

**How it is derived, and what it will not do.** One capture in, one
recommendation out: no configuration is tried. The sweep replays the
durations it observed and does not model contention (`UX-14`), and
cores-busy is an average over the whole run rather than over the
contended window — both stated in the payload's own `caveat`, because a
recommendation that hides its shape is worse than none.

**When it declines**, and this is the part worth knowing, because a
missing recommendation looks exactly like an absent feature:

| the block is absent when | because |
|---|---|
| no `--plane2` was given | `cores_busy` is a Plane 2 measurement and there is no Plane 1 substitute |
| the capture recorded no host core count | the CPU ceiling is `host_cores × …`; without it there is no ceiling to state |
| the run context has no builders value | every constraint is expressed *per builder*, so there is no baseline to move from |
| the capacity sweep cannot run | the graph constraint is the sweep's knee; the block does not guess one |
| Plane 2 saw no CPU at all | a recommendation resting on a missing `cores_busy` is a guess wearing a measurement's clothes |

It never recommends a value it has no measurement for. `--builders`
advice that clears the CPU check and blows the memory one is advice to
build into swap, which is why the two are computed together and the
binding one is named.

**The sweep behind it, as data: `sweep/v1`** (`UX-339`). The graph
constraint above is the *knee* of a capacity sweep, and `bga sweep`
prints that whole curve rather than the one number the recommendation
uses:

```bash
bga sweep tests/fixtures/macro_micro/run --format json | jq '.knee_points'
```

| key | what it is |
|---|---|
| `resource` | which resource was swept — `PROCESS`, `DOWNLOAD` or `UPLOAD`. One sweep answers about one of them |
| `sweeps` | one row per capacity tried: the full capacity vector, the makespan the replay produced, and `normalized_improvement` — a **step** gain over the capacity before it, not a total |
| `knee_points` | per resource, the capacity past which more buys little. A resource with no knee is absent rather than zero |
| `monotonicity_violations` | capacities where the makespan got *worse* as capacity rose. The replay model says that cannot happen, so each is a hole in the model rather than a finding about the build |
| `capacity_model_caveat` | what the projection does not model, carried with the numbers rather than beside them: the replay replays already-observed durations and does not model CPU contention rising with concurrency |
| `calibration_capacities` | the capacities that had real measurements behind them. Empty means every point is a projection — the difference between a curve with data in it and one without |

It had **no `schema:` key at all** until `UX-339`, and `bga sweep
--schema` answered the analyze contract — one this document has none of
the required keys of. `UX-328` found that while enrolling three others,
said what was true in the meantime, and filed the contract this is.

**Where it appears.** In the text report, under the headline. It is
**not** a key of `analyze/v5` — `bga analyze -f json` does not carry it
(`UX-275`).

### The memory envelope (`UX-104`)

`memory_envelope` is what decides whether `--builders` can go up, and it
is a published key of [`correlate/v2`](#the-two-plane-join-published-ux-215):

```bash
bga correlate @last -f json | jq .memory_envelope
```

```json
{
  "host_memory_bytes": 16855859200,
  "builders": 4,
  "elements_measured": 9,
  "largest_element_peak_bytes": 160956416,
  "at_observed_builders": {"builders": 4, "envelope_bytes": 643497574,
                           "share_of_host": 0.038, "fits": true},
  "first_builders_that_does_not_fit": null
}
```

Every figure is in **bytes** (`UX-341`: the payload has one spelling
per dimension, and `ru_maxrss` is converted once at the input
boundary), and `share_of_host` is a fraction of `host_memory_bytes`.
The same thing in the text report reads:

```text
  Memory: 4 builders of this shape peak at ~0.6 GB of 15.7 GB (4%); 9 would still fit at ~1.3 GB, so memory is not what binds first here
```

**What it is an envelope of.** The envelope at N builders is the sum of
the **N largest measured per-element peaks**, as if those N elements
built at once *and* peaked at the same instant. That is deliberately a
concurrent peak and not a sum over the whole build: summing every
element's peak would count memory that was never held at the same
moment, and summing only the *observed* concurrency would answer a
question about the run you already have rather than the one you are
considering. Both are upper bounds, and for "is it safe to raise
`--builders`?" an upper bound is the useful direction to be wrong in.

**No safety margin is invented.** `fits` is a strict comparison against
the host's RAM, with nothing reserved for the OS or page cache — so
headroom below 100% is not the same as safe. A reserve would be a
threshold picked from nothing.

**It projects only as far as it measured.** `elements_measured` bounds
the table: N builders can only be N elements building at once, and past
the elements whose peak was measured there is nothing to sum but a
guess. That is why the constraint line above says *"measured over 9
element peak(s), so it says nothing above 9"* rather than reporting a
ceiling it did not reach.

**When it declines.** It is `{}` — and the line simply absent — when
`--plane2` was not given, when Plane 2 recorded no per-element peak RSS,
or when the capture did not record the host's RAM. The arithmetic needs
the peaks and the host together; half of it is not an estimate, it is a
guess. As with the recommendation above, an absent line means *this
capture cannot answer*, not *this tool has no answer*.

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

Both efficiency gates read `occupancy_share`, which needs a
`resource_capacities.PROCESS` in `run-context.json`. Any legacy or
hand-built run directory may have none, and both gates then pass —
correctly, since a verdict must not be fabricated from missing data, but
for a long time silently. A pipeline that believed it was gating on
efficiency saw exit `0`, an empty stderr, and JSON indistinguishable
from a run that had really passed.

Fail-open is still the default. It is no longer silent (`UX-87`):

- stderr carries `Efficiency gate NOT APPLIED: … the baseline run has no
  \`occupancy_share\` signal …`, naming the gate and the run.
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
bga analyze RUN/
```

### 2. Generate JSON Report for CI

Integrate into a CI pipeline to track metrics over time:

```bash
bga analyze RUN/ --format json --output metrics.json
# Then process with jq, e.g. (certified_headroom, not certified_headroom_us -
# confirmed against a real --format json run):
# jq '.floors.certified_headroom' metrics.json
```

### 3. Simulate Hardware Upgrade

Estimate build time improvement if moving from 4 to 16 cores:

```bash
# Current 4-core simulation
bga analyze RUN/ --capacity 4 --replay

# Hypothetical 16-core simulation
bga analyze RUN/ --capacity 16 --replay
```

### 4. Deep Dive into Bottlenecks

Identify which elements to optimize for maximum speedup:

```bash
# criticality_probability is a JSON *object* keyed by element UID
# (confirmed against a real --format json run), not an array - to_entries
# converts it to an array of {key, value} pairs before sorting.
bga analyze @last --diagnostics --format json | \
  jq '.elements.criticality_probability | to_entries | sort_by(.value.probability) | reverse | .[0:10]'
```

## Reading the report

- **Confidence** — how much to trust the numbers below (data completeness/quality of this specific trace). Below "high"? Fix the underlying trace before acting on anything else. A build that *failed* is called out even louder, before any efficiency figure.
- **Certified Headroom** — a *proven* lower bound, not a guess: given the work this build actually did, it cannot possibly finish faster than `T∞`/`LB` (whichever is larger) without changing that work. Headroom above zero means real room to improve scheduling *without touching any element's build steps*; zero means rescheduling cannot help at all.
- **Efficiency Score and Dispatch Occupancy** — deliberately two numbers, because one cannot do the job. **Efficiency Score** asks *"did the scheduler pack this graph well?"*, and everything it is built from comes from the graph this run actually had — so a build whose independent elements were accidentally chained scores a perfect 1.00, correctly and uselessly. **Dispatch Occupancy** asks *"how much of the available slot-time did the run actually use?"* and never consults the graph, so serializing work that could have run concurrently pushes it down. Read them together: a high score with low occupancy means the scheduler did fine and the *graph* is the problem. (Real measured pair: three one-line fixes made a build 30.5% faster while Efficiency Score fell 1.00 → 0.83 and Dispatch Occupancy rose 27.8% → 63.0%. See [`docs/backlog/scenarios/UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md).)
- **Where the time is** — on a build the chain constrains, the headline is one table: each heavy element's duration, its share of the critical path, and what fixing it would actually recover. The rows are ordered by duration because that is what "where is the time" means; the fix order is named separately, because on a dense graph the two disagree.
- **What to do after that** — the next few fixes projected from the same capture: what the build drops to after each, whether the recommended set's savings *add*, and which heavy elements sit off the critical path worth nothing to fix today. Without it, finding the second thing to fix costs another full build. ([`UX-74`](../backlog/scenarios/UX-0074-one-capture-one-finding.md))
- **Elements Most Worth Optimizing First** — on a build the *graph* constrains rather than the chain, this ranks by blast radius instead: fixing a slow element near the root helps every downstream element too.
- **Biggest wait category / Attribution Breakdown** — where wall-clock time went, by category: execution, dependency wait, resource wait, scheduler wait, idle, retries, plus **untracked head and tail** (real wall-clock before the first task started and after the last one finished, which belongs to no task at all). All eight sum to exactly the total build time — nothing is hidden or double-counted, and the two untracked categories are why: on the quick-start fixture above, untracked tail is 12.5% of the build and is the *largest* non-execution category.
- **Critical Path** — the chain that determines total build time, printed in full with each link's duration and share.
- If a hard gate fails (e.g. `critical_path_coverage`), the violation names the specific missing element(s) and whether each is a structural element (`stack`/`import`/…) that never had a real compute task or a genuine gap worth investigating.

Everything in that block is also published as **data**, with a stable `id`, a `severity` and the numbers behind each sentence — so a CI job acts on `.findings[]` rather than re-deriving a threshold or grepping prose:

```bash
bga analyze /tmp/run --format json | jq '.findings[] | select(.id == "time-concentration") | .evidence'
```

```json
{
  "path_us": 3610500000,
  "share_of_path": 0.94035,
  "chain_bound": true,
  "rows": [
    { "element_uid": "components/_private/cmake-stage1.bst", "duration_us": 1569800000,
      "share_of_path": 0.43478, "realizable_saving_us": 1569800000 },
    { "element_uid": "components/python3.bst", "duration_us": 639800000,
      "share_of_path": 0.17720, "realizable_saving_us": 114100000 }
  ]
}
```

The `rows` array is the part a CI comment renders: each heavy element's measured duration, its
share of the chain, and — separately — what fixing it would actually recover, which on a dense
graph is a much smaller number than its share suggests.

## Exit Codes

- `0`: Success.
- `1`: General error (e.g., invalid arguments, missing files).
- `2`: Data ingestion failure (e.g., malformed v9 artifacts), and
  `bga snapshot`'s own refusals — no project here, nothing to run, and
  (`UX-324`) a build command whose executable will not run, which is
  declined before anything is written.
- `3`: Analysis failure (e.g., graph cycles detected).
- `4`: **not "slower" alone.** `bga compare` returns it for any of three things, and a CI job that triages it as a duration regression will mis-read two of them:
  - `--fail-on-regression` and the build's total duration really did regress beyond the threshold (`docs/backlog/scenarios/UX-03`);
  - the **build-failure gate** (`UX-54`) - either run describes a build in which an element FAILED, so no scheduling verdict is meaningful. This fires whenever *any* gate was requested, including when only the efficiency gates were;
  - `--fail-on-low-confidence` and a run's confidence is below the "high" band.

  Read the stderr line, which names which of the three fired. All three are distinct from 1/2/3, which mean `bga` itself failed to run.
- `5`: `bga compare --fail-on-efficiency-regression`/`--min-efficiency`/`--fail-on-inefficient-additions` only - the build became meaningfully *less efficient*, whether or not it also got slower. Deliberately distinct from `4`: "slower" and "less efficient" are different verdicts and often different teams' problems (`docs/backlog/scenarios/UX-39`).
- `6`: **refused as not comparable** - not a verdict about the build at all, which is why it does not share a code with one. Two commands return it: `bga compare`, when the two runs share fewer than half their element UIDs or one is a caches-off run and the other incremental (`docs/backlog/scenarios/UX-78`; `--allow-mismatch` overrides); `bga cache-trend`, when the series is not all of one project and target set, in which case the per-run rows still print and only the band verdict is withheld (`docs/backlog/scenarios/UX-111`); and `bga baseline`, when the assembled set's captures are not comparable to each other (`docs/backlog/scenarios/UX-96`).
- `7`: `bga compare --require-efficiency-signal` only - an efficiency gate was requested but could not be evaluated, because a run has no `occupancy_share`. Like `6`, not a verdict about the build: `4` would say it got slower and `5` would say it got less efficient, and neither was determined (`docs/backlog/scenarios/UX-87`). Without `--require-efficiency-signal` the same situation exits `0`, prints an `Efficiency gate NOT APPLIED` line to stderr, and publishes `efficiency_gate_evaluated: false`.
- `130`: **interrupted** (`UX-157`, `UX-163`). Ctrl-C during a capture is
  not a failure and not a verdict: whatever the build completed is kept,
  analyzed, and labelled as a build that did not finish. A comparison
  against that snapshot obeys the same incompleteness rules as any
  unfinished build. Interrupting *before* the build starts leaves
  nothing behind and says so — and so does a machine that cannot start
  the build at all, which refuses with `2` before creating a snapshot
  (`UX-324`).

## See Also

- [Project README](../../README.md)
- [Architecture Overview](../design/architecture.md) — both analysis planes, and every extension beyond the original spec
- [v9 Specification](../spec/specification.md)
