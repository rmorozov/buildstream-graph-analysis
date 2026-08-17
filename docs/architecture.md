# `bga`: Current Architecture — Two Analysis Planes

**Start here to orient in this codebase.** `docs/specification.md` (v9) is the original design document and stays authoritative for full-length invariant/data-contract text — it is *not* wrong, but it describes the tool as originally scoped, and does not know about anything built since. This doc describes what `bga` actually does **today**, as one coherent system, and points at the real file/doc for every claim so you don't have to reconstruct that history from 22 `docs/scenarios/` files, 75 `docs/tasks/` files, and the commit log yourself.

## The shape of the tool today

`bga` was designed as a single-plane analyzer: given one real BuildStream run's element-level log, reconstruct the dependency graph, classify every wait gap into one of 8 attribution categories, and report certified/advisory floors — a **whole-project** view. That plane is real, done, and still the tool's core (`docs/specification.md`'s v9 design, unchanged in its fundamentals).

What's changed since: the tool now has a **second, complementary plane** — real visibility *inside* a single element's own sandbox, at the native-build-system level (`make -jN`, `cmake --build`'s own internal process tree) — deliberately kept as a separate mechanism with its own separate horizon, not folded into the first plane's `Σattribution == H` accounting. Together:

- **Plane 1 (whole-project, spec-native)** answers *"which elements/phases dominate this build's critical path, and where is real scheduling/resource capacity being wasted across the whole run?"*
- **Plane 2 (intra-element, `UX-11`)** answers *"inside this one element's own sandbox, is its native build system actually achieving the parallelism it should, or silently serializing / contending against sibling elements?"*

Neither plane subsumes the other, and that's intentional: Plane 1 operates purely on BuildStream's own element-level log (one START/SUCCESS pair per element, no visibility below that) and needs no live BuildStream install to analyze a captured run; Plane 2 requires a real, live `bwrap`+`LD_PRELOAD`-capable sandbox to capture from, and produces a different kind of artifact (a raw per-process trace) with no shared timeline contract with Plane 1's `trace/v9`.

### Where the two planes connect — a real, not-yet-built opportunity

Plane 1 already tells you *which* elements are expensive or on the critical path (`UX-20`'s `sensitivity.top_opportunities`, `UX-22`'s serialization-point detection). Plane 2 can now tell you, for any *one* of those elements, exactly what its own native build system spent its time on. Running Plane 2 across **multiple** elements of the same project opens a genuinely new class of question neither plane can answer alone: are several elements each independently, redundantly doing the *same* real sub-work inside their own sandboxes — the same expensive `configure` step, the same codegen invocation, the same dependency-resolution pass — that could be shared or cached once instead of paid for by every element separately?

**Confirmed real, not hypothetical, and now automatically detected** (`UX-23`, done): a real, fully-fresh `bst build all.bst` capture of `examples/05-cmake-cpp-toolchain` (6 cmake elements) traced under Plane 2, with real `--dir`-based element tagging, produced **37 redundant-operation findings, every one correctly spanning all 6 real elements** - including the exact CMake compiler-ABI-detection probe this section originally found by hand. Implementing element-tagging also surfaced and fixed a real, previously-latent correctness bug in `UX-11`'s own original design: pairing traced process START/END events by pid alone is unsound once a trace spans multiple elements, since each element gets its own independent `--unshare-pid` namespace and the same small pid number recurs across every element's sandbox. `UX-24` (Chrome Trace export for Plane 2, and a combined two-plane `perfetto.dev` view) is done too: one real single `bst build` invocation now captures both planes at once (`bst_native_build_tracer.py run --wrapped-log`), and a real end-to-end run confirmed the two clocks correlate correctly - Plane 2's earliest event landed exactly on Plane 1's own real build-start timestamp. Closest existing relatives: `UX-20` (batch/map-reduce simulation, but over already-observed element durations, not intra-element operation identity) and `UX-14`'s tier-2 design (PR #58/#61, cross-run calibration, a different but related use of multi-capture comparison).

## Real current CLI surface (Plane 1)

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
| `bga compare BASELINE CANDIDATE` | Run-to-run deltas + improved/regressed verdict, and **two independent CI gates** — duration (`--fail-on-regression`, exit 4) and efficiency (`--fail-on-efficiency-regression`/`--min-efficiency`, exit 5). **Not spec-mandated**, `UX-01`/`UX-03`/`UX-39` | — |

## Real package structure (Plane 1)

`bga/` mirrors the spec's own pipeline stages fairly directly:

```
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
report/       -> text/JSON rendering
```

`tools/` is a separate, deliberately-not-`bga`-internal set of scripts that turn a real `bst` invocation into `bga`-ingestible input (needs a live `bst`+`bwrap` install; `bga` itself never does) — full data-flow diagram in `docs/ingestion-pipeline.md`. `tools/bst_native_build_tracer.py` (+ `tools/native_trace/`) is Plane 2 — see below.

One script in `tools/` is not part of that pipeline and needs no `bst` at all: `tools/gen_synthetic_scale_run.py` emits a synthetic run directory (`graph.json`/`trace.json`/`run-context.json`) at a scale no example project in this repo reaches — by default 1202 elements over 14 real levels, scheduled onto 16 builders by a real dependency-respecting greedy pass so the trace satisfies the same ordering and capacity properties a real capture does. It exists because the second audit round found four defects that were invisible at eleven elements (`UX-41`–`UX-44`), and their acceptance tests all cite this fixture; running it with the same `--seed` reproduces the directory byte-for-byte. It exercises `bga`'s **analysis** side only — nothing about a synthesized run directory says whether the capture tools survive a thousand-element build.

## Plane 2: intra-element native-build-system tracing (`UX-11`)

`tools/bst_native_build_tracer.py` wraps a real `bst build` invocation: a `bwrap` shim placed ahead of the real binary in `$PATH` injects an `LD_PRELOAD` hook (`tools/native_trace/hook.c`) into every dynamically-linked process the sandbox execs, recording real `CLOCK_MONOTONIC` start/end timestamps. Validated end-to-end against a real `cmake`+`make`+`gcc` build (98 real traced processes, reproduced real `-j4` compile concurrency across independent runs). Known, honestly-reported limitation: statically-linked processes are invisible to this mechanism and there is no way to detect that gap from outside — every report carries a fixed disclaimer rather than a false completeness claim. Full design history (five brainstormed options, an external design contribution, a risk-reduction spike, a second external review that was checked and refuted, and the final validated mechanism) is in `docs/scenarios/UX-11-native-build-system-profiler-tool.md` — read that only if you need the *why*; this doc is the *what, today*.

The hook records three things per process, and the second and third arrived in the third round of work:

1. **Lifecycle** (`UX-11`) — `CLOCK_MONOTONIC` START/END, which is what every timing analysis below is built on.
2. **Real CPU time** (`UX-45`) — `getrusage(RUSAGE_SELF)` plus `RUSAGE_CHILDREN` in the destructor, the one place with access to the kernel's own accounting for a process about to exit. This is `bga`'s **only** CPU-time measurement anywhere; everything in Plane 1 is slot occupancy, and deliberately still says so (see `UX-36` below). Its value is a question Plane 1 structurally cannot answer — *was this element CPU-bound or waiting?* On a real capture, `core.bst` (pinned with `notparallel: True`) runs at **0.87 cores busy** while every sibling runs at ~1.7. Coverage is always reported: a process killed by a signal, or one replaced by `exec`, runs no destructor and is counted as **unmeasured**, never as zero (~19% of processes in a real `examples/06` build).
3. **Opened file paths** (`UX-46`, opt-in via `--trace-opens`) — `open`/`openat` interposition, deduplicated in-process and flushed once at exit. Opt-in because unlike the other two it runs on a genuinely hot path. Matched against `bst artifact list-contents`, this answers *"which of this element's declared build dependencies did its sandbox never read?"* — the last macro-level gap, and the one problem in `examples/06` that no Plane 1 signal could find. It **refuses rather than guesses**: an element with no observed opens (a statically-linked build looks identical to one that used nothing) or with a truncated read set is reported `uncovered`, never as having unused dependencies.

Every traced process is tagged with its real owning BuildStream element (`UX-23`, parsed from BuildStream's own `--dir` bwrap option). Two further analyses build on that. `compute_per_element_parallelism` (`UX-32`) reports, per element, the parallelism its native build system *actually achieved* against the `-jN` it asked for - splitting real work processes (compilers, assemblers, linkers) from orchestration that spends its life waiting on children, and emitting two findings: `pinned_to_one_job` (this element asked for `-j1` while its siblings asked for more - the `notparallel` case, invisible to any achieved-vs-requested ratio, since a pinned element gets exactly what it asked for) and `underachieved_requested_jobs`. `detect_redundant_operations` (`UX-23`, rescored by `UX-37`) flags real operations repeated independently across multiple elements' own sandboxes, ranked by *recoverable wall-clock* rather than by process time summed across elements that ran concurrently, and excluding each element's own build driver (identical across elements by construction, entirely different work in each). `tools/native_trace_to_chrome_trace.py` (`UX-24`) exports Plane 2 traces as Chrome Trace JSON, standalone or combined with Plane 1's own real export for the same run — `bst_native_build_tracer.py run --wrapped-log PATH` captures both planes from one single real `bst build` invocation.

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

```
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

## Core invariants still load-bearing (Plane 1)

The spec's invariants (full text: `docs/specification.md`) remain the real correctness contract every Plane 1 change is checked against:

- **I4** `Σ attribution == H` (horizon) — checked by `bga/validation/invariants.py`, exercised end-to-end by every attribution-touching change (e.g. `UX-19`'s wait-gap re-saturation fix).
- **I8** run-identity capture/enforcement (`UX-07` fixed a real cross-sibling-project collision in it).
- **I9** CPU-accounting reconciliation within tolerance.
- **I11** determinism (same input → byte-identical output, N-run harness in `bga/validation/determinism.py`).
- **I12** cold-floor independence from certified/measured attribution.

## Real extensions beyond the original spec

Everything below is **additive**, not a spec contradiction — each is clearly marked non-spec in its own code/docstrings. This table is the one-scan replacement for reading all 22 `docs/scenarios/*.md` files individually; each still has the full evidence trail if you need it.

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

(`UX-08` was never filed — not a missing/lost file.)

## Navigating the rest of the docs

- **`docs/specification.md`** — original design intent, full formal Part-by-Part text (invariants, data contracts, terminology). Still authoritative for anything not listed as an extension above.
- **`docs/scenarios/README.md`** + `UX-*.md` — active backlog, full real-evidence trail for every extension above (why it was filed, what was tried, real command output).
- **`docs/tasks/`** + `docs/fix-progress-tracker.md` — **closed** historical spec-compliance backlog (P0-P4). Read only for archaeology.
- **`docs/ingestion-pipeline.md`** — real data flow from a `bst` invocation to `bga`-ingestible input.
- **`docs/optimization-walkthrough.md`** — a full worked example using the tool for real.
- **`docs/optimization-walkthrough-06.md`** — the harder companion: a real macro-then-micro cycle on `examples/06-macro-micro-optimization`, written up as the case where the tool does *not* guide you, with every command and output pasted.
- **`docs/design-directions.md`** — where the tool should go next, argued separately for its two real usage scenarios (local optimization helper, and CI analytics/gate). Reading order: `architecture.md` (what it is) → `optimization-walkthrough-06.md` (what that felt like) → `design-directions.md` (what to do about it).
- **`docs/fixing-guide.md`** — mandatory session-start discipline (verification rules) for either backlog.
- **`docs/cli.md`** — CLI reference/usage examples.

## Verification Log

Written 2026-08-16, grounded directly in `bga/cli.py`'s real subparser definitions, `bga/` and `tools/` directory listings, and `docs/scenarios/README.md`'s own current backlog table (re-read in full, not from memory) - not written from the original spec or from assumption. No code changed; this is a docs-only addition.
