# `bga`: Current Architecture — Three Analysis Planes

**Start here to orient in this codebase.** `docs/spec/specification.md` (v9) is the original design document and stays authoritative for full-length invariant/data-contract text — it is *not* wrong, but it describes the tool as originally scoped, and does not know about anything built since. This doc describes what `bga` actually does **today**, as one coherent system, and points at the real file/doc for every claim so you don't have to reconstruct that history yourself from the commit log, the 632 `docs/backlog/scenarios/` files and the 75 `docs/backlog/tasks/` files this commit carries.

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
| `bga wrap PROJECT LOG -- bst build TARGET` | **Plane 1's capture.** Runs a real `bst` command and writes the wrapped-format log every later stage reads - the first command in the README's own quickstart, and what `bga snapshot` calls when it captures for you. **Not spec-mandated**, `UX-67` | — |
| `bga capture run\|report\|census PROJECT` | **Plane 2** — trace processes inside element sandboxes (`--trace-opens`, `--trace-spine`), re-render a saved report, or run the static-binary census with no build at all. **Not spec-mandated**, `UX-11`/`UX-105`/`UX-106` | — |
| `bga snapshot -- bst build TARGET` | The local loop as one command: `capture run --run-dir` + `analyze` + `compare` against the previous snapshot, into a project-local store (`.bga/runs/`), with `@last`/`@prev`/`@<stamp-prefix>` resolving for every argument that names a run directory. Composes those commands rather than reimplementing them, so it changes no number and keeps every refusal. **Not spec-mandated**, `UX-126` | — |
| `bga bundle --export STAMP \| --load FILE` | **The capture as one file.** Packs one snapshot's whole capture-layout set - the run directory *and* the Plane 2 report, raw trace, host samples, published analysis and build log beside it - into a single archive to `scp`, and loads one back into a project's store under its own stamp. The member list is derived from the layout contract, so `run/`-only tarring stops losing Plane 2; each member carries its contract version, so a bundle from a newer `bga` is refused rather than half-read. `--no-plane2` trades the large member for a small bundle and records the omission. **Not spec-mandated**, `UX-520` | — |
| `bga doctor [PROJECT]` | Can this machine capture at all: `bst`, a real `bwrap` sandbox, a compiler, Plane 3's log tree, whether the project loads and what it stages — each failure with its own remedy. Read-only; exits non-zero only on a real failure. **Not spec-mandated**, `UX-125` | — |
| `bga baseline --glob REFS -n N` | Assemble a baseline *set* from published capture refs and band-compare against it in one command, refusing a set whose captures are not comparable. **Not spec-mandated**, `UX-96` | — |
| `bga view RUN [--export FILE]` | **The report as a page.** Serves the run on `127.0.0.1` at a kernel-chosen port and opens a browser at it, or writes one self-contained file with `--export`. Renders the *schema*, not the report, from the same payloads the subcommands publish - so it can disagree with the CLI only by being stale. Where the reader stops depends on the question: see [what the viewer answers](../guides/what-the-viewer-answers.md). **Not spec-mandated**, `UX-193`/`UX-195` | — |
| `bga timeline RUN` | **Both planes on one clock.** Emits Perfetto's own TrackEvent protobuf by default (`--format chrome` for the legacy JSON), with Plane 1 element spans and Plane 2 process slices scoped by `slice.category` and joined on the element uid both carry. The trace `bga view`'s Perfetto button hands off, and the thing a reader drops to when the page's aggregates are not enough. **Not spec-mandated**, `UX-188`/`UX-298` | — |
| `bga extract` / `rebuild-set` / `log-to-chrome` / … | The remaining eleven thin aliases dispatching to the programs in `tools/`, which stay independently runnable as `python3 -m tools.<module>` — the workflow reads as one tool without merging the code. Format converters and internal utilities: a reader looking for what `bga` *answers* wants the rows above, not these. **Not spec-mandated**, `UX-67` (`bga/tools_dispatch.py`) | — |

Every conclusion the text report draws is also published by `--format json` as a `findings` array, each entry with a stable `id`, a `severity` and the numbers behind it (`UX-75`). Both renderers consume the same list, so they cannot disagree, and a CI consumer keys on `id` rather than re-deriving a threshold out of the renderer.

**`bga analyze --explain`** is how the provenance chain below is reached from the command line: under each claim it prints the evidence fields it was drawn from, the rule that fired, and the trace query that deepens it (`UX-229`). The mechanism is published in `analyze/v5` either way; the flag is what makes it visible to a reader who has a terminal and not a payload.

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

`tools/` is a separate, deliberately-not-`bga`-internal set of scripts that turn a real `bst` invocation into `bga`-ingestible input (needs a live `bst`+`bwrap` install; `bga` itself never does) — full data-flow diagram in `docs/spec/ingestion-pipeline.md`. `tools/bst_native_build_tracer.py` (+ `tools/native_trace/`) is Plane 2 — see below. Every command in the CLI table above that dispatches into `tools/` runs one of these files:

- `bga wrap` -> `tools/bst_run_wrapped.py` — Plane 1's capture
- `bga extract` -> `tools/bst_extract_run.py` — a log plus a project becomes a run directory
- `bga capture` -> `tools/bst_native_build_tracer.py` — Plane 2's tracer, over `tools/native_trace/bwrap_shim.py` (the shim ahead of the real `bwrap`), `tools/native_trace/hook.c` (the `LD_PRELOAD` hook), `tools/native_trace/spine.c` (the ptrace spine, for static binaries) and `tools/native_trace/trackevent.py` (Perfetto's own TrackEvent writer)
- `bga cache-logs` -> `tools/bst_cache_logs.py` — Plane 3's reader
- `bga snapshot` -> `tools/bga_snapshot.py` — the local loop as one command
- `bga timeline` -> `tools/bga_timeline.py` — both planes on one clock
- `bga view` -> `tools/bga_view.py` — the report as a page
- `bga doctor` -> `tools/bga_doctor.py` — can this machine capture at all
- `bga baseline` -> `tools/bst_baseline_set.py` — the baseline set and its band

### Where fixtures come from

Nothing in `tools/` above answers *"give me a build of this shape"* —
they all wrap a build somebody already has, or read one. Two things do,
and they split the question rather than competing for it. `UX-463`
settled the split by asking which axes each half can reach:

| | curated fixtures | generated projects |
|---|---|---|
| written by | `tests/fixtures/topologies.py` | `tools/bga_gen_project.py` |
| produces | an ingested triple: `graph.json`, `trace.json`, `run-context.json` | a BuildStream project `bst build` accepts |
| needs `bst` | no | to *build* what it writes, yes |
| owns | graph shape, where the wall-clock sits, run mode, source topology | outcome, sandbox profile, scale |

The line between them is not convenience. A curated triple is
deterministic to the microsecond, and that is the **only** way to build
a fixture whose two longest paths are within a few percent of each
other — a real build cannot be asked for a near-tie critical path, and
`blast_radius_disagrees_with_horizon` and `shared_base_wide`'s
`tie_ratio` both exist because of it. Going the other way, a synthesised
trace can only assert what its author already believed: a process storm
or inode-count staging is something the `LD_PRELOAD` hook and the ptrace
spine *observe*, so **that axis does not exist above `bst`** and no
amount of writing JSON reaches it. A real failed build is the same
argument in one instance — it is the only thing that shows the capture
path survives one (`UX-156`, `UX-148`).

`tools/gen_synthetic_scale_run.py` is the curated half at a scale
nobody hand-writes: a synthetic run directory, by default 1202 elements
over 14 real levels, scheduled onto 16 builders by a real
dependency-respecting greedy pass so the trace satisfies the same
ordering and capacity properties a real capture does. It exists because
the second audit round found four defects invisible at eleven elements
(`UX-41`–`UX-44`), and their acceptance tests all cite this fixture;
running it with the same `--seed` reproduces the directory byte for
byte. Like every curated fixture it exercises the **analysis** side
only — nothing about a synthesised run directory says whether the
capture tools survive a thousand-element build, which is the sentence
`bga_gen_project.py` exists to stop this document from having to
hedge.

Captures are never committed (`UX-189`): every `examples/*/.bga/` is
git-ignored, so a clone carries the fixtures above and no run of a real
build at all. That is why two censuses exist to say what a clone can
actually reach — `tools/dev_finding_coverage.py` for findings and
`tools/dev_trace_coverage.py` for trace carriers. Both are dev
instruments and are listed with the rest in the fixing guide's §6
context map rather than here; this section is about where a *shape*
comes from, and a reader who wants the instrument list is one link
away.

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
  **127,632 processes on freedesktop-sdk, all one class**. `UX-487`
  made the two streams carry the same *counters* as well as the same
  identities: the spine records `minflt`/`majflt` from the `/proc`
  read it already did, and `inblock`/`oublock` from the task's own
  `/proc/<pid>/task/<pid>/io` — the hook's key names and units, so a
  spine-only process reaches every reader a hook-recorded one does.
  On one workload traced by both at once the two agree exactly.
- **One counter, and two refusals** (`UX-310`). `UX-298` pinned
  `TYPE_COUNTER` as "reserved rather than used" under the rule that an
  event stream may carry only what a capture measured; this is its
  caller, and the same rule decides what is *not* drawn. There is no
  memory curve: `max_rss_kb` is a per-process **lifetime** peak, not a
  sample, so a curve from it would sum peaks that never coexisted -
  exactly what `compute_peak_memory` refuses - and a guard asserts no
  memory counter exists rather than leaving the absence to be read as
  an oversight. "Cores busy" and "open process count" are one question,
  answered by `compute_max_concurrency` over matched records only,
  because an open record's end is unknown and a curve that included it
  would be inventing one. So one series - *traced processes running* -
  whose peak **equals** the published `max_concurrency`, with the tie
  rule taken from the scalar rather than re-decided. The stride is a
  decision with a number: 1,000 windows, each contributing its maximum
  and its closing value, so the cost is independent of build size and
  the peak survives exactly - 1,626 raw endpoints become 538 samples on
  `examples/06` with the peak still 20. Cost: one packet a sample plus
  one for the track, 25.1 B uncompressed and 6.3 B compressed.
- **The trace knows whose build it was** (`UX-311`). A trace file
  leaves the machine that made it - attached, shared, opened weeks later
  beside five others - and carried no identity at all. One `bga: run`
  process track, ranked first, holds one annotated instant: the run
  stamp, project, targets, manifest hash, git commit, `bga` and `bst`
  versions, the host manifest, the builders, and the plane anchor and
  offset. Portable vocabulary on purpose - `trace_processor` selects it
  like any other slice. An unfinished run says so in the **track name**
  (`bga: run (interrupted)`), not only in an annotation, because an
  annotation is something a reader has to open a slice to see and the
  honesty `UX-156` enforces in the report belongs where the first scroll
  lands; all three ways of being unfinished are covered because it calls
  `bga`'s own one accessor rather than re-deriving the rule. Lane order
  is explicit: `sibling_order_rank` per track, and - the rule that had
  to be read rather than remembered - the root descriptor (`uuid = 0`)
  setting `process_ordering` to `PROCESS_ORDERING_EXPLICIT`, without
  which every rank is a hint no UI reads. Identity first, Plane 1
  second, element lanes after, **heaviest traced first** and labelled
  with their kind. That last is a recorded deviation: the item asks for
  the critical path, the timeline reads two logs and a graph rather than
  an analysis, and the trace states which rule it used in `lane_order`
  instead of letting a reader assume the other one.
- **The arrows say why something started now** (`UX-309`). An element
  ends, another begins, and whether that adjacency is *causation* is
  what `graph.json` knows and the trace never said. Perfetto's
  vocabulary is **flows**, drawn as arrows: the timeline emits one per
  dependency edge whose two endpoints both produced a task, and one per
  `ppid` link inside a sandbox - the exec chain, which makes a build
  system's process tree followable instead of inferred from lane
  adjacency. Nothing else: there is no captured relation between one
  element's process and another's, and a flow that invented one would be
  a lie the UI draws in bold. A flow is *one id on two slices* and
  upstream infers the direction from their timestamps, so an edge whose
  source does not begin strictly before its sink is **dropped and
  counted** rather than guessed at - on `examples/06` that is two edges,
  because `toolchain.bst` is instantaneous and both its dependents begin
  in the microsecond it does. The bound is no bound, and the measurement
  is the argument: a flow id rides the slice packet that already exists,
  so **packets are unchanged** at both scales measured (2,335 on
  `examples/06`, 62,804 on a 20,000-process synthetic) and a flow costs
  20.0 B uncompressed, 8.6 B gzipped. The ids are `fixed64`, a different
  wire type from every other number the emitter writes, and a varint in
  that field is a packet a reader drops without complaining - so the
  guard asserts the wire type, not only the value.
- **A slice says what `bga` knows about it** (`UX-308`). A slice used
  to carry its name alone. Perfetto's
  vocabulary for the rest is **debug annotations**, and the timeline now
  writes them: per Plane 2 slice `src`, `cpu_us`,
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
  was nearly all of it, and on that capture 412 of 813 records ran past
  the 120-character name.
- **And the name is the whole command** (`UX-333`, which reverses the
  half of `UX-308` above that trimmed it). The 120-character cut fell
  where a compiler argv is least distinguishing: the flags prefix is
  shared and the file is at the end, so **3,000 distinct compiles
  interned to one slice name** - the trim did not hide detail, it
  destroyed identity. The name is untrimmed and the `cmd` annotation
  that carried the tail is dropped with it, because the two together
  would pay for one string twice. Measured on those 3,000 processes at
  466 characters of argv: full name with `cmd` kept costs +75.1% raw,
  full name without it +0.6%. A saved query reading `debug.cmd` gets
  NULL now and reads `slice.name` instead - a declared break.
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

`floors.occupancy_share` (`UX-27`) is the second signal - `Σ task
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
"was the work this build does being done efficiently", on `occupancy_share`,
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
| UX-27 | `floors.occupancy_share` - a graph-shape-aware efficiency signal beside `efficiency_score`, which structurally cannot be one (real pair: +35.2pp where every other metric was flat or backwards) | 🟢 Done |
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
| UX-39 | Independent CI efficiency gate (`--fail-on-efficiency-regression`, `--min-efficiency`, exit code 5) on `occupancy_share`, with a default derived from measured run-to-run noise | 🟢 Done |
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
  functions the CLI calls, so nothing is analysed differently. One entry
  is conditional rather than fixed - `store-all.json`, the whole store
  behind the windowed `store.json` (`STORE_WINDOW = 12`, `UX-528`),
  offered only when the window hides something and fetched only when a
  reader asks for it. Three
  urls take a parameter - `blast.json?target=` and
  `whatif.json?elements=`, both of which call the function their
  subcommand calls, and `?run=<stamp>` (`UX-394`), which chooses
  **which snapshot the whole page is of**. The server is started on one
  run and serves any run in that project's store, building its
  documents on demand; the stamp is the state, so a run is a link. The
  rail draws a picker only where there is a choice - two or more runs -
  and an export, which has no store, renders none.
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
  them into eight chapters, each named for a question the reader has -
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

  The thresholds are exported names in `bga/viewer/structured.js`
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
  formatter, so the quantity table stays in `format.js`. Under three
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
  self-contained HTML file. Past `DATA_COMPACT_MIN_B` (200,000 B of
  JSON) a document is inlined gzip+base64 in an
  `application/octet-stream` block that `load()` inflates rather than as
  readable JSON text (`UX-529`) - the same document, one order of
  magnitude of bytes. What cannot survive the export at all - a live
  search box, anything needing a server - is *hidden with the command
  that answers it* rather than shipped as a control that always fails.
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

### Which file owns what

`UX-294`. The principles above are written down; the map from a
principle to the file that implements it was not, so a reader opening
`bga/viewer/` had to derive it. One line each — the file is its own
description, and this table's job is only to say which one to open.

| module | owns |
|---|---|
| `app.js` | the boot sequence, the payload fetches, the findings block, and the router that sends a section key to whatever draws it |
| `views.js` | the report's sections down to the element object: the band, the trend, the blast box, the overview and the two graphs (`UX-337`) |
| `element.js` | the element object — one element's facts, history, culprits, horizon and what-if, and the sections built per element (`UX-216`, `UX-337`) |
| `decision.js` | the first screen: the decision panel, the provenance block and the investigation context (`UX-207`, `UX-337`) |
| `structured.js` | a value becomes a table and the table becomes interrogable — columns, filters, sort, Top-N, presets, folds, the copy control (`UX-201`, `UX-289`, `UX-337`) |
| `format.js` | the nine `bga:` hint keys, the readers that pull them off a schema node, the formatters they select, and `el` — the one node constructor (`UX-201`, `UX-337`) |
| `primitives.js` | what everything may use and that uses nothing: the SVG namespace, the bar row, the anchor spelling, and whether this page is served (`UX-337`) |
| `shapes.js` | the styleguide's §1 dispatch table as code: value shape + hint → the one control that draws it (`UX-302`) |
| `tables.js` | the element table, its columns, sorting and the preset filters `bga:presets` declares |
| `nav.js` | the rail, the anchors, section collapse, and the jump box / command palette |
| `chapters.js` | the chapter grouping that turns forty-eight sections into a document (`UX-286`) |
| `viewstate.js` | the URL fragment contract — the working set `UX-211` and `UX-225` publish links against |
| `focus.js` | focusing one element and dimming the rest (`UX-222`) |
| `tablefocus.js` | opening one nested or capped table full width, and putting it back (`UX-318`) |
| `drawings.js` | sparklines and density strips: the size scale, the two drawing grades, and the boundary on what one may print (`UX-303`, `UX-316`) |
| `controls.js` | `name`/`id` for every form control the page builds, and `for` on the labels beside them — imports nothing, so `views.js` may use it (`UX-334`) |
| `rawjson.js` | the "view as JSON" toggles, and the record of which section each blob came from (`UX-302`) |
| `questions.js` | the canned SQL library, its categories, and the `why` each question carries (`UX-210`, `UX-312`) |
| `perfetto.js` | the handoff transports: `postMessage`, the `?url=` deep link, and what Perfetto's CSP will fetch (`UX-314`) |
| `perfetto_page.js` | the standalone handoff page `bga view --perfetto` lands on — and, since `UX-373`, the query library under it, which was `sql.js` |
| `trace_context.js` | the finding→query mapping that gives an investigate button its question (`UX-229`) |
| `sections.js` | the section walk: a payload and a schema become DOM — findings, verdicts, the empty-population sentence, the section router and the summary. Draws and returns; never touches the document, the URL or an event, which is `app.js` (`UX-450`) |
| `style.css` | every colour, the two token grades, and dark as the design surface (`UX-304`) |

`tests/unit/test_the_viewer_modules_have_a_home.py` holds this table
and the directory equal in both directions, so a new module that no
one documented reddens rather than joining the eight that once had no
entry here.

## The published contracts

The tool's external surface, one line each. **`--schema` is the source
of truth** - it prints the JSON Schema from `bga/schemas.py`, which the
renderers are built against, so nothing here is a second copy to drift.

| schema | what it is | printed by |
|---|---|---|
| `analyze/v5` | one run's analysis: attribution, floors, the element population, the graph's shape, findings, the headline decision, next steps, who each finding is for (`readers`, `UX-372`), and the provenance behind each claim. **v5** (`UX-535`) removed `graph_summary.total_elements`, `graph_summary.critical_path_length` and `graph_summary.max_parallelism` — three facts assigned from the same `StructuralMetrics` object `graph_metrics` publishes, so the document carried one number under two spellings in two sections; they are read from `graph_metrics.num_elements`, `graph_metrics.critical_path_length` and `graph_metrics.max_parallelism`. **v4** (`UX-344`) removed the two namespaces — `signals` and `structural` were maps of named tables that held no value of their own, so each table is a top-level key now, `metrics` and `summary` renamed to `graph_metrics` and `graph_summary` and the six element-keyed maps grouped under `elements`; `provenance` is published once per claim at the top level rather than written into every finding, the headline and each top action; and `findings[].evidence.blast_radius` is gone by `UX-288`'s rule, being a slice of a population published in full beside it. Measured on the two fixtures: leaves deeper than three fell from 57% to 40% and from 67% to 53%, and the golden report's deepest path from six levels to five. **v3** (`UX-341`) renamed every key that carried a retired unit — `measured_us`, `peak_rss_bytes`, `useful_share`, `occupancy_share` and the rest — so the payload measures time in µs, memory in bytes and a bounded fraction in 0..1, one spelling each. **v2** (`UX-288`) had removed three fields that republished element membership already published beside them — `signals.critical_path`, `signals.leaf_analysis.leaves`, and `structural.deferrability`'s two uid lists (their names at the time). `UX-345` removed one more on the same rule — `signals.critical_path_length`, which held `floors.t_infinity_observed`'s microseconds under a `count` — and renamed `signals.wall_clock_share` to `wall_clock_share_us` | `bga analyze --schema` |
| `compare/v2` | two runs, their signed deltas, the verdict and its noise band, the per-element culprits, and the candidate's diagnosis chain | `bga compare --schema` |
| `blast/v2` | what rebuilds if one repository, path or element changes | `bga blast --schema` |
| `correlate/v2` | the two planes joined on element uid, with the coverage of the join | `bga correlate --schema` |
| `store/v1` | what the run store holds: one row per snapshot, with the alias, the verdict and why a capture is not a measurement | `bga snapshot --list --format json` |
| `store-aggregate/v1` | that store as a distribution: min/median/p95/max/MAD per host class, and the refusal when a mix cannot be blended | `bga snapshot --aggregate --format json` |
| `capacity-model/v1` | that same store as a queue (`UX-613`): what a builder count and a declared arrival rate would do to utilization, the wait before a build starts and the number waiting, per host class. A model over the fact base rather than a block inside it - the arrival rate is the operator's, not measured, and every figure carries the assumption ids its own arithmetic used | `bga snapshot --capacity N,RATE --format json` |
| `whatif/v1` | what the build would drop to for a chosen set of fixes - one projection, never a sum | `bga whatif --format json` |
| `sweep/v1` | what more capacity would buy: one makespan per capacity tried, the knee past which it buys little, and where the replay model contradicted itself (`UX-339`) | `bga sweep --format json` |
| `host/v2` | the machine a capture was taken on; written into every run context and read by the cross-host refusal | inside `run-context.json` |
| `sources/v1` | every element's source resources and how each is keyed - the on-disk shape `bga blast` reads | inside `sources.json` |
| `plane2/v3` | Plane 2's report about one build: **run-level measurements, with the per-element reductions among them** - 21 of its 24 top-level blocks answer for the whole run and 3 are keyed by element uid, which is the ratio `bga correlate`'s join and every "what did this build cost" question read from opposite ends of (`UX-386`). `UX-297` retired the per-process record list, which is a statement about what was removed rather than about the shape of what is left | at `plane2.json` beside a run |
| `capture-layout/v1` | the capture directory itself (`UX-381`): every path `.bga/` holds, what writes it, what reads it, whether it is required, conditional or derived, and what an absence means. Specification 32.6, declared as `run_store.CAPTURE_LAYOUT` beside the constants it names | the directory a capture writes |
| `host-samples/v1` | the host's own memory and swap while the build ran, one JSON object per line (`UX-378`) - the series that says whether a slow build was an OOM. Written by `tools/bst_native_build_tracer.py`, which `bga.contracts`' package walk cannot see, so `run_store.OWNED` names it (`UX-381`) | at `host-samples.jsonl` beside a run |
| `bundle-manifest/v1` | what is inside a run bundle (`UX-520`): each member's snapshot-relative path, its presence word and its contract version, plus the `bga` that packed it and anything `--no-plane2` left out. Derived from `capture-layout/v1` rather than restated, and the reason the receiving side can refuse a bundle from a newer `bga` instead of half-reading it | inside `bundle.json` in a `bga bundle --export` archive |
| `plane2/v2` | the same report with the element names of every redundancy finding embedded - the shape a capture before `UX-384` wrote. With the row cap in place that list was the one term still `O(elements)`: 78% of the section at 40 elements and 99% at 1,200. Read, never written | as above, in an older store |
| `plane2/v1` | the same reductions plus every per-process record - the shape a capture before `UX-297` wrote. Read, never written | as above, in an older store |
| `analyze/v4` | what `analyze` wrote before `UX-535` removed the three graph facts `graph_summary` republished from `graph_metrics`. Read, never written | in an older store |
| `analyze/v3` | what `analyze` wrote before `UX-344` lifted the `signals` and `structural` namespaces and published `provenance` once. Read, never written | in an older store |
| `analyze/v2` | what `analyze` wrote before `UX-341` unified the units - `measured_seconds`, `peak_rss_kb`, `useful_pct`, `occupancy_ratio`. Read, never written | in an older store |
| `compare/v1` | the same, for a comparison. Read, never written | in an older store |
| `blast/v1` | the same, for a blast answer. Read, never written | in an older store |
| `correlate/v1` | the same, for the two-plane join. Read, never written | in an older store |
| `host/v1` | the host manifest with `memory_mb` where `host/v2` has `memory_bytes`. Read - and normalised on the way in, so an old baseline still compares - never written | inside an older `run-context.json` |

**Every artifact says what wrote it** (`UX-249`): a `producer` block —
tool, version, and the contract set the writing build had — rides in
every run directory and every published `analyze/v5` document, because
`bga` reads its own past output as input and until round 30 nothing in
those artifacts said which build produced them. The version there is
*provenance*; compatibility is decided per contract, which is why
`bga compare` refuses on **contract movement** and not on a version gap
(`UX-250`). Which contract states shipped together is
[`CHANGELOG.md`](../../CHANGELOG.md) (`UX-251`).

**The versioning rule**: a field rename or removal bumps the version; an
addition does not. `additionalProperties` is true everywhere, so a
consumer that pins a version keeps working while the tool grows.

Six rows are written but not printable — on-disk shapes a run
directory carries rather than documents a subcommand emits. `--schema`
does not know them, and `bga.contracts.unprintable()` says so.
The last nine go one further: they are read and never written, which
`bga.contracts.superseded()` names, because a store full of captures
taken before `UX-297`, `UX-341`, `UX-344`, `UX-384` and `UX-535` still
has to analyze.

A guard (`tests/unit/test_the_documents_keep_up_with_the_contracts.py`)
asserts this table and the spec's Part 32.5 name every contract in
`bga.contracts.ids()`, and no contract that does not exist. That
inventory is derived from the package rather than kept as a list —
`UX-248` found `sources/v1` written to every run directory and present
in no registry, no guard and no document, because the previous version
unioned the registry with a single hard-coded id. A new payload without documentation
reddens it - which is the only mechanism this repository has found that
keeps two hand-maintained copies of one fact together.

## The contracts it reads

The other half of the surface (`UX-540`): the input shapes `bga` reads
and stamps nothing with. Something else wrote them, `bga analyze`
refuses without all three, and until `UX-540` they were in no registry
at all - so no consumer could ask which input versions a release
accepts.

| schema | what it is | read by |
|---|---|---|
| `run-context/v9` | what the run was: identity, the `host/v2` manifest, scheduler configuration, the resolved `native_max_jobs` | `bga.ingest.load_run_context` |
| `graph/v9` | the declared element graph, from `bst show` | `bga.ingest.load_graph` |
| `trace/v9` | the scheduler's own spans and phases - Plane 1 | `bga.ingest.load_trace` |

`bga.ingest.READS` declares them and `bga.contracts.reads()` walks it,
beside `ids()` for what the tool emits and `superseded()` for what it
still opens. Three accessors because *emits*, *accepts* and *no longer
writes* are three different answers. `analysis/v9` (spec 32.4) is not
one of these: it is the analyzer's in-memory result shape, on no
artifact.

## Navigating the rest of the docs

- **`docs/spec/specification.md`** — original design intent, full formal Part-by-Part text (invariants, data contracts, terminology). Still authoritative for anything not listed as an extension above.
- **`docs/backlog/scenarios/README.md`** + `UX-*.md` — active backlog, full real-evidence trail for every extension above (why it was filed, what was tried, real command output).
- **`docs/backlog/tasks/`** + `docs/backlog/progress-tracker.md` — **closed** historical spec-compliance backlog (P0-P4). Read only for archaeology.
- **`docs/spec/ingestion-pipeline.md`** — real data flow from a `bst` invocation to `bga`-ingestible input.
- **`docs/guides/real-project.md`** — the end-to-end user-facing walkthrough on a real project: capture → read → go inside → join → act → gate, with real output at every step and an explicit list of what the tool refuses to say.
- **`docs/guides/optimization-walkthrough.md`** — a full worked example using the tool for real.
- **`docs/audits/case-study-06-macro-micro.md`** — the harder companion: a real macro-then-micro cycle on `examples/06-macro-micro-optimization`, written up as the case where the tool does *not* guide you, with every command and output pasted.
- **`docs/design/directions.md`** — where the tool should go next, argued separately for its two real usage scenarios (local optimization helper, and CI analytics/gate). Reading order: `architecture.md` (what it is) → `optimization-walkthrough.md` (what that felt like) → `directions.md` (what to do about it).
- **`docs/contributing/fixing-guide.md`** — mandatory session-start discipline (verification rules) for either backlog.
- **`docs/guides/cli.md`** — CLI reference/usage examples.

## Verification Log

Updated 2026-09-04 (after `UX-622`), covering one change to this
document — the opening sentence now names the population its two
backlog counts are drawn from ("the … files this commit carries"),
which is the index plus untracked and non-ignored, the population
`tools/dev_close_task.py` writes them from and
`tests/unit/test_a_counted_figure_is_derived.py` checks them against —
re-grounded in the two contract tables above against `bga.contracts`
and `bga.schemas`: **23 emitted ids, 9 of them superseded, and 3 read
and never written**, 8 printable and 15 not, and `analyze/v5` still at
**56 top-level properties**. `bga/viewer/` is still **22 modules** and
the table still names all of them. Every figure re-read and unchanged
from the entry below — this change was prose, not a contract.

Updated 2026-09-03 (after `UX-569`), covering round 83's three changes
to this document — the opening sentence's two backlog counts, the
`tools/` dispatch list under the layout block, and the two stale `.md`
names in the reading order — re-grounded in the two contract tables
above against `bga.contracts` and against `bga analyze --schema`:
**23 emitted ids, 9 of them superseded, and 3 read and never
written**, 8 printable and 15 not, and `analyze/v5` still at **56
top-level properties**. Every figure re-read and unchanged from the
entry below: round 83 published no new contract id, and the one
commit that touched `bga/schemas.py` added keys under `elements`,
which 32.5's rule makes an addition. `bga/viewer/` is still **22
modules** and the table still names all of them. Recorded by
architecture review 14, whose row is in
[`../audits/architecture-review.md`](../audits/architecture-review.md);
the entry below was true about its own date and named a round older
than the file's last change, which is the half that guard cannot read.

Updated 2026-09-03 (after `UX-549`), covering round 81's three
changes to this document — `UX-540`, `UX-548` and `UX-549` —
re-grounded in the two contract tables above against `bga.contracts` — **23 emitted ids, 9
of them superseded, and 3 read and never written**. The third set is
new: `graph/v9`, `run-context/v9` and `trace/v9` are declared by
`bga.ingest.READS` and answered by `contracts.reads()`, which is the
chapter *The contracts it reads* below the inventory. 8 printable and
15 not; `schemas.schema`'s `analyze/v5` still has **56 top-level
properties**, re-read here and unchanged. The viewer chapter's document
table now names `store-all.json` as its one conditional entry
(`UX-528`), and the `--export` bullet says a document past
`DATA_COMPACT_MIN_B` travels gzip+base64 (`UX-529`).

Updated 2026-09-02 (after `UX-535`), re-grounded in the contracts
table above against `bga.contracts`'s derived inventory — **23 ids, 9
of them marked superseded**, 8 printable and 15 not — and the keys
`bga analyze --schema` prints: **56 top-level properties**, unchanged,
because round 80's move was a removal *and* a re-read, not an addition.

Round 80 changed this document in three places, each the table that
already owned the fact. The CLI table gained `bga bundle` (`UX-520`):
the capture-layout set as one archive, with a manifest that lets the
receiving side refuse a bundle from a newer `bga` rather than half-read
it. The contracts table gained `bundle-manifest/v1` for that manifest,
and moved `analyze` to **v5** (`UX-535`) — `graph_summary` published
three facts it took from the same `StructuralMetrics` object
`graph_metrics` publishes, so three removals, and `analyze/v4` joins
the rows below it that are read and never written. The viewer chapter
is unchanged:
`bga/viewer/` is still **22 modules** and the table still names all of
them, which `test_the_viewer_modules_have_a_home.py` holds both ways.

The round-73 grounding, kept for what it settled:

Updated 2026-09-01 (after `UX-472`), re-grounded in the contracts
table above against `bga.contracts`'s derived inventory — **21 ids, 8
of them marked superseded**, 8 printable and 13 not — and the keys
`bga analyze --schema` actually prints: **56 top-level properties**.
Both figures are unchanged from the round-65 grounding below and from
`UX-450`'s, and are re-read here rather than carried forward.

Round 73 changed this document in one place: the "One script in
`tools/`" sentence became a **Where fixtures come from** section.
`UX-472` filed it because that sentence claimed uniqueness — one script
outside the capture pipeline needing no `bst` — and round 72 shipped
three more tools it cannot hold. What replaces it is `UX-463`'s split
between curated fixtures and generated projects, which was settled in a
backlog row and lived nowhere a reader of the architecture would find
it. The two censuses added in the same round are named but not listed:
they are in the fixing guide's §6 with every other dev instrument, and
`dev_js_deps.py` and `dev_perfetto_queries.py` were already the
precedent for that being their only home.

Round 71 changed this document in one place only, the viewer chapter's
module table, which gained `sections.js`: `UX-450` split the section
walk out of `app.js`, which sat exactly on `UX-337`'s 1,500-line
ceiling. The directory is **22 modules** now and the table names all
of them — `test_the_viewer_modules_have_a_home.py` holds the two equal
in both directions, and is what failed when the row was missing.

The round-65 grounding, kept for what it settled: round 65 changed
this document in one place only, the viewer chapter's document table,
which gained `?run=<stamp>` beside the two endpoints that already took
a parameter (`UX-394` shipped it in round 64 and no document named it;
`UX-416` is that gap).

The paragraph below is round 62's grounding and is kept for what it
records about the v4 move.

Re-grounded 2026-08-29 (after `UX-372`) against eighteen ids, five
superseded, and fifty-two top-level properties, `readers` among them,
with `reader` declared on the findings item. That was an addition and
not a version move — nothing changed meaning and nothing left — so
`analyze` is still at **v4** for the reason it went there: the two
namespaces are gone, `provenance` is published once per claim, and one
evidence key that republished a population went with them — three
removals, which is what a version move is for. The row is checked
against the keys the schema declares, and `ANALYZE_FULL_KEYS` now names
the eighteen tables the namespaces used to hold, with a third list for
the four that depend on what the run has rather than on which planes
were captured.

**What the lift left measurable.** The document publishes its own
shape: `document_shape` carries the leaf count, the deepest path and
the count over three levels, counting itself, so the next round reads
the depth off the document instead of writing a script against two
fixtures — and a guard re-measures and compares, which is the clause
that would catch a level coming back.

**What the two rounds asserted that no guard held before.** `UX-341`
made the vocabulary five members and `DIMENSIONS` state what each
measures, so "no two members measure one dimension" is a property the
suite evaluates rather than a list of retired names a later round could
re-add. `UX-343` made every numeric leaf on the page carry a
declaration — 98% and 99% declared on the two fixtures, from 26% and
24%. `UX-345` closes the third gap the first two structurally cannot
see: a leaf that declares a *valid* member and holds a value that
member cannot be. `signals.critical_path_length` declared `count` and
held 43,200,000 microseconds; the check that a `count` is integral and
a `share` is in 0..1 found two more the same day
(`signals.wall_clock_share`, `confidence.duration_coverage`).

Updated 2026-08-27 (after `UX-337`), re-grounded in `bga/viewer/`, which
is twenty modules rather than fifteen: `app.js` and `views.js` held
5,283 of the viewer's 9,603 lines between them and now hold 2,151, with
`primitives.js`, `format.js`, `structured.js`, `element.js` and
`decision.js` carrying the rest. A pure move — the exported page is
byte-identical but for the two characters of one `?.`, and both
committed fixtures render the same 28 and 40 sections booted in real
Chrome.

**What the round added that no guard held before.** The export
concatenates the modules in the order `tools/bga_view.py::_module_order`
derives from `import` lines, and its premise is that what a module
imported is declared above it. `walk()` adds a module to `seen` *before*
recursing, so a cycle does not hang — it emits an order in which a
module precedes something it imports, and the blob reads a `const` in
its temporal dead zone. That is `UX-199`'s empty report by a new route,
and it was unasserted.
`tests/unit/test_the_viewer_splits_along_its_seams.py` now asserts the
order is a real topological order of the graph, that no module uses a
re-export form `_IMPORT_RE` cannot see (`export * from` is the tidy
shape a future round will reach for, and it produces an export that
never inlines the module at all), that everything inlined is also
served, and that no module is over 1,500 lines.

**The instrument was wrong before it was right.** The symbols crossing
each candidate cut were counted with comments and string literals
stripped — first by regexes, which paired the backtick of a template
holding `${…}` with a later one and ate 90% of `app.js`, reporting a
cleaner split than the real one. The character scanner that replaced it
found three more crossings. The lesson is the repository's own: an
instrument that reports a good answer is not thereby correct, and the
cheapest check is whether it still sees the file.

Updated 2026-08-27 (after `UX-334`), re-grounded in the viewer module
map against the directory it claims to describe: `bga/viewer/` gained
`controls.js`, and `tests/unit/test_the_viewer_modules_have_a_home.py`
holds the table and the directory equal in both directions, so the row
below was not optional. The same round's instrument is
`tests/cdp.mjs --observe` and
`tests/unit/test_the_console_stays_clean.py`, which read what the
*browser* says about the page - the first thing in this repository to
do so, and the reason the served report's exhibit geometry could
disagree with the export's for ten rounds unnoticed.

Updated 2026-08-26 (after `UX-310`), re-grounded in
`tools/native_trace/trackevent.py`'s `counter_track`/`counter`, in
`tools/bga_timeline.py`'s `concurrency_series`, and in
`tests/unit/test_the_counter_the_constant_was_waiting_for.py`. The
Plane 2 bullets now say what the trace graphs and - as load-bearing -
what it declines to graph and why.

**A guard caught the whole round on the way past.**
`examples/06-macro-micro-optimization/.bga/runs/**` is gitignored: it
exists on this machine and not in a clone. Every clause `UX-308`,
`UX-309`, `UX-310` and `UX-311` wrote against it would have passed here
and failed in CI before an assertion ran, and
`test_a_guard_reads_only_what_a_clone_has.py` says so by name. It fired
on this item, where the last committed fixture had just been removed as
an unused import; the same defect was latent in the three before it.
The repository's convention is a skipif, and a skip alone would leave
CI believing something it never ran - so every *property* those clauses
check now has a committed-fixture clause beside it, and only the
*figures* (813 records, 412 past the 120-character name, 538 samples,
836 flows) stay behind the skip. Verified by moving that directory
aside and running the four files as a clone sees them: **61 passed, 17
skipped**, clone guard green.

Six mutations against the committed tree, all discriminating after one
repair, and one rejected:

```text
M1  open records extended to the trace's last stamp          6 red
M2  a tie is resolved start-first                            1 red
M3  the window keeps its close and drops its maximum         2 red
M4  the track claims to be a memory series                   2 red
M5  the counter track forgets it is a counter                2 red
M6  the sweep is walked in reverse                           9 red
--  `open` dropped from the exclusion test               rejected
```

M6 is the one that changed the code. Its first form - removing the
"drop a backwards sample" branch from the series filter - **passed**,
and the reason is that the branch was dead: the construction never
produces a backwards sample, and a filter that silently swallowed one
would *hide* a construction bug rather than fix one. The branch is gone
and the ordering is asserted in the guard instead, where a break in it
fails loudly; reversing the sweep then reddens nine clauses including
that one.

M1's first form was rejected rather than counted. Dropping `open` from
the exclusion test changes nothing, because `_open_record` always sets
`end_ts` to `None` - the two halves of that condition are one fact.
The mutation that is a real defect is the historical one
`compute_max_concurrency`'s own docstring describes: extending an open
record to the trace's last timestamp, which once produced a
`max_concurrency` of 24 for a `-j4` build. That reddens six clauses.

Updated 2026-08-26 (after `UX-311`), re-grounded in
`tools/native_trace/trackevent.py`'s `order_processes_explicitly` and
ranked `process_track`, in `tools/bga_timeline.py`'s `run_identity` /
`identity_annotations` / `identity_track_name`, and in
`tests/unit/test_the_trace_knows_whose_build.py`. The viewer axis now
says what a trace states about its own run, which it could not before
there was anything in it to state.

Six mutations against the committed tree, all discriminating:

```text
M1  the root descriptor never asks for explicit order        1 red
M2  every element lane takes the same rank                   1 red
M3  the incompleteness is an annotation and not the name     3 red
M4  the reason is re-derived from `interrupted` alone        3 red
M5  the lane label drops the element kind                    3 red
M6  the identity forgets which run it is                     3 red
```

M4 is the one worth keeping. `interrupted` alone is the obvious
re-derivation and it is wrong twice over - a failed run and a suspended
one are both incomplete, which is exactly why `UX-156`, `UX-157` and
`UX-185` were joined into one accessor. The guard parametrizes all
three, so the shortcut cannot pass by being right about the case whoever
wrote it had in mind: it reddens on `failed` and on `suspended` and
stays green on the one it remembered.

M1 is the one that would otherwise have been silent. Dropping the root
packet leaves every rank on the wire, every lane in the right order in
the file, and a UI that ignores all of it - a trace that looks correct
and orders nothing. Only a clause that reads the root descriptor can
tell the difference.

Updated 2026-08-26 (after `UX-309`), re-grounded in
`tools/native_trace/trackevent.py`'s flow writer, in
`tools/bga_timeline.py`'s `dependency_edges` / `_plane1_flows` /
`_plane2_flows`, and in `tests/unit/test_the_arrows_say_why_now.py`.
The Plane 2 bullets now say which relations the trace draws as
causation and which it refuses to.

Six mutations against the committed tree, all discriminating:

```text
M1  flow ids written as varints instead of fixed64   1 red, 9 errors
M2  the parent lookup crosses sandboxes                     1 red
M3  a backwards or tied edge is drawn anyway                3 red
M4  one event both starts and ends a flow                   7 red
M5  a half-connected edge is emitted                 1 red, 9 errors
M6  the two planes reuse each other's flow ids              7 red
```

M2 is the one worth keeping. It **passed** the first time: the fixture
ran its two sandboxes ten seconds apart, so a lookup that forgot the
invocation still found the right shell by accident - the other one had
already exited. A parallel build's sandboxes overlap, which is the
whole reason pids collide; the fixture now starts the second shell
50 ms after the first, both are alive when either's children fork, and
the mutation reddens. The fixture was wrong, not the guard, and the
mutation is what said so.

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

Eight mutations against the committed tree, all discriminating, and a
ninth rejected:

```text
M1  a contract key is emitted under a different name       4 red
M2  a key is documented and never written                  3 red
M3  the failed rule is the first draft's `not in (None,0)` 3 red
M4  an absent field is annotated as zero                   2 red
M5  the annotation is truncated like the name              3 red
M6  the Plane 2 annotations are dropped from the begin     7 red
M7  a wrong field number for `debug_annotations`           1 red
M8  annotation names go into the event-name table       1 red, 12 errors
--  the three interning tables share one iid counter       rejected
```

M7 reddens **only** the schema clause, and that is the point: this
round's own decoder reads the constant it is checking, so a wrong
number is invisible to it and the committed fixture is the only thing
that can see it - which is what `UX-298`'s docstring says and what this
mutation confirms rather than assumes. The rejected one is not a defect:
iids unique across tables are legal, so sharing a counter only wastes
the low ones. It is written down rather than counted.

**A finding the first draft made and the record refuted.** `spine.c`
writes `exit=%d` for a normal exit and `exit=signal:%d` for a killed
one, so `exit_status` is a *string with a vocabulary*, not a number.
The first failed-category rule read `status not in (None, 0)` - which
would have marked **every** process failed, because `"0"` is not `0`.
Success is exactly the string `"0"`, and the constant that says so has
a name and three assertions on it.

Updated 2026-08-26 (after `UX-294` and `UX-295`), re-grounded in the
new `Which file owns what` table above and in `docs/guides/cli.md`'s
`whatif/v1` entry — the two halves of review 3's *does this have a
home* checklist that were still open.

Both were found the same way and both had the same shape: a guard that
was green because it was asking the maintainer's question.
`UX-294`'s acceptance (*named in at least one document under `docs/`*)
had become true of all fifteen viewer modules by attrition, while the
architecture — the document a reader of `bga/viewer/` opens — named
eight; so the guard went on the map instead. `UX-295`'s contract-home
guard checked the spec and this document, which is where a maintainer
looks, so `whatif/v1` being absent from every *guide* sat under it
unnoticed; the new clause asks the reader's question, scoped to the
printable contracts with the run-directory shapes exempted by name.

Six mutations across the two, all discriminating. Recorded because it
recurred: the first attempt at two of `UX-294`'s measured nothing —
`git checkout -- docs/` reverted the uncommitted map between
mutations, so the guard was asserting against a document with no table
in it. Mutation testing runs against a committed tree.

Updated 2026-08-26 (after `UX-314`'s browser verification), re-grounded
in what the deployed Perfetto UI actually does with the deep link.

The reporter suggested running Perfetto locally, and it worked better
than expected: `ui.perfetto.dev` is refused at CONNECT here, but the
bucket serving it is not, so the whole UI (81 files, `v58.2`) mirrors
byte-for-byte and stamps its own CSP exactly as the live site does -
checked by reading the directive back out of the shipped bundle. Driven
over CDP with the Chromium already installed:

```text
                                   CSP        request     result
A  http://127.0.0.1:41234      REFUSED    never sent    empty Perfetto
B  http://localhost:8080        passed    SENT          CORS: no grant
C  http://localhost:8080        passed    RESPONSE 200  trace loaded
   (+ grant issued)
```

A is the field report reproduced verbatim, down to the console text. B
separates the two layers: on a CSP-legal origin the request is sent and
*then* fails CORS, which is the cleanest demonstration that the
`Access-Control-Allow-Origin` grant is necessary and not sufficient. C
is the handoff working, and it closes `UX-298`'s second recorded
deviation - the one-time UI open - which had assumed the trace would
have to be uploaded to a third party. It did not.

Updated 2026-08-26 (after `UX-312`), re-grounded in
`bga/viewer/questions.js` as it now selects, `tools/bga_timeline.py`'s
three scope categories, and `docs/spec/trace-dictionary.md` - which is
the trace's half of what the styleguide is to the report, and is held
equal to the emitter's own contract in both directions.

The finding is worth the entry. The canned question library was not
thin, it was **dead**: `UX-204` wrote it against the Chrome JSON trace
(`args.<key>`, a `cat` field), `UX-298` made TrackEvent the default
(`debug.<key>`, and `EVENT_CATEGORY_IIDS` unused until `UX-308`), and
nobody re-pointed it. All six questions returned zero rows, in silence,
because `extract_arg` on an absent key is null rather than an error.
Decoded off the wire before the fix: zero categories interned.

Eight mutations, all discriminating; two of them run twice, because the
first attempt at each broke the module rather than the property. Two
existing guards had been asserting the broken shapes and are corrected
rather than deleted.

Updated 2026-08-26 (after `UX-314`), re-grounded in
`bga/viewer/perfetto.js`'s `perfettoCanFetch`, `tools/bga_view.py`'s
`landing_url`, and the two handoff guards that now parametrize the
served origin. The viewer axis gains the rule it was missing: a
transport is only offered where the *other* side's policy permits it.

A field report - `connect-src` in ui.perfetto.dev's console, no trace -
turned out to be Perfetto's own Content-Security-Policy, not this
server's headers. Our `Access-Control-Allow-Origin` grant is necessary
and not sufficient: when `connect-src` refuses, the request never
leaves the browser for CORS to answer. Read from
`ui/src/frontend/index.ts` rather than guessed, over plain `http:`
exactly two origins are fetchable - `127.0.0.1:9001` and
`localhost:8080` - and `bga view` binds an ephemeral port, so the
`?url=` deep link had never worked in served mode. `UX-299` then made
it the only transport above 4 MiB.

Eight mutations, all discriminating:

```text
P1  served implies fetchable (the bug as it shipped)   3 guards red
P2  the host spelling is ignored                       1 red
P3  8080 is named by address again                     3 red
P4  navigate to a link CSP will refuse                 1 red
P5  the save-it-yourself route disappears              1 red
P6  the server stops saying the handoff is limited     1 red
P7  the rule stops saying where it was read from       1 red
P8  the message stops naming the way out               1 red
```

P4 passed on the first run, and that is the finding. The
over-threshold branch was the whole bug and nothing covered it,
because `UX-299`'s harness pinned `location` to a refused origin while
asserting the navigation happened - a guard written entirely from this
side of the boundary. Both halves of the fix are now held to one
answer by a clause that runs the Python spelling through the
JavaScript predicate.

**Not verified against the live site.** Both Perfetto hosts are
refused by this environment's network policy, so this is argued from
Perfetto's source and guarded against it, not confirmed in a browser.

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

Updated 2026-08-26 (after `UX-320`), re-grounded in
`bga/viewer/drawings.js`'s `SCALE` and its two grades,
`bga/viewer/tablefocus.js` as it now stands, `bga/viewer/index.html`'s
header and actions group, and `tools/bga_view.py`'s `ASSETS`: the
viewer module map gained `tablefocus.js` and `drawings.js`'s row now
says the size scale is its. Four measurements this round, each taken
rather than argued - the sticky header 172px to 92px at 1440x900 and
284px to 134px at 390x844 with the actions moved out; the click cost of
reaching any section, 1 wide and 2 narrow, unchanged by the round and
recorded because it had never been taken; +44,601 B of checked-in
viewer source, per file; and the exported page measured at 89% code,
which falsified round 41's claim that 175 KB of it was commented
JavaScript and corrected `UX-307`'s motivation accordingly.

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
the contracts table's `analyze/v5` row is checked against the keys the
schema declares - which `UX-275` added one to. The date on this line is
guarded (`UX-247`): a commit that changes this document's prose without
re-grounding it reddens
`tests/unit/test_the_verification_log_is_true.py`.

Updated 2026-08-18 (after `UX-76`), re-grounded in `bga/cli.py`'s real subparser definitions, the current `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s backlog table re-read in full: the extensions table gained `UX-41`–`UX-76`, the Plane 2 and join sections gained what rounds 7–10 measured, and the package listing gained `findings.py`/`correlate.py`/`tools_dispatch.py`. Every figure quoted is from the capture published as `5eda28a` or from the task file that measured it.

Originally written 2026-08-16, grounded directly in `bga/cli.py`'s real subparser definitions, `bga/` and `tools/` directory listings, and `docs/backlog/scenarios/README.md`'s own current backlog table (re-read in full, not from memory) - not written from the original spec or from assumption. No code changed; this is a docs-only addition.
