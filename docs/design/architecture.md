# `bga`: Current Architecture — Three Analysis Planes

**Start here to orient in this codebase.** `docs/spec/specification.md` (v9) is the original design document and stays authoritative for full-length invariant/data-contract text — it is *not* wrong, but it describes the tool as originally scoped, and does not know about anything built since. This doc describes what `bga` actually does **today**, as one coherent system, and points at the real file/doc for every claim so you don't have to reconstruct that history from 75 `docs/backlog/scenarios/` files, 75 `docs/backlog/tasks/` files, and the commit log yourself.

**Want to *use* the tool rather than work on it?** [`docs/guides/real-project.md`](../guides/real-project.md) is the end-to-end walkthrough on a real project, with real output at every step.

## The shape of the tool today

`bga` was designed as a single-plane analyzer: given one real BuildStream run's element-level log, reconstruct the dependency graph, classify every wait gap into one of 8 attribution categories, and report certified/advisory floors — a **whole-project** view. That plane is real, done, and still the tool's core (`docs/spec/specification.md`'s v9 design, unchanged in its fundamentals).

What's changed since: two more planes, each a different **source of evidence** about the same builds, each deliberately kept as its own mechanism with its own horizon rather than folded into the first plane's `Σattribution == H` accounting.

- **Plane 1 (whole-project, spec-native)** answers *"which elements/phases dominate this build's critical path, and where is real scheduling/resource capacity being wasted across the whole run?"*
- **Plane 2 (intra-element, `UX-11`)** answers *"inside this one element's own sandbox, is its native build system actually achieving the parallelism it should, or silently serializing / contending against sibling elements?"*
- **Plane 3 (BuildStream's own persisted logs, `UX-91`)** answers *"what has this project been spending its time on across every build already on this machine — and how much of each element's time never reached the build at all?"*

The three differ in what they cost to obtain, which is most of why there are three:

| | source | needs | horizon | resolution |
|---|---|---|---|---|
| **Plane 1** | one run's element-level log | nothing live — a captured log analyzes anywhere | the whole run | milliseconds, ±1.5s of read-lag (`UX-110`) |
| **Plane 2** | processes inside the sandbox | a live `bst` + `bwrap` build, captured deliberately | one element's sandbox | microseconds, per process |
| **Plane 3** | `~/.cache/buildstream/logs` | **nothing at all** — the logs are already there | every build on the machine | one second, per activity |

No plane subsumes another. Plane 1 sees one START/SUCCESS pair per element and nothing below it. Plane 2 sees everything below it and has no idea what the schedule around it looked like. Plane 3 sees neither the schedule nor the processes — but it is the only one that is **free and retrospective**: it needs no capture, no flags, and no foresight, because BuildStream wrote the logs during builds that already happened.

### Where the planes connect

Plane 1 already tells you *which* elements are worth fixing and by how much (`UX-70`'s realizable saving, `UX-74`'s horizon, `UX-22`'s serialization-point detection). Plane 2 can now tell you, for any *one* of those elements, exactly what its own native build system spent its time on. Running Plane 2 across **multiple** elements of the same project opens a genuinely new class of question neither plane can answer alone: are several elements each independently, redundantly doing the *same* real sub-work inside their own sandboxes — the same expensive `configure` step, the same codegen invocation, the same dependency-resolution pass — that could be shared or cached once instead of paid for by every element separately?

**Confirmed real, not hypothetical, and now automatically detected** (`UX-23`, done): a real, fully-fresh `bst build all.bst` capture of `examples/05-cmake-cpp-toolchain` (6 cmake elements) traced under Plane 2, with real `--dir`-based element tagging, produced **37 redundant-operation findings, every one correctly spanning all 6 real elements** - including the exact CMake compiler-ABI-detection probe this section originally found by hand. Implementing element-tagging also surfaced and fixed a real, previously-latent correctness bug in `UX-11`'s own original design: pairing traced process START/END events by pid alone is unsound once a trace spans multiple elements, since each element gets its own independent `--unshare-pid` namespace and the same small pid number recurs across every element's sandbox. `UX-24` (Chrome Trace export for Plane 2, and a combined two-plane `perfetto.dev` view) is done too: one real single `bst build` invocation now captures both planes at once (`bst_native_build_tracer.py run --wrapped-log`), and a real end-to-end run confirmed the two clocks correlate correctly - Plane 2's earliest event landed exactly on Plane 1's own real build-start timestamp. Closest existing relatives: `UX-20` (batch/map-reduce simulation, but over already-observed element durations, not intra-element operation identity) and `UX-14`'s tier-2 design (PR #58/#61, cross-run calibration, a different but related use of multi-capture comparison).

## Real current CLI surface

Confirmed against `bga/cli.py` directly, not the original spec's Part 37 proposal (which this matches closely — see each subcommand's own `description=` citing its spec Part):

| Command | What it reports | Spec Part |
|---|---|---|
| `bga analyze RUN` | Full report — every section below, in one invocation | all |
| `bga graph RUN [--by-kind]` | Static dependency graph, critical path, structural (M6) metrics | 5, 14.1, M6 |
| `bga floors RUN [--cold] [--allow-partial-cold]` | Certified/advisory floors: `T∞`, `LB`, certified headroom, cold floor | 14–17 |
| `bga replay RUN` | Deterministic replay makespan (`T_C`) | 18 |
| `bga sweep RUN --resource R` | Capacity sweep for one resource — predicted `T_C` curve, knee point | 19 |
| `bga utilisation RUN` | CPU utilisation accounting | 30, M4 |
| `bga diagnostics RUN` | Blast radius, criticality probability, wall-clock shares | 20–29, M5 |
| `bga correlate RUN NATIVE_REPORT` | Joins this run with a Plane 2 native trace of the same build on element UID, and says what to fix. **Not spec-mandated**, `UX-51` | — |
| `bga compare BASELINE CANDIDATE` | Run-to-run deltas + improved/regressed verdict, and **two independent CI gates** — duration (`--fail-on-regression`, exit 4) and efficiency (`--fail-on-efficiency-regression`/`--min-efficiency`, exit 5); `--baseline-run`/`--band-k` compare against a baseline *set* instead of a fixed threshold. **Not spec-mandated**, `UX-01`/`UX-03`/`UX-39`/`UX-59` | — |
| `bga cache-trend RUN...` | Is the cache getting worse? A chronological *series*, not a pair — hit ratio, transfer seconds, churn per step, and a finding when the newest run leaves the band its trailing window describes. **Not spec-mandated**, `UX-103` | — |
| `bga cache-logs [LOG_ROOT] --project NAME` | **Plane 3** — BuildStream's own persisted element logs: per-element phase breakdown, sandbox tax, configure tax, developer tax. Needs no capture. **Not spec-mandated**, `UX-91`/`UX-99`/`UX-101`/`UX-102` | — |
| `bga capture run\|report\|census PROJECT` | **Plane 2** — trace processes inside element sandboxes (`--trace-opens`, `--trace-spine`), re-render a saved report, or run the static-binary census with no build at all. **Not spec-mandated**, `UX-11`/`UX-105`/`UX-106` | — |
| `bga baseline --glob REFS -n N` | Assemble a baseline *set* from published capture refs and band-compare against it in one command, refusing a set whose captures are not comparable. **Not spec-mandated**, `UX-96` | — |
| `bga wrap` / `extract` / `rebuild-set` / … | Thin aliases dispatching to the programs in `tools/`, which stay independently runnable as `python3 -m tools.<module>` — the workflow reads as one tool without merging the code. **Not spec-mandated**, `UX-67` (`bga/tools_dispatch.py`) | — |

Every conclusion the text report draws is also published by `--format json` as a `findings` array, each entry with a stable `id`, a `severity` and the numbers behind it (`UX-75`). Both renderers consume the same list, so they cannot disagree, and a CI consumer keys on `id` rather than re-deriving a threshold out of the renderer.

## Real package structure (Plane 1)

`bga/` mirrors the spec's own pipeline stages fairly directly:

```text
ingest/       -> load run-context/v9, graph/v9, trace/v9 (Part 32 data contracts)
normalize/    -> timestamp quantization, clamp, violation reporting (Part 3)
occupancy/    -> per-resource interval sweep (Part 4)
graph/        -> EDG, critical path, dominators, depth (Part 5, 14.1)
attribution/  -> blame-chain walk, 8-category wait-gap classification (Part 7-12)
floors/       -> LB/capacity/cold/serialization floors (Part 14-17)
replay/       -> deterministic scheduler, capacity sweep, duration_overrides hook (Part 18-19)
utilisation/  -> CPU accounting (Part 30, M4)
diagnostics/  -> blast radius, Monte-Carlo criticality, leaf/deferrability (Part 20-29, M5)
structural/   -> M6 graph metrics, batching (UX-20), serialization-point detection (UX-22)
validation/   -> determinism harness, invariant checks, provenance (Part 35, I1-I13)
findings.py   -> every conclusion the report draws, as data (UX-75) - the single
                 place that decides what is worth saying; both renderers read it
correlate.py  -> the two-plane join (UX-51), a third consumer of two finished
                 artifacts that neither plane knows about
tools_dispatch.py -> `bga <alias>` -> tools/ programs, lazily imported (UX-67)
report/       -> text/JSON rendering (presentation only, since UX-75)
```

`tools/` is a separate, deliberately-not-`bga`-internal set of scripts that turn a real `bst` invocation into `bga`-ingestible input (needs a live `bst`+`bwrap` install; `bga` itself never does) — full data-flow diagram in `docs/spec/ingestion-pipeline.md`. `tools/bst_native_build_tracer.py` (+ `tools/native_trace/`) is Plane 2 — see below.

One script in `tools/` is not part of that pipeline and needs no `bst` at all: `tools/gen_synthetic_scale_run.py` emits a synthetic run directory (`graph.json`/`trace.json`/`run-context.json`) at a scale no example project in this repo reaches — by default 1202 elements over 14 real levels, scheduled onto 16 builders by a real dependency-respecting greedy pass so the trace satisfies the same ordering and capacity properties a real capture does. It exists because the second audit round found four defects that were invisible at eleven elements (`UX-41`–`UX-44`), and their acceptance tests all cite this fixture; running it with the same `--seed` reproduces the directory byte-for-byte. It exercises `bga`'s **analysis** side only — nothing about a synthesized run directory says whether the capture tools survive a thousand-element build.

## Plane 2: intra-element native-build-system tracing (`UX-11`)

`tools/bst_native_build_tracer.py` wraps a real `bst build` invocation: a `bwrap` shim placed ahead of the real binary in `$PATH` injects an `LD_PRELOAD` hook (`tools/native_trace/hook.c`) into every dynamically-linked process the sandbox execs, recording real `CLOCK_MONOTONIC` start/end timestamps. Validated end-to-end against a real `cmake`+`make`+`gcc` build (98 real traced processes, reproduced real `-j4` compile concurrency across independent runs). Known, honestly-reported limitation: statically-linked processes are invisible to this mechanism and there is no way to detect that gap from outside — every report carries a fixed disclaimer rather than a false completeness claim. Full design history (five brainstormed options, an external design contribution, a risk-reduction spike, a second external review that was checked and refuted, and the final validated mechanism) is in `docs/backlog/scenarios/UX-0011-native-build-system-profiler-tool.md` — read that only if you need the *why*; this doc is the *what, today*.

The hook records four things per process. The first is what `UX-11` shipped; the rest arrived as later rounds found questions timing alone could not answer:

1. **Lifecycle** (`UX-11`) — `CLOCK_MONOTONIC` START/END, which is what every timing analysis below is built on.
2. **Real CPU time** (`UX-45`) — `getrusage(RUSAGE_SELF)` plus `RUSAGE_CHILDREN` in the destructor, the one place with access to the kernel's own accounting for a process about to exit. This is `bga`'s **only** CPU-time measurement anywhere; everything in Plane 1 is slot occupancy, and deliberately still says so (see `UX-36` below). Its value is a question Plane 1 structurally cannot answer — *was this element CPU-bound or waiting?* On a real capture, `core.bst` (pinned with `notparallel: True`) runs at **0.87 cores busy** while every sibling runs at ~1.7. Coverage is always reported: a process killed by a signal, or one replaced by `exec`, runs no destructor and is counted as **unmeasured**, never as zero (~19% of processes in a real `examples/06` build).
3. **Peak resident memory** (`UX-63`) — `ru_maxrss` from that same `getrusage` call, giving a *measured* per-element peak where the memory-oversubscription guard had only ever had operator-declared estimates. Reported as "no single process here exceeded this", never summed: two processes peaking at different moments never held the sum between them.
4. **Opened file paths** (`UX-46`, opt-in via `--trace-opens`) — `open`/`openat` interposition, deduplicated in-process and flushed once at exit, and re-flushed rather than dropped when the window fills (`UX-57` — the fixed buffer had been losing 70% of a real build's opens). Opt-in because unlike the others it runs on a genuinely hot path. Matched against `bst artifact list-contents`, this answers *"which of this element's declared build dependencies did its sandbox never read?"* — the last macro-level gap, and the one problem in `examples/06` that no Plane 1 signal could find. It **refuses rather than guesses**: an element with no observed opens (a statically-linked build looks identical to one that used nothing) or with a truncated read set is reported `uncovered`, never as having unused dependencies.

### Element attribution: the hardest thing in Plane 2

Every traced process is tagged with its owning BuildStream element (`UX-23`, originally parsed from BuildStream's own `--dir` bwrap option). That parse is a *path convention*, and a real project overrides it: on `freedesktop-sdk`, which sets `build-root: /buildstream-build`, **99.4% of 127,630 processes landed in one bucket that is not an element** (`UX-56`), and every per-element figure was a whole-build figure wearing an element's name.

The fix does not guess. Each sandbox is correlated against Plane 1's own BUILD spans, on the sandbox's **end** edge — chosen by measurement, not by argument: requiring the whole interval inside the span resolved 2 of 9 sandboxes with 7 unmatched, because Plane 1 timestamps a line when the wrapper reads it and every sandbox therefore begins *before* its element's logged BUILD START; matching on the end edge resolved 8 of 9 with none unmatched (`UX-64`). The same work removed an unsound elimination pass: a real project runs more than one sandbox per element, so striking a resolved element from every other candidate set could attribute a sandbox to the *wrong* element.

Measured on a real capture, in order: **0.6% → 14.9% → 86.1%** of processes attributed to a named element. The remainder sits in an explicitly unresolved bucket, and every consumer states its coverage rather than folding it in — including `detect_redundant_operations`, which had been counting that bucket as a second element and thereby sourcing **87% of its claimed recoverable time from an element that does not exist** (`UX-73`).

### What is built on the per-element split

`compute_binary_cost` (`UX-69`) reports, per element, where the CPU actually went — binaries ranked by measured CPU rather than by invocation count, with the single-process case called out separately. On a real capture `cc1plus` is **81.3% of the CPU** of the element that is 43.5% of the build, and `dwz` is **one process holding 138.6s**, a serialization point no job count can help. Ranked by count neither is visible: `as` runs twice as often as `cc1plus` for a tenth of the cost.

`compute_per_element_parallelism` (`UX-32`) reports, per element, the parallelism its native build system *actually achieved* against the `-jN` it asked for - splitting real work processes (compilers, assemblers, linkers) from orchestration that spends its life waiting on children, and emitting two findings: `pinned_to_one_job` (this element asked for `-j1` while its siblings asked for more - the `notparallel` case, invisible to any achieved-vs-requested ratio, since a pinned element gets exactly what it asked for) and `underachieved_requested_jobs`. `detect_redundant_operations` (`UX-23`, rescored by `UX-37`) flags real operations repeated independently across multiple elements' own sandboxes, ranked by *recoverable wall-clock* rather than by process time summed across elements that ran concurrently, and excluding both each element's own build driver (identical across elements by construction, entirely different work in each — `UX-37`) and its own top-level command block, which bwrap's PID namespace identifies structurally rather than by string matching (`UX-73`). `tools/native_trace_to_chrome_trace.py` (`UX-24`) exports Plane 2 traces as Chrome Trace JSON, standalone or combined with Plane 1's own real export for the same run — `bst_native_build_tracer.py run --wrapped-log PATH` captures both planes from one single real `bst build` invocation.

## Plane 3: BuildStream's own persisted logs (`UX-91`)

BuildStream writes a per-element log for every task it runs, and keeps
them: `$XDG_CACHE_HOME/buildstream/logs/<project>/<element>/<key>-<action>.<timestamp>.log`.
They were sitting on every developer's machine, unread by anything.

`bga cache-logs [LOG_ROOT] --project NAME` reads them. It is the only
part of this tool that needs **no capture, no flags and no foresight** —
the evidence is a by-product of builds that already happened, including
builds nobody thought to instrument.

What that buys, and what it costs:

- **Per-element phase breakdown.** Each log carries BuildStream's own
  timed activities — `Staging dependencies`, `Integrating sandbox`,
  `Running commands`, `Caching artifact` — at one-second resolution.
- **The sandbox tax** (`UX-99`): how much of each element's time went to
  staging, integrating and caching rather than to the build itself. On
  freedesktop-sdk it is **13.0s of 4409.0s (0.3%)** — and the answer
  being *small* is the point: the toll is what the merge half of the
  granularity advice is computed from (`UX-100`), and a project where it
  is 0.3% has no elements that are too small to be worth their own
  sandbox.
- **The configure tax** (`UX-102`): what the build tools themselves say
  they spent answering configure questions. Counted only where the build
  tool reports it — cmake does, autotools' `configure` and meson do not
  — so on an autotools project this is a floor of zero rather than a
  measurement, and the report says so and points at Plane 2's traced
  view instead. With `--native-report`, both figures are shown per
  element, side by side and **never summed**: one is wall-clock the tool
  self-reported, the other is CPU seconds traced, and adding them would
  invent a quantity.
- **The developer tax** (`UX-101`): which elements this project has spent
  the most time rebuilding, across every build in the tree. With
  `--graph` it can separate a rebuild caused by an upstream key change
  from one whose own definition changed — the logs alone carry no
  dependency edges.

The costs are stated in the report itself, every time: one-second
resolution, no `--builders`, no `--max-jobs`, no scheduler context, no
timestamps inside `Running commands`, and **no session id** — a log's
header is its own task's start, not its build's, so the number of builds
is a lower bound taken from the most-rebuilt element, never a count.
Nothing in Plane 3 may feed a certified floor, and the report says that
too.

## Joining the planes (`UX-51`, `UX-100`)

Planes 1 and 2 are joined by `bga correlate RUN_DIR NATIVE_REPORT.json`, and the contract between them is **one string**: the element UID. Plane 3 joins the same command through `--cache-logs PLANE3.json`, which is what the *merge* half of the granularity findings is computed from (`UX-100`) — without it the split half still runs and the merge half stays silent, because the sandbox toll is the whole basis for calling an element too small. That choice was made by measuring rather than arguing, and the measurements are worth keeping because they also say why the alternative is closed:

- **A merged capture would buy nothing.** `UX-24`'s `run --wrapped-log` already produces both artifacts from one real `bst build`.
- **The join key is exact.** On a real dual capture of `examples/06`, 9 of 9 Plane 2 elements matched Plane 1 UIDs with zero mismatches; the only Plane 1 elements absent were a `stack` and an `import`, which run no build commands, so their absence is correct.
- **The horizons cannot be merged**, per this doc's own argument above — Plane 2 measures inside one element's sandbox and shares no horizon with an element-level trace. Anything called a merge would be a join with a misleading name.

So `bga/correlate.py` is a third consumer that reads two finished artifacts and neither plane knows about, leaving both independently replaceable. It produces the sentences neither can alone, ranks by Plane 1 impact (Plane 2 explains that ranking, never reorders it), carries `UX-45`'s measurement coverage through so a partial result says so, and names elements Plane 1 ranks that Plane 2 never traced rather than passing over them in silence.

Four properties of the join are worth stating because each was a defect first:

- **It ranks on what a fix is worth.** It used to rank and gate on `sensitivity.top_opportunities`, whose score is `min(duration, next_binding_gap)` — a correct upper bound and a useless ranking, because the cap is a constant over exactly the population being ranked. On a real capture all five candidates scored an identical `0.0316`, so the order was the alphabetical tiebreak and the gate never opened for anything, making the join's own headline verdict unreachable. It now reads `UX-70`'s realizable saving, the same number `bga analyze` ranks on, so the two commands cannot name different elements first (`UX-71`).
- **It reads all of Plane 2, ranked by evidence strength.** Every row used to be the same explicitly-hedged declared-vs-used sentence while `binary_cost`, `peak_memory` and `redundant_operations` sat unread in the file it had just opened. It now carries all of them, strongest measurement first and the hedged one last, with that class published as an `id` and a `severity` rather than implied by ordering (`UX-72`, `UX-75`).
- **It refuses fiction.** Plane 2's own element test is syntactic — a name ends in `.bst`, which is all Plane 2 can do alone. The *declared graph* is a Plane 1 fact, so the join checks against it: a bucket name the graph never contained is excluded from every recommendation and listed, rather than quietly recommended (`UX-66`). On the real capture that is exactly `buildstream-build`, `flit_core`, `unknown`.
- **Negative results are load-bearing.** "Already compute-bound at 3.41 cores busy" tells a reader to stop looking inside that element, which is worth as much as a positive finding and much easier to skip past.

## The ingestion path now measures itself (`UX-105`–`UX-110`)

Every plane above rests on an ingestion mechanism, and each mechanism
used to be trusted rather than measured. A capture said what it found;
nothing said what it could not have found. The most recent round closed
that, and the pattern is the same in all four cases: **the same quantity,
obtained twice, is a free test** (`UX-53`) — so wherever a second source
existed, it was wired up.

### Plane 2 knows the size of its own blind spot

`LD_PRELOAD` structurally cannot see a statically-linked process: no
dynamic linker runs, so nothing loads the hook. Every Plane 2 report used
to carry one fixed footnote about that, which fired identically on a
capture that missed nothing and on one whose entire process list was
empty.

- **`bga capture census PROJECT`** (`UX-105`) classifies every executable
  the project's own sources stage — ELF header arithmetic, no build, no
  BuildStream. `examples/01-resource-contention` reports **5 static
  executables reaching 10 of 10 elements**; `examples/06`'s glibc
  toolchain reports zero and gets silence instead of a warning.
  Classification reads `e_type` as well as `PT_INTERP`, because
  `PT_INTERP` alone calls every shared object on the system a static
  binary — measured, on a real sysroot, before it was believed.
- **`bga capture run --trace-spine`** (`UX-106`) adds a static ptrace
  process-event tracer inside the sandbox that records every process
  whatever its linkage. On `examples/01` that is the difference between
  **0 processes and 24**.
- **The two record streams are one process list** (`UX-107`). A
  dynamically-linked process is now recorded twice, and consumed naively
  that double-counts every one: on `examples/06`, 1644 records read as
  1644 processes and **112.61 CPU seconds for a build that used 58.47**.
  They are joined on `(invocation, pid)` and a START inside a tolerance,
  every entry carries `spine+hook` / `spine-only` / `hook-only`, and
  coverage stops being a footnote and becomes a count. Verified at scale:
  **127,632 processes on freedesktop-sdk, all one class**.
- **Opens-dependent findings state their scope.** Declared-vs-used
  (`UX-46`) now computes over the hook-covered processes and says what
  share that is — `examples/01`'s eight static elements are reported
  `UNCOVERED - 0 of 3 process(es) … were reachable by the LD_PRELOAD
  hook` instead of being skipped in a silence that reads as "no unused
  dependencies".

The spine is **opt-in**, and that is a measurement too (`UX-108`):
**+2.7%** wall on `examples/06` over ten runs per mode, **+13.5%** on
`examples/08-process-storm` (575 processes/second, a fixture built
because no project in this repository was process-dense enough to ask
the question). The rule was stated before the numbers — under 2% it
defaults on, over it stays a flag — and the numbers chose. Those two
percentages are kept as the figures that made the decision; `UX-112`
then showed the ratio is a fact about the fixture's baseline rather than
about the tool, and the per-process form below supersedes them.

`UX-112` later re-measured that as a full {spine} × {opens} factorial and
found the ratio unstable and the unit wrong. `UX-129` then found the
replacement headline overshot too, and narrowed it to what five
independent measurements support: the price is **0.3 to 1.1 ms per
process**, below the spread on `examples/06` and clearly visible on
`examples/08`. The spread is machine state rather than uncertainty
within a run — the tightest measurement, five interleaved `off`/`on`
pairs, gives +0.79s on 2003 processes (0.39 ms), with the raw figures in
[`docs/audits/data/spine-cost-storm.md`](../audits/data/spine-cost-storm.md). The predicted spine × opens interaction is
not there — on the process-dense fixture the spine is *cheaper* alongside
opens, because opens raises the baseline. `UX-113`'s
`--trace-spine=auto` follows directly: pay that cost only where the
census says the hook is blind — which is also why the exact size of it
matters less than it looks.

### Plane 1 knows the resolution of its own timestamps

A wrapped log line is stamped when the wrapper *reads* it, and
BuildStream flushes in bursts, so both ends of every span carry a
read-lag. The same log already contained the check: BuildStream's own
`[HH:MM:SS]` elapsed prefix is an independent measurement of the same
task. Nothing was comparing them (`UX-110`).

Compared across three real builds from 12s to 3261s, the envelope is
**-0.56s to +1.50s and does not grow with the task** — 0.03% of a
1415-second element and 11% of a three-second one, which is why it went
unseen. `bga analyze` now states the resolution where it is a material
share of some task, and names any task reported as *shorter* than
BuildStream timed it, which is a duration that did not happen rather than
one measured imprecisely.

It is **compared, never substituted**: the elapsed prefix is a
second-resolution lower bound, and moving a span's endpoint to satisfy it
would manufacture overlap the capacity model reports as a violation.

### What this is worth

The tool's whole posture is that a number nobody can check is not a
measurement. These four changes apply that to the layer underneath every
number the tool prints — so a report can now distinguish, in its own
output, between *"we looked and found nothing"* and *"nothing could have
looked"*.

## What the 2026-08-16 audit round changed structurally

`UX-27`..`UX-40` were mostly small fixes, but three of them changed the
*shape* of what the tool asserts, and those are worth knowing before
reading anything else in this doc.

### 1. Efficiency is now two numbers, not one

`efficiency_score` (`UX-02`) is `LB / horizon`, and every input to `LB`
is derived from the graph the run actually had. That makes it a correct
answer to *"did the scheduler pack this graph well?"* and a structurally
impossible answer to *"was this graph worth packing?"* - a build whose
independent elements were accidentally chained has a critical path equal
to its own total work, so `LB == T∞ == T_C` identically and the score is
1.00.

Measured, not argued: on `examples/06-macro-micro-optimization`, three
one-line fixes made a real build **30.5% faster** while
`efficiency_score` moved **1.00 → 0.83** and `certified_headroom` moved
**0.00s → 4.05s**. Both backwards.

`floors.occupancy_ratio` (`UX-27`) is the second signal - `Σ task
slot-occupancy / (horizon × builders)` - and it never consults the graph,
so serializing work that could have run concurrently pushes it down. On
the same pair: **27.8% → 63.0%**. Neither number is redundant and neither
replaces the other; the report prints them adjacently, and a high score
beside a low occupancy is the specific reading that means *"the scheduler
did fine, your graph is the problem"*.

Known weakness, stated in the source rather than hidden: the numerator is
slot occupancy, not CPU time (P1-33/`UX-36`), so it inflates under
contention. It is an honest directional signal, not a precise one.

### 2. Capacity has a single verdict, and everything conditions on it

Before this round the capacity guards (`UX-12`/`15`/`16`/`17`/`21`) were
inert on every run the documented pipeline produced, because
`native_max_jobs` was operator-only (`UX-29`), and the bar they compared
against was BuildStream's own default rather than the real core count
(`UX-28`). Both are fixed, and the resulting verdict is now published
once as `AnalysisResult.capacity_verdict`:

```text
{"oversubscribed": bool, "undersubscribed": bool,
 "checks_ran": bool, "skipped_inputs": [...]}
```

Consumers condition on that dict rather than re-deriving capacity
arithmetic - `UX-35`'s next-step hints are the first, and the rule is
`UX-17`'s own: two independently-derived formulas comparing the same real
inputs will eventually disagree about the same real condition.
`checks_ran` is load-bearing and deliberately separate from
`oversubscribed: false` - "we checked and it is fine" and "we could not
check" are different claims, and the report says which one it is making.

### 3. The CI posture is two gates, not one threshold

`--fail-on-regression` (`UX-03`) answers "did the build get slower".
`--fail-on-efficiency-regression`/`--min-efficiency` (`UX-39`) answer
"was the work this build does being done efficiently", on `occupancy_ratio`,
with their own exit code `5`. The separation exists because on a growing
project those verdicts diverge, and measurably do: two well-parallelized
elements added to a real project took wall-clock **+2.5%** (failing the
duration gate) while occupancy **rose 13.8pp** (passing the efficiency
one).

The efficiency gate's default tolerance is derived from three repeat
captures of an unchanged project on one real runner (1.0pp of observed
occupancy noise, against 7.4% of wall-clock noise - which is itself the
measured evidence that the duration gate's own 1% default sits below the
noise floor).

## What the real-capture rounds (7–10) changed structurally

Rounds 1–6 were measured against builds this repository wrote itself. From round 7 the tool has been audited against a real `freedesktop-sdk` capture, and four things changed shape as a result.

### 1. The report ranks by what a fix is worth, not by how big something is

`share of the critical path` answers *what is this chain made of*. It does not answer *what happens if I change it*, because it holds the rest of the graph fixed — and on the real capture **97 of 126 elements have zero slack**, so the rest of the graph does not stay fixed at all. `compute_realizable_savings` recomputes the longest path with each candidate zeroed: `python3.bst` holds **17.7%** of the path and eliminating it entirely saves **3.2%** of the build, because a near-tie chain takes over the moment it shrinks (`UX-70`). `zero_slack_share` is published beside it, because *chain or mesh* decides whether "optimize the top element" is meaningful advice at all.

### 2. One capture answers more than one question

A real capture costs ~60 minutes; a longest-path recomputation costs 0.40 ms. `UX-74` spends a handful of the latter to publish what becomes binding after each fix, what the recommended set is worth *together* (simulated — on a chain savings compose, on parallel branches they take a maximum, and only the simulation knows which), and which heavy elements sit off the path worth nothing to fix today. On the real capture the 4th and 6th heaviest elements in the whole build appear in no ranking, correctly, and are now named anyway.

### 3. Conclusions are data, not prose

Every judgement the report makes lives in `bga/findings.py` with a stable `id`, a `severity` and its numeric evidence; `bga/report/text.py` renders that list and `bga/report/json.py` publishes it (`UX-75`). Before this, `--format json` carried every number and none of the conclusions, so a CI consumer had to re-implement the structural exclusion and four thresholds out of the renderer — and two implementations of one judgement is precisely how `analyze` and `correlate` had already drifted (`UX-71`). A finding that is not produced cannot appear in either format; that property is tested, not asserted.

### 4. The known gap, stated rather than papered over

**Both CI scenarios are now captured.** Rounds 6-10 were all incremental — 25 elements built, 65 skipped — which meant the critical path every round measured was the chain through the rebuilt elements rather than the project's real one. Round 11 took the first caches-off capture (`UX-86`): `bootstrap/build/gcc-stage1.bst`'s whole 18-element closure built from source with remotes ignored, 0 cached, 34.2 minutes, confidence 1.00. The constraint that produced warm-then-cut bounds the *target*, not the scenario — every `components/*` target roots in a 64-element compiler bootstrap, but `bootstrap/base-sdk/*` is rooted at a 2-element pre-built binary seed, so a bounded subtree builds from nothing. Related and measured: run-to-run noise on the real build spans **5.8%** across three captures of the *same* commit (3614.2s / 3434.4s / 3405.8s) against the regression gate's fixed 1% default, so `UX-59`'s band over a baseline *set* is the correct path. Its three-run minimum became reachable in round 11, once `UX-81` stopped each capture force-pushing over the last: the band those three define is median 3434.4s ± 3×42.5s (scaled MAD), and it correctly calls a pair the fixed rule reports as `IMPROVED (-5.8%)` no significant change. See `docs/audits/round-9.md`.

## Core invariants still load-bearing (Plane 1)

The spec's invariants (full text: `docs/spec/specification.md`) remain the real correctness contract every Plane 1 change is checked against:

- **I4** `Σ attribution == H` (horizon) — checked by `bga/validation/invariants.py`, exercised end-to-end by every attribution-touching change (e.g. `UX-19`'s wait-gap re-saturation fix).
- **I8** run-identity capture/enforcement (`UX-07` fixed a real cross-sibling-project collision in it).
- **I9** CPU-accounting reconciliation within tolerance.
- **I11** determinism (same input → byte-identical output, N-run harness in `bga/validation/determinism.py`).
- **I12** cold-floor independence from certified/measured attribution.

## Real extensions beyond the original spec

Everything below is **additive**, not a spec contradiction — each is clearly marked non-spec in its own code/docstrings. This table is the one-scan replacement for reading the `docs/backlog/scenarios/*.md` files individually; each still has the full evidence trail if you need it.

| ID | One-line addition | Status |
|---|---|---|
| UX-01 | `bga compare` — baseline vs. candidate deltas + verdict | 🟢 Done |
| UX-02 | `efficiency_score` — composite, banded, confidence-gated | 🟢 Done |
| UX-03 | `bga compare --fail-on-regression` — CI gate, exit code 4 | 🟢 Done |
| UX-04 | Per-attribution-category "what to do about it" hints | 🟢 Done |
| UX-05 | Real 2-iteration optimization walkthrough tutorial | 🟢 Done |
| UX-06 | Fixed `--format raw` cross-task timestamp corruption | 🟢 Done |
| UX-07 | Fixed `run_identity` collision across sibling projects | 🟢 Done |
| UX-09 | Confirmed real: `--builders`×native `max-jobs` CPU contention | 🟢 Done |
| UX-10 | `total_duration_us` now prefers real wall-clock | 🟢 Done |
| UX-11 | **Plane 2** — intra-element native-build-system tracer | 🟢 Done |
| UX-12 | Capture real native `--max-jobs` + host CPU core count | 🟢 Done |
| UX-13 | `LB`/certified-headroom report caveat: dispatch capacity ≠ CPU cores | 🟢 Done |
| UX-14 | Sweep/replay fixed-duration caveat (tier 1) + real, calibration-driven contention-aware duration model (tier 2, `--calibration-dir`) | 🟢 Done |
| UX-15 | `--cpu-budget` overrides raw host core detection (cgroup-aware) | 🟢 Done |
| UX-16 | Fixed `max-jobs=0` sentinel silently treated as "missing" | 🟢 Done |
| UX-17 | `UtilizationAnalyzer` oversubscription dead code delegated to `UX-12` | 🟢 Done |
| UX-18 | Standalone `bst_run_context.py` gained `UX-12`/`UX-15` fields | 🟢 Done |
| UX-19 | Wait-gap re-saturation + retry-gap contention decomposition | 🟢 Done |
| UX-20 | `sensitivity.top_opportunities` in text report + batch/map-reduce simulation | 🟢 Done |
| UX-21 | Memory/swap oversubscription guard (independent of CPU) | 🟢 Done |
| UX-22 | Per-element `max-jobs` capture + serialization-point risk detection (**capture route and premise both corrected by `UX-31`** - `%{vars}`, not `%{public}`; pinned-below, not raised-above) | 🟢 Done |
| UX-23 | Element-tag Plane 2 traces + detect redundant cross-element operations (real evidence: `examples/05`'s CMake ABI probe reran 6x independently; real run found 37 redundant-operation findings) | 🟢 Done |
| UX-24 | Chrome Trace export for Plane 2 + combined two-plane `perfetto.dev` view, real dual-plane single-invocation capture | 🟢 Done |
| UX-25 | Coverage hard-gate violations gain real diagnostic detail (not just a bare ratio) | 🟢 Done |
| UX-26 | Batch/map-reduce report stops surfacing zero-savings groups | 🟢 Done |
| UX-27 | `floors.occupancy_ratio` - a graph-shape-aware efficiency signal beside `efficiency_score`, which structurally cannot be one (real pair: +35.2pp where every other metric was flat or backwards) | 🟢 Done |
| UX-28 | Oversubscription bar re-based onto the real governing core count (was BuildStream's own defaults, whose ratio-to-cores collapsed as the host grew), plus a new `dispatch_oversubscription` check on `builders` alone | 🟢 Done |
| UX-29 | `native_max_jobs` recovered from the wrapped log's own recorded invocation, with a `native_max_jobs_source` provenance field - the whole capacity-guard chain was inert on runs made by the documented pipeline | 🟢 Done |
| UX-30 | Sweep knee point is the last capacity that bought a real gain, computed over the whole curve | 🟢 Done |
| UX-31 | `%{vars}` capture of the *resolved* per-element `max-jobs` + `notparallel` (correcting `UX-22`'s route and premise); detector re-pointed at parallelism-pinned elements | 🟢 Done |
| UX-32 | Plane 2 per-element achieved parallelism, with work-vs-orchestration classification and two real findings (`pinned_to_one_job`, `underachieved_requested_jobs`) | 🟢 Done |
| UX-33 | Critical path always printed (per-element duration/share when long); choke points named | 🟢 Done |
| UX-34 | Structural kinds filtered out of the what-to-fix-first ranking, named in `omitted_structural_opportunities` | 🟢 Done |
| UX-35 | `RESOURCE WAIT`'s hint conditioned on a real `capacity_verdict` (consumed from `UX-28`'s check, never re-derived), with a distinct branch for "the checks could not run" | 🟢 Done |
| UX-36 | Dispatch-occupancy block titled for what it measures; capacity shown with provenance; buckets labelled as occupancy | 🟢 Done |
| UX-37 | Redundant-operation findings scored and ranked in recoverable wall-clock, filtered, elided readably, element build drivers excluded | 🟢 Done |
| UX-38 | Tracer `report` detects and re-renders a saved JSON report; wrong input is an error, not a zero-process result | 🟢 Done |
| UX-39 | Independent CI efficiency gate (`--fail-on-efficiency-regression`, `--min-efficiency`, exit code 5) on `occupancy_ratio`, with a default derived from measured run-to-run noise | 🟢 Done |
| UX-40 | Measured pipeline overhead no longer penalizes confidence (real capture 0.694 -> 0.869, CI gate live), plus `--fail-on-low-confidence` | 🟢 Done |
| UX-41 | Parallelism levels decomposed by *longest* path from a root, not shortest | 🟢 Done |
| UX-42 | Resource saturation computed once, not re-derived per wait gap (1200-element analyze: 68s → ~4s) | 🟢 Done |
| UX-43 | "Choke point" re-defined against the real graph, not `fan-in >= 2 and fan-out >= 2` | 🟢 Done |
| UX-44 | Real slack replaces the `duration × 0.5` placeholder; the improvement ranking was inverted | 🟢 Done |
| UX-45 | **Real per-process CPU time** in Plane 2 (`getrusage`), with coverage always stated | 🟢 Done |
| UX-46 | Declared-vs-used build dependencies, from `--trace-opens` matched against artifact contents | 🟢 Done |
| UX-47 | Narrow subcommands run only the stages they render (`bga graph` ~1.2s vs `analyze` ~3.7s at 1200 elements) | 🟢 Done |
| UX-48 | Idle capacity split into real buckets instead of all booking to `IDLE_NO_TASKS` | 🟢 Done |
| UX-49 | `parallelism_efficiency` no longer scores a perfectly serial build 1.000 | 🟢 Done |
| UX-50 | Structural analyzer keeps every task per element (an element whose FETCH sorted after its BUILD read as zero-duration) | 🟢 Done |
| UX-51 | **`bga correlate`** — the two-plane join, on element UID | 🟢 Done |
| UX-52 | Structural plane gates on `build` edges only; `runtime` edges no longer inflate its critical path | 🟢 Done |
| UX-53 | One per-element duration definition across every path computation (two coexisted, 22% apart) | 🟢 Done |
| UX-54 | A build in which elements **failed** says so before any efficiency figure | 🟢 Done |
| UX-55 | Cached elements recognised as cached, not as coverage gaps — `run_mode` published, incremental scoping stated | 🟢 Done |
| UX-56 | Plane 2 element attribution correlated against Plane 1 BUILD spans, not a path convention (0.6% → 14.9% on a real project) | 🟢 Done |
| UX-57 | Hook's open-path buffer flushes instead of dropping (70% of a real build's opens were lost) | 🟢 Done |
| UX-58 | Plane 2 shim records the bwrap argv and invocation it rewrites | 🟢 Done |
| UX-59 | Regression gate can compare against a baseline *set* — median ± k·MAD band, minimum three runs | 🟢 Done |
| UX-60 | `I3` implemented; the FETCH-in-efficiency question **decided** and documented rather than deferred again - but not yet **applied**, because the answer cannot be one number per element and moves a certified floor in both directions | 🟡 Partial |
| UX-61 | `max_concurrency` keyed on `(invocation, pid)` — it reported 5,268 concurrent processes on a 4-core runner | 🟢 Done |
| UX-62 | Per-span terminal status carried through `trace/v9`; failed task time reported as waste, not silently reclassified | 🟢 Done |
| UX-63 | **Measured per-element peak RSS** (`ru_maxrss`), replacing operator-declared memory estimates | 🟢 Done |
| UX-64 | Sandbox correlation matches on the interval's **end** edge (measured: 8 of 9 resolved vs 2 of 9 for whole-interval containment) — real attribution 14.9% → **86.1%** | 🟢 Done |
| UX-65 | The headline leads with **where the time is**, not with the largest sub-1% wait category | 🟢 Done |
| UX-66 | Attribution guard judges *validity*, not completeness — an 86.1% join renders with its coverage stated; a name the declared graph never contained is excluded and listed; a cancelled capture can no longer publish over a good one | 🟢 Done |
| UX-67 | **One entry point**: `bga wrap/extract/capture/…` dispatch to the programs in `tools/`, which stay independently runnable | 🟢 Done |
| UX-68 | A `stack` stages one marker file, so "nobody opened it" is not evidence — 90% false-positive rate removed from declared-vs-used | 🟢 Done |
| UX-69 | Plane 2 ranks binaries by **measured CPU**, not invocation count, and names single-process serialization points | 🟢 Done |
| UX-70 | **Realizable saving** — the longest path recomputed with each candidate zeroed — replaces share-of-path as the what-to-fix ranking | 🟢 Done |
| UX-71 | The join ranks and gates on that same realizable saving; a saturated metric is declared rather than broken by element name | 🟢 Done |
| UX-72 | The join reads all of Plane 2 — CPU concentration, serialization points, peak memory, redundancy — ranked by evidence strength | 🟢 Done |
| UX-73 | Redundancy detection excludes the unresolved attribution bucket and each element's own command block (claimed recoverable time 4129s → 91s on a real capture) | 🟢 Done |
| UX-74 | **Optimization horizon**, joint saving of the recommended set, and latent heavies — the next several findings from one capture | 🟢 Done |
| UX-75 | **`bga/findings.py`** — every conclusion the report draws, as data with stable ids and severities, rendered by text and published by JSON | 🟢 Done |
| UX-76 | One headline table instead of three rankings of the same elements | 🟢 Done |

(`UX-08` was never filed — not a missing/lost file.)

## Navigating the rest of the docs

- **`docs/spec/specification.md`** — original design intent, full formal Part-by-Part text (invariants, data contracts, terminology). Still authoritative for anything not listed as an extension above.
- **`docs/backlog/scenarios/README.md`** + `UX-*.md` — active backlog, full real-evidence trail for every extension above (why it was filed, what was tried, real command output).
- **`docs/backlog/tasks/`** + `docs/backlog/progress-tracker.md` — **closed** historical spec-compliance backlog (P0-P4). Read only for archaeology.
- **`docs/spec/ingestion-pipeline.md`** — real data flow from a `bst` invocation to `bga`-ingestible input.
- **`docs/guides/real-project.md`** — the end-to-end user-facing walkthrough on a real project: capture → read → go inside → join → act → gate, with real output at every step and an explicit list of what the tool refuses to say.
- **`docs/guides/optimization-walkthrough.md`** — a full worked example using the tool for real.
- **`docs/guides/optimization-walkthrough-06.md`** — the harder companion: a real macro-then-micro cycle on `examples/06-macro-micro-optimization`, written up as the case where the tool does *not* guide you, with every command and output pasted.
- **`docs/design/directions.md`** — where the tool should go next, argued separately for its two real usage scenarios (local optimization helper, and CI analytics/gate). Reading order: `architecture.md` (what it is) → `optimization-walkthrough-06.md` (what that felt like) → `design-directions.md` (what to do about it).
- **`docs/contributing/fixing-guide.md`** — mandatory session-start discipline (verification rules) for either backlog.
- **`docs/guides/cli.md`** — CLI reference/usage examples.

## Verification Log

Updated 2026-08-18 (after `UX-76`), re-grounded in `bga/cli.py`'s real subparser definitions, the current `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s backlog table re-read in full: the extensions table gained `UX-41`–`UX-76`, the Plane 2 and join sections gained what rounds 7–10 measured, and the package listing gained `findings.py`/`correlate.py`/`tools_dispatch.py`. Every figure quoted is from the capture published as `5eda28a` or from the task file that measured it.

Originally written 2026-08-16, grounded directly in `bga/cli.py`'s real subparser definitions, `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s own current backlog table (re-read in full, not from memory) - not written from the original spec or from assumption. No code changed; this is a docs-only addition.
