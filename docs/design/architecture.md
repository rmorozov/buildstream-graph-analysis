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
| `bga blast TARGET [RUN]` | What rebuilds if one thing changes, from whichever end the reader has it — a git url (every element sourcing that repository: the monorepo case, where one ref decides them all), a path (the elements whose `local` sources stage it), or an element name (its downstream closure). The answer says which reading it used, splits the closure into kinds that build and kinds that assemble, and prices it against the named run. A question, not a gate — always exits 0. **Not spec-mandated**, `UX-172`/`UX-173`/`UX-182` | — |
| `bga whatif [RUN] --element UID …` | What the build drops to if those elements were fixed *together*: one longest-path recompute with each of them zeroed, never a sum of their individual savings — which is wrong the moment two of them share a chain. "Fixed" means instant over this run's measured durations, so the figure is an upper bound and not a forecast. **Not spec-mandated**, `UX-230` | — |
| `bga compare BASELINE CANDIDATE` | Run-to-run deltas + improved/regressed verdict, and **two independent CI gates** — duration (`--fail-on-regression`, exit 4) and efficiency (`--fail-on-efficiency-regression`/`--min-efficiency`, exit 5); `--baseline-run`/`--band-k` compare against a baseline *set* instead of a fixed threshold. **Not spec-mandated**, `UX-01`/`UX-03`/`UX-39`/`UX-59` | — |
| `bga cache-trend RUN...` | Is the cache getting worse? A chronological *series*, not a pair — hit ratio, transfer seconds, churn per step, and a finding when the newest run leaves the band its trailing window describes. **Not spec-mandated**, `UX-103` | — |
| `bga cache-logs [PROJECT_DIR\|LOG_ROOT]` | **Plane 3** — BuildStream's own persisted element logs: per-element phase breakdown, sandbox tax, configure tax, developer tax. Needs no capture, and takes the project directory a user has rather than the log root they would have to derive (`UX-127`). **Not spec-mandated**, `UX-91`/`UX-99`/`UX-101`/`UX-102` | — |
| `bga capture run\|report\|census PROJECT` | **Plane 2** — trace processes inside element sandboxes (`--trace-opens`, `--trace-spine`), re-render a saved report, or run the static-binary census with no build at all. **Not spec-mandated**, `UX-11`/`UX-105`/`UX-106` | — |
| `bga snapshot -- bst build TARGET` | The local loop as one command: `capture run --run-dir` + `analyze` + `compare` against the previous snapshot, into a project-local store (`.bga/runs/`), with `@last`/`@prev`/`@<stamp-prefix>` resolving for every argument that names a run directory. Composes those commands rather than reimplementing them, so it changes no number and keeps every refusal. **Not spec-mandated**, `UX-126` | — |
| `bga doctor [PROJECT]` | Can this machine capture at all: `bst`, a real `bwrap` sandbox, a compiler, Plane 3's log tree, whether the project loads and what it stages — each failure with its own remedy. Read-only; exits non-zero only on a real failure. **Not spec-mandated**, `UX-125` | — |
| `bga baseline --glob REFS -n N` | Assemble a baseline *set* from published capture refs and band-compare against it in one command, refusing a set whose captures are not comparable. **Not spec-mandated**, `UX-96` | — |
| `bga wrap` / `extract` / `rebuild-set` / … | Thin aliases dispatching to the programs in `tools/`, which stay independently runnable as `python3 -m tools.<module>` — the workflow reads as one tool without merging the code. **Not spec-mandated**, `UX-67` (`bga/tools_dispatch.py`) | — |

Every conclusion the text report draws is also published by `--format json` as a `findings` array, each entry with a stable `id`, a `severity` and the numbers behind it (`UX-75`). Both renderers consume the same list, so they cannot disagree, and a CI consumer keys on `id` rather than re-deriving a threshold out of the renderer.

**`bga analyze --explain`** is how the provenance chain below is reached from the command line: under each claim it prints the evidence fields it was drawn from, the rule that fired, and the trace query that deepens it (`UX-229`). The mechanism is published in `analyze/v2` either way; the flag is what makes it visible to a reader who has a terminal and not a payload.

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

`bga cache-logs PROJECT_DIR` reads them. It is the only
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
  **0 processes and 24**. It attaches with `PTRACE_SEIZE` behind a pipe
  handshake — the child blocks until the parent has seized it — rather
  than inferring the attach stop from the first `SIGSTOP` it happens to
  see (`UX-130`); every restart site degrades by name instead of failing
  silently (`UX-128`); and the final drain is bounded rather than
  unbounded, which took a build with a backgrounded daemon in it from
  **30.01s to 0.01s** of teardown (`UX-133`).
- **The two record streams are one process list** (`UX-107`). A
  dynamically-linked process is now recorded twice, and consumed naively
  that double-counts every one: on `examples/06`, 1644 records read as
  1644 processes and **112.61 CPU seconds for a build that used 58.47**.
  They are joined on `(invocation, pid)` and a START inside a tolerance,
  every entry carries `spine+hook` / `spine-only` / `hook-only`, and
  coverage stops being a footnote and becomes a count. Verified at scale:
  **127,632 processes on freedesktop-sdk, all one class**.
- **A slice says what `bga` knows about it** (`UX-308`). A slice used
  to carry its name alone, and for Plane 2 that name is the command
  truncated to 120 characters - so the argv tail that tells two
  compiler invocations apart was not in the trace at all. Perfetto's
  vocabulary for this is **debug annotations**, and the timeline now
  writes them: per Plane 2 slice `cmd` (whole), `src`, `cpu_us`,
  `max_rss_kb`, `exit_status`, `exec_chain`; per Plane 1 task
  `element`, `element_kind`, `task_type`, `outcome`. A process that did
  not exit `0` also gets the `failed` **category**, which is what makes
  a class of slice filterable in the UI and selectable in SQL - and
  which is the constant `UX-298` pinned as "reserved rather than used".
  The keys are a contract (`PLANE1_ANNOTATIONS` / `PLANE2_ANNOTATIONS`
  in `tools/bga_timeline.py`, rendered by `UX-312`'s trace dictionary),
  because renaming one silently breaks a saved query; the guard holds
  the emitted set and the documented set equal in both directions. An
  absent field is an absent key rather than a zero: the hook cannot
  observe an exit status, and `0` there would state that the process
  succeeded. Measured on `examples/06`, 825 slices: 100,922 to 330,188 B
  uncompressed and 27,013 to 51,102 B gzipped - the whole command line
  is nearly all of it, and on that capture 412 of 813 records run past
  the 120-character name.
- **Extraction is one pass over the log, holding no events**
  (`UX-297`). Parsing and pairing were two phases with the whole event
  list between them, because `pair_events` sorted globally before
  pairing. Pairing needs a weaker property than that: one key's own
  events in order, a key being one process seen through one mechanism,
  whose START and END are written by one writer. `examples/06` carries
  **2 global inversions and 0 per-key inversions**, which is the
  measurement that decides it. `stream_records` yields a record when
  its END arrives and holds only the processes currently open;
  `pair_events` is that generator with its input and output sorted, so
  the list every existing caller wants is still a list and still says
  the same thing. On a 200,000-process trace: **288.3 MB peak to 259.5
  MB, 8.2 s to 7.1 s, identical report digest**. The remaining floor is
  the record list itself - `O(processes)`, not `O(elements)`, and named
  as such rather than implied (`UX-313`).
- **Opens-dependent findings state their scope.** Declared-vs-used
  (`UX-46`) now computes over the hook-covered processes and says what
  share that is — `examples/01`'s eight static elements are reported
  `UNCOVERED - 0 of 3 process(es) … were reachable by the LD_PRELOAD
  hook` instead of being skipped in a silence that reads as "no unused
  dependencies".

The spine is **opt-in**, and that decision was a measurement (`UX-108`):
the rule was stated before the numbers — under 2% wall it defaults on,
over it stays a flag — and **+2.7%** on `examples/06` against **+13.5%**
on `examples/08-process-storm` chose. Those two percentages are kept as
the figures that decided it, but they are not the claim any more.

`UX-112` re-measured the same question as a full {spine} × {opens}
factorial and found the ratio unstable and the *unit* wrong: it is a
fact about the fixture's baseline, not about the tool. `UX-129` then
found the replacement headline overshot too. What five independent
measurements support is **0.3 to 1.1 ms per process** — below the
run-to-run spread on `examples/06`, clearly visible on `examples/08`.
The spread is machine state rather than uncertainty within a run: the
tightest measurement, five interleaved `off`/`on` pairs, gives +0.79s on
2003 processes (0.39 ms), with the raw figures in
[`docs/audits/data/spine-cost-storm.md`](../audits/data/spine-cost-storm.md).
The predicted spine × opens interaction is not there — on the
process-dense fixture the spine is *cheaper* alongside opens, because
opens raises the baseline.

`UX-113`'s `--trace-spine=auto` follows directly: pay that cost only
where the census says the hook is blind, which is also why the exact
size of it matters less than it looks. It is what `bga snapshot` uses by
default.

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

**Both CI scenarios are now captured.** Rounds 6-10 were all incremental — 25 elements built, 65 skipped — which meant the critical path every round measured was the chain through the rebuilt elements rather than the project's real one. Round 11 took the first caches-off capture (`UX-86`): `bootstrap/build/gcc-stage1.bst`'s whole 18-element closure built from source with remotes ignored, 0 cached, 34.2 minutes, confidence 1.00. The constraint that produced warm-then-cut bounds the *target*, not the scenario — every `components/*` target roots in a 64-element compiler bootstrap, but `bootstrap/base-sdk/*` is rooted at a 2-element pre-built binary seed, so a bounded subtree builds from nothing. Related and measured: run-to-run noise on the real build spans **33%** across five captures of the *same* commit (3614.2 / 3434.4 / 3405.8 / 3261.2 / 2712.4s) against the regression gate's fixed 1% default, so `UX-59`'s band over a baseline *set* is the correct path. Its three-run minimum became reachable in round 11, once `UX-81` stopped each capture force-pushing over the last. The band those five define is median 3405.8s ± 3×214.3s (scaled MAD): it correctly calls the pairs the fixed rule reports as `IMPROVED (-5.8%)` and `(-9.8%)` no significant change, and — re-checked at n=5 on 2026-08-20 — the widest same-commit pair falls outside it, because the *fastest* run (2712.4s) sits below the lower edge of the band it helped build. That pair used to read `IMPROVED (-25.0%)`; since `UX-170` it answers `within the baseline set's own observed range`, because a duration the baseline runs themselves reached is not evidence of a change. The band is unchanged — widening it to cover the observed range was measured and rejected (it lets one contaminated baseline run swallow a real regression), so what `UX-170` added is a withheld verdict, not a wider band. See `docs/audits/round-9.md`.

## Core invariants still load-bearing (Plane 1)

The spec's invariants (full text: `docs/spec/specification.md`) remain the real correctness contract every Plane 1 change is checked against:

- **I4** `Σ attribution == H` (horizon) — checked by `bga/validation/invariants.py`, exercised end-to-end by every attribution-touching change (e.g. `UX-19`'s wait-gap re-saturation fix).
- **I8** run-identity capture/enforcement (`UX-07` fixed a real cross-sibling-project collision in it).
- **I9** CPU-accounting reconciliation within tolerance.
- **I11** determinism (same input → byte-identical output, N-run harness in `bga/validation/determinism.py`).
- **I12** cold-floor independence from certified/measured attribution.

## What a projection is, and why it is a bound (`UX-230`, `UX-74`)

`bga whatif` and the page's what-if panel answer one question — *what
would the build drop to if these were fixed together* — and the answer
is a **bound**, not a forecast. Two things make it one, and both are
stated in every `whatif/v1` answer (`bga/whatif.py`'s `CONVENTION`) and
in [`../guides/cli.md`](../guides/cli.md); this is where the reasoning
behind them lives.

**"Fixed" means instant.** The projection zeroes each chosen element's
measured duration and recomputes the longest path. A real fix that
makes an element *faster* rather than instant lands under the figure; a
fix that changes the graph — splitting an element, moving a dependency,
caching a source — is not modelled at all. So the number is a ceiling
on what the selection can be worth over this run's durations. A
re-capture is still the ground truth.

**It is one recompute, never a sum.** Whether two savings add is a
property of *this* graph, and it is the opposite of the intuition:

```text
freedesktop-sdk capture, measured by UX-74:
  same chain      cmake-stage1 + openssl + doxygen
                  individually 1569.8s + 522.5s + 513.5s = 2605.8s
                  jointly                                  2605.8s   (adds exactly)
  different chains  cmake-stage1 + git-minimal
                  individually 1569.8s + 547.7s          = 2117.5s
                  jointly                                  1569.8s   (takes the maximum)
```

Being in **series** is what makes savings compose — shortening two
links of one chain shortens the chain by both. Being **parallel** is
what makes them not — the other chain was never binding.

And summing is not merely optimistic: it is wrong in **both**
directions. On the committed `examples/06` run, `codegen.bst` is worth
**nothing** alone and the pair is worth more than either:

```text
$ bga whatif examples/06-…/run --element core.bst --element codegen.bst
  Makespan 43.200s -> 24.150s (saves 19.050s)
  Their individual savings add up to 12.050s, which is not what they are
  worth together (19.050s) - what one fix is worth depends on the others.
```

`codegen.bst` sits on the chain that becomes binding the moment
`core.bst` is fixed, so an element a reader would strike off the list
today is worth seven seconds tomorrow. That is the same effect the
optimization horizon (`UX-74`) projects forward, seen from one
selection: what a fix is worth is a property of the set it is in, and
no per-element table can carry it.

`compute_joint_saving` (`bga/graph/edg.py`) is the one recompute, and
`whatif/v1` publishes `sum_of_individual_us` **beside**
`joint_saving_us` rather than instead of it, so the difference is
visible in the payload rather than reproduced by the consumer.

## Real extensions beyond the original spec

Everything below is **additive**, not a spec contradiction — each is clearly marked non-spec in its own code/docstrings.

The table covers `UX-01`..`UX-76`: the additions that shaped the architecture this document describes. Everything filed since — the capture chain's diagnosability, the local snapshot store, the interrupt contract, the spine — is indexed with its status in [`docs/backlog/scenarios/README.md`](../backlog/scenarios/README.md), which is the live list; each item still has the full evidence trail in its own file.

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

## The viewer axis (rounds 21-26)

The three planes above are how `bga` *measures*. Rounds 21 onward built
how it is *read*, and the shape is deliberately small.

- **`bga view`** serves the run on `127.0.0.1` at a kernel-chosen port
  and opens a browser at it. The server is a `ThreadingHTTPServer` with
  a fixed document table: each url is a payload computed by the same
  functions the CLI calls, so nothing is analysed differently. Two
  endpoints take a parameter - `blast.json?target=` and
  `whatif.json?elements=` - and both call the function their subcommand
  calls.
- **Startup computes nothing large** (`UX-296`, Direction 15's first
  rule: *capture computes, view serves*). Nothing on the path to the
  socket may do O(events) work, and a large artifact is opened only to
  stream its bytes. So the report is the analysis `bga snapshot`
  already ran and published beside the run (`analyze.json`); the store
  aggregate reads the capacity scalars from the store row, written at
  capture time (`plane2-resource.json`), rather than re-parsing every
  snapshot's Plane 2 report for two floats; the noise band reads each
  baseline's `run-context.json` instead of re-analysing it; and the
  timeline is *offered* from a file test and rendered at the first
  request for its bytes, into a file the handler streams in fixed
  chunks - and that file is **Perfetto's own format** (`UX-298`):
  protobuf TrackEvent, gzipped by the writer as the packets are
  emitted, so the render is the served file and nothing passes over it
  twice. A `Trace` is `repeated TracePacket`, which is why it can be
  written that way at all; the legacy Chrome JSON stays behind
  `bga timeline --format chrome` for `chrome://tracing`. There is no
  protobuf dependency - the wire format is varints and
  length-delimited fields, and every field number is pinned to
  upstream's own `.proto` by a committed fixture, because a wrong
  number is silent. Measured on a generated 247 MB report of a million process
  records: 17.04 s and 1232.9 MB to reach the socket, against 0.04 s
  and 39.5 MB after - and viewing a 2 MB run *beside* it cost 1233.5 MB
  before and 39.8 MB after, because the aggregate used to walk into its
  neighbour's monolith. A run whose capture published no analysis is
  still analysed here from Plane 1; its Plane 2 report is refused above
  a size bound with the sentence naming the command that publishes one.
- **The page obeys a policy the server sets.** Every response carries
  `default-src 'self'; frame-ancestors 'none'` and `nosniff`; the only
  cross-origin grant is `Access-Control-Allow-Origin` for Perfetto's
  own origin, on the trace blob alone (`UX-198`) - together with the
  **pre-flight** that grant needs, scoped identically (`UX-265`): the
  blob only, Perfetto only, `GET`/`HEAD` only, plus
  `Access-Control-Allow-Private-Network`, because a public origin
  reading `127.0.0.1` is a transition Chrome asks about by name. Two
  consequences bind
  the page: it may not load anything off-host, and it may not write a
  **style attribute** - a style attribute is inline style and the
  policy refuses it, which silently killed four of the viewer's width
  channels until `UX-263`. Drawings set style through CSSOM
  (`el.style.width`, `el.style.setProperty`), which the policy does not
  cover. Relaxing it with `'unsafe-inline'` was declined: this page
  renders element names and paths out of a build and gets attached to
  tickets.
- **The page is schema-driven.** `bga/viewer/` is hand-written ES
  modules with no build step and no framework. Sections, columns, units
  and hover text come from the *view-hints* the published schemas carry
  (`bga:quantity`, `bga:question`, `bga:columns`, `bga:rail`,
  `bga:markers`, `bga:presets`, ...), so a field that gains a
  description in `bga/schemas.py` gains a tooltip in the page with no
  page edit.
- **A view is a named filter over one table, declared not coded**
  (`bga:presets`, `UX-289`, round 38). One element table serving every
  question carried 13 columns on the 1,202-element run, and the
  questions readers actually arrive with were answered by other tables
  the payload published separately. A preset names one question and the
  four to six columns that answer it — `{name, question, from|where,
  columns, sort, bound}` — and every population is a **filter over a
  published field**: `from` reads a selection the payload publishes once
  and takes its order from it, `where` tests a column the element
  records carry. Nothing computes a membership the payload does not
  have, which is why `UX-288` came first. The preset travels in
  `UX-211`'s fragment and is named in the rail, so a view is a link.
  `PRESET_COLUMNS_MAX` bounds a view at eight columns and the schema
  validator refuses a wider one: a table that needs more than that to
  answer one question is not a view of the data, it is the data.
- **The document has chapters** (`UX-286`, round 39). Forty-eight
  sections averaging 0.24 screens, grouped by nothing, made the fragment
  the reader's only unit of navigation. `bga/viewer/chapters.js` groups
  them into seven chapters, each named for a question the reader has -
  and the sections that answer it are the ones whose published
  `bga:question` is a spelling of that question. The table is in the
  viewer rather than the schema because nine of the forty-eight sections
  are built by the page and published by no contract; `bga:rail` is the
  fallback, so a payload key added later lands in the chapter its rail
  already names. The rail lists the chapters and nests the sections
  under them, which is the same grouping the document has. Grouping cost
  no height: 18.51 screens to 18.10 on the 1,202-element run, because
  the chapter boundary carries separation the sections no longer need
  between them. Padding every section to one screen was refused on the
  measurement that it adds 31.3 screens of whitespace
  ([Direction 13](directions.md#direction-13-the-report-has-48-fragments-and-no-chapters-argued-2026-08-24-round-38)).
- **A value is drawn by width, not depth** (`UX-267`, round
  36). The hints above decide what a field is *called* and where it
  sits; this decides what happens to its **value**, and it applies to
  every object- or array-valued field in every published schema without
  a page edit. `renderStructured` picks one of three renderings by how
  wide the value is: narrow objects and short arrays are **inlined**
  into their cell, wider ones become a **bounded table** that scrolls
  inside itself, and only what is wider still **folds** — labelled with
  what it holds, never with the word "object". Long *text* is a
  separate case: a long **value** truncates with the whole thing kept
  behind a fold, and a long **explanation** does not truncate, because
  the sentence is the point.

  The thresholds are exported names in `bga/viewer/app.js`
  (`OBJECT_INLINE_FIELDS`, `ARRAY_INLINE_ITEMS`, `CELL_TEXT_CAP`) rather
  than numbers repeated here, so a later round moves them in one place.
  Depth is deliberately not the criterion, and that is the whole
  choice: a two-level object of four fields reads fine inline, and a
  flat one of forty does not. The
  argument, and what the page looked like before the rule, is
  [Direction 12](directions.md#direction-12-the-report-is-read-not-decoded-argued-2026-08-24-round-35).

- **The mapping is law** (`UX-302`, round 41). The rule above is now a
  table — round 41's style guide
  ([`styleguide.md` §1](styleguide.md)) maps published shape (+ hint)
  to the one control that may render it — and
  `bga/viewer/shapes.js` is that table as code. `classify()` returns a
  control's name; every render path asks it rather than testing shapes
  itself, so "which control draws this" has one answer and one place to
  read it. **Raw JSON on the page is a defect unless it is
  deliberate**, and there are exactly two deliberate sites: `UX-277`'s
  labelled fold, and the per-section **"view as JSON" toggle**
  (`bga/viewer/rawjson.js`) that a reader opens to paste a section into
  an issue — which works in the export, because that is who needs it. A
  shape the table does not cover renders as the fold *and* warns on the
  console naming the payload path: the gap is a design task, not an
  improvisation. `tests/unit/test_the_mapping_is_law.py` boots the real
  pages and walks every text node for JSON-shaped content outside those
  two.

- **A shape draws as a shape** (`UX-303`, round 41). Two hints join the
  vocabulary — `bga:series` for an ordered numeric array and
  `bga:distribution` for a published percentile object — and each
  carries the reading its control needs: the unit of one step, and the
  key that holds the sample count. `bga/viewer/drawings.js` holds the
  sparkline and the density strip; it imports nothing and takes its
  formatter, so the quantity table stays in `app.js`. Under three
  points is a sentence and no drawing. A table past the row bound
  wears a strip built from its primary quantity column's own
  `data-raw` values, under [`styleguide.md` §2](styleguide.md)'s
  boundary: **a self-built strip prints no derived number** — its
  labels are actual rows and a count of rows, and the percentile ticks
  are geometry. That boundary is the no-arithmetic rule below, applied
  to a drawing.

- **Dark is the design surface, and a fill is not a text color**
  (`UX-304`, round 41). `bga/viewer/style.css` holds every color the
  product has: `:root` carries the dark tokens, `@media
  (prefers-color-scheme: light)` is the override — it also matches a
  reader who expressed no preference, so an unset browser is unchanged
  — and `@media print` renders light on white, because an export is
  attached and printed. Tokens come in two grades: **text-grade**
  (≥4.5:1 against its surface, for reading) and **mark-grade** (≥3:1
  and inside the surface's lightness band, for filling). The split
  exists because the dark set had never been validated and three of
  its four status colors were text-grade doing fill work.
  `tests/palette.py` is the validator — WCAG contrast, CIE L\*, ΔE2000,
  dichromat simulation, no dependency — and the guard pins the bands,
  refuses a hex literal outside the stylesheet, and holds every
  status-toned rule against a list naming its non-color channel
  ([`styleguide.md` §4-5](styleguide.md)).

- **`--export`** inlines every served document and every module into one
  self-contained HTML file. What cannot survive that - a live search
  box, anything needing a server - is *hidden with the command that
  answers it* rather than shipped as a control that always fails.
- **The no-arithmetic boundary** is the axis's one rule, and it is the
  reason the rest holds: **a viewer that derives a conclusion is a
  second analyzer.** Diagnoses, rankings, verdicts, savings, next steps
  and projections are all decided in the pipeline and read by the page.
  Where a question needs a number the payload does not carry, the page
  *asks the server* rather than computing it. Guards assert this
  directly, and the discipline is what lets the terminal, the CI comment
  and the page state one build's facts identically.

The corollary is the constraint Direction 7 wanted: anything the viewer
should show has to enter a published schema first, where the text
renderer, CI and every external consumer get it too.

## The published contracts

The tool's external surface, one line each. **`--schema` is the source
of truth** - it prints the JSON Schema from `bga/schemas.py`, which the
renderers are built against, so nothing here is a second copy to drift.

| schema | what it is | printed by |
|---|---|---|
| `analyze/v2` | one run's analysis: attribution, floors, signals, findings, the headline decision, next steps, and the provenance behind each claim. **v2** (`UX-288`) removed three fields that republished element membership already published beside them — `signals.critical_path`, `signals.leaf_analysis.leaves`, and `structural.deferrability`'s two uid lists; the leaf's `deferral_risk` is published in their place | `bga analyze --schema` |
| `compare/v1` | two runs, their signed deltas, the verdict and its noise band, the per-element culprits, and the candidate's diagnosis chain | `bga compare --schema` |
| `blast/v1` | what rebuilds if one repository, path or element changes | `bga blast --schema` |
| `correlate/v1` | the two planes joined on element uid, with the coverage of the join | `bga correlate --schema` |
| `store/v1` | what the run store holds: one row per snapshot, with the alias, the verdict and why a capture is not a measurement | `bga snapshot --list --format json` |
| `store-aggregate/v1` | that store as a distribution: min/median/p95/max/MAD per host class, and the refusal when a mix cannot be blended | `bga snapshot --aggregate --format json` |
| `whatif/v1` | what the build would drop to for a chosen set of fixes - one projection, never a sum | `bga whatif --format json` |
| `host/v1` | the machine a capture was taken on; written into every run context and read by the cross-host refusal | inside `run-context.json` |
| `sources/v1` | every element's source resources and how each is keyed - the on-disk shape `bga blast` reads | inside `sources.json` |
| `plane2/v2` | Plane 2's report: the per-element reductions a capture computed, and nothing else (`UX-297`) | at `plane2.json` beside a run |
| `plane2/v1` | the same reductions plus every per-process record - the shape a capture before `UX-297` wrote. Read, never written | as above, in an older store |

**Every artifact says what wrote it** (`UX-249`): a `producer` block —
tool, version, and the contract set the writing build had — rides in
every run directory and every published `analyze/v2` document, because
`bga` reads its own past output as input and until round 30 nothing in
those artifacts said which build produced them. The version there is
*provenance*; compatibility is decided per contract, which is why
`bga compare` refuses on **contract movement** and not on a version gap
(`UX-250`). Which contract states shipped together is
[`CHANGELOG.md`](../../CHANGELOG.md) (`UX-251`).

**The versioning rule**: a field rename or removal bumps the version; an
addition does not. `additionalProperties` is true everywhere, so a
consumer that pins a version keeps working while the tool grows.

The last four rows are written but not printable — on-disk shapes a run
directory carries rather than documents a subcommand emits. `--schema`
does not know them, and `bga.contracts.unprintable()` says so.
`plane2/v1` goes one further: it is read and never written, which
`bga.contracts.superseded()` names, because a store full of captures
taken before `UX-297` still has to analyze.

A guard (`tests/unit/test_the_documents_keep_up_with_the_contracts.py`)
asserts this table and the spec's Part 32.5 name every contract in
`bga.contracts.ids()`, and no contract that does not exist. That
inventory is derived from the package rather than kept as a list —
`UX-248` found `sources/v1` written to every run directory and present
in no registry, no guard and no document, because the previous version
unioned the registry with a single hard-coded id. A new payload without documentation
reddens it - which is the only mechanism this repository has found that
keeps two hand-maintained copies of one fact together.

## Navigating the rest of the docs

- **`docs/spec/specification.md`** — original design intent, full formal Part-by-Part text (invariants, data contracts, terminology). Still authoritative for anything not listed as an extension above.
- **`docs/backlog/scenarios/README.md`** + `UX-*.md` — active backlog, full real-evidence trail for every extension above (why it was filed, what was tried, real command output).
- **`docs/backlog/tasks/`** + `docs/backlog/progress-tracker.md` — **closed** historical spec-compliance backlog (P0-P4). Read only for archaeology.
- **`docs/spec/ingestion-pipeline.md`** — real data flow from a `bst` invocation to `bga`-ingestible input.
- **`docs/guides/real-project.md`** — the end-to-end user-facing walkthrough on a real project: capture → read → go inside → join → act → gate, with real output at every step and an explicit list of what the tool refuses to say.
- **`docs/guides/optimization-walkthrough.md`** — a full worked example using the tool for real.
- **`docs/audits/case-study-06-macro-micro.md`** — the harder companion: a real macro-then-micro cycle on `examples/06-macro-micro-optimization`, written up as the case where the tool does *not* guide you, with every command and output pasted.
- **`docs/design/directions.md`** — where the tool should go next, argued separately for its two real usage scenarios (local optimization helper, and CI analytics/gate). Reading order: `architecture.md` (what it is) → `optimization-walkthrough-06.md` (what that felt like) → `design-directions.md` (what to do about it).
- **`docs/contributing/fixing-guide.md`** — mandatory session-start discipline (verification rules) for either backlog.
- **`docs/guides/cli.md`** — CLI reference/usage examples.

## Verification Log

Updated 2026-08-26 (after `UX-308`), re-grounded in
`tools/native_trace/trackevent.py`'s annotation and category writers,
in `tools/bga_timeline.py`'s `PLANE1_ANNOTATIONS` /
`PLANE2_ANNOTATIONS`, and in
`tests/unit/test_the_slice_says_what_bga_knows.py`. The field numbers
were fetched again rather than remembered: `track_event.proto` and
`interned_data.proto` came back **byte-identical** to what `UX-298`
pinned, and `debug_annotation.proto` is recorded beside them with its
own sha256. The Plane 2 bullet now says what a slice carries, which
until this round was only its name.

`UX-298`'s non-vacuity clause - "the table above must cover what the
module pins" - caught all ten new constants the moment they were added,
before any of the work below.

Six mutations against the committed tree, all discriminating:

```text
M1  a contract key is emitted under a different name       2 red
M2  a key is documented and never written                  1 red
M3  the failed category is on every process                2 red
M4  an absent field is annotated as zero                   2 red
M5  the full command is truncated like the name            1 red
M6  the annotations move to the slice end                  1 red
```

**A finding the first draft made and the record refuted.** `spine.c`
writes `exit=%d` for a normal exit and `exit=signal:%d` for a killed
one, so `exit_status` is a *string with a vocabulary*, not a number.
The first failed-category rule read `status not in (None, 0)` - which
would have marked **every** process failed, because `"0"` is not `0`.
Success is exactly the string `"0"`, and the constant that says so has
a name and three assertions on it.

Updated 2026-08-26 (after `UX-297`), re-grounded in
`tools/bst_native_build_tracer.py`'s `stream_trace_events` /
`stream_records` as they now stand, in the three call sites in
`tools/bga_timeline.py`, and in
`tests/unit/test_the_pairing_pass_streams.py`. The Plane 2 bullet now
says extraction holds no events and names what it does hold, which is
the half this document had been leaving to a task file.

Six mutations against the committed tree, all discriminating:

```text
M1  the pass stops counting fork-only exits            1 guard red
M2  `pair_events` stops sorting its output             3 red
M3  `pair_events` stops consuming its input            1 red
M4  the still-open records are dropped                 passed - see below
M5  the analysis builds an event list again            1 red
M6  the timeline builds one again                      1 red
```

M4 is the one worth keeping. Every clause comparing the two entry
points is true *by construction* - they share one implementation, so a
change moves both sides and the comparison stays green; that is the
same hole `UX-297`'s own M2 fell into a round earlier. Four hand-worked
processes replace the argument with an answer - one that pairs, one
still open, a hook END with no START and a spine END with no START -
and M4 reddens now. It was already caught by two clauses elsewhere in
the suite, which is why it was worth finding rather than worth
shipping.

Updated 2026-08-25 (after `UX-306`), re-grounded in the three viewer
bullets round 41 added and in the guards that hold them:
`bga/viewer/shapes.js` against `docs/design/styleguide.md` §1 and
`tests/unit/test_the_mapping_is_law.py`; `bga/viewer/style.css`'s two
token grades against `tests/palette.py`'s measured bands; and
`bga/viewer/drawings.js` against §2's boundary on what a self-built
strip may print. The viewer axis now says what a value renders as,
what may be coloured and what a drawing owes its reader — three
questions this document could not answer before there was a contract
to answer them from.

Updated 2026-08-25 (after `UX-298`), re-grounded in
`tools/native_trace/trackevent.py`'s pinned field numbers against
`tests/fixtures/perfetto_field_numbers.json`, and in `bga timeline`'s
own `--format` help: the viewer axis now says which trace format the
handoff carries, which it could not before there was a choice.

Updated 2026-08-25 (after `UX-296`), re-grounded in `tools/bga_view.py`'s
`serve`/`payloads` as they now stand, `bga/store_aggregate.py`'s row
build, and the startup measurements in
`tests/unit/test_the_view_parses_nothing.py`: the viewer axis gained the
rule that startup computes nothing large, which is the first thing
Direction 15 asks for and the one the field capture broke.

Updated 2026-08-25 (after `UX-286`), re-grounded in `bga/viewer/`'s
module list, the published schema `bga analyze --schema` prints, and
`docs/backlog/scenarios/closed.md`'s round-38 and round-39 rows: the
viewer axis gained the chapters `UX-286` groups the document into, and
the contracts table's `analyze/v2` row is checked against the keys the
schema declares - which `UX-275` added one to. The date on this line is
guarded (`UX-247`): a commit that changes this document's prose without
re-grounding it reddens
`tests/unit/test_the_verification_log_is_true.py`.

Updated 2026-08-18 (after `UX-76`), re-grounded in `bga/cli.py`'s real subparser definitions, the current `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s backlog table re-read in full: the extensions table gained `UX-41`–`UX-76`, the Plane 2 and join sections gained what rounds 7–10 measured, and the package listing gained `findings.py`/`correlate.py`/`tools_dispatch.py`. Every figure quoted is from the capture published as `5eda28a` or from the task file that measured it.

Originally written 2026-08-16, grounded directly in `bga/cli.py`'s real subparser definitions, `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s own current backlog table (re-read in full, not from memory) - not written from the original spec or from assumption. No code changed; this is a docs-only addition.
