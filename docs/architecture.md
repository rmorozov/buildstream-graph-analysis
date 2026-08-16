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
| `bga compare BASELINE CANDIDATE` | Run-to-run deltas + improved/regressed verdict — **not spec-mandated**, `UX-01` | — |

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

## Plane 2: intra-element native-build-system tracing (`UX-11`)

`tools/bst_native_build_tracer.py` wraps a real `bst build` invocation: a `bwrap` shim placed ahead of the real binary in `$PATH` injects an `LD_PRELOAD` hook (`tools/native_trace/hook.c`) into every dynamically-linked process the sandbox execs, recording real `CLOCK_MONOTONIC` start/end timestamps. Validated end-to-end against a real `cmake`+`make`+`gcc` build (98 real traced processes, reproduced real `-j4` compile concurrency across independent runs). Known, honestly-reported limitation: statically-linked processes are invisible to this mechanism and there is no way to detect that gap from outside — every report carries a fixed disclaimer rather than a false completeness claim. Full design history (five brainstormed options, an external design contribution, a risk-reduction spike, a second external review that was checked and refuted, and the final validated mechanism) is in `docs/scenarios/UX-11-native-build-system-profiler-tool.md` — read that only if you need the *why*; this doc is the *what, today*.

Every traced process is tagged with its real owning BuildStream element (`UX-23`, parsed from BuildStream's own `--dir` bwrap option), enabling `detect_redundant_operations` (same file) to flag real operations repeated independently across multiple elements' own sandboxes. `tools/native_trace_to_chrome_trace.py` (`UX-24`) exports Plane 2 traces as Chrome Trace JSON, standalone or combined with Plane 1's own real export for the same run — `bst_native_build_tracer.py run --wrapped-log PATH` captures both planes from one single real `bst build` invocation.

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
| UX-27..UX-40 | **Open backlog round (2026-08-16 audit).** Filed together from a real claims-vs-reality audit plus a full macro-then-micro walkthrough of the new `examples/06-macro-micro-optimization`. Anchor finding: every certified floor is derived from the run's *own observed graph*, so a deliberately-serialized build scores `efficiency_score` 1.00 with 0.00s headroom, and a real 30.5% optimization moves both numbers backwards. See `docs/design-directions.md`. | 🔴 Open |

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
