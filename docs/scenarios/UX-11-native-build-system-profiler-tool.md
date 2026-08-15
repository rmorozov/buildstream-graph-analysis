# UX-11: a tool to observe native-build-system behavior *inside* a single element

**Priority:** Medium | **Status:** 🔴 Not Started (design brainstorm only) | **Depends on:** `UX-09` (the joint-optimization finding this directly follows from)

## Motivation

The user's own proposed direction, following `UX-09`'s confirmation that `--builders` and native `max-jobs` genuinely compete for the same CPU cores with no coordination: since `bga` currently has zero visibility into what happens *inside* a single element's "Running commands" span (BuildStream logs exactly one START/SUCCESS pair per element regardless of how many `make -jN`/`ninja` sub-processes ran inside it), a real, separate tool is needed to analyze the native build system's *own* behavior within one element - is its internal parallelism actually being used well, or is a `make -j8` inside a `cmake` element secretly running mostly serial (bad internal dependency graph), or badly thrashing against sibling elements' own compiles (`UX-09`'s oversubscription finding, made visible per-element rather than only in aggregate wall-clock)?

This is explicitly a **separate, large tool** from `bga`'s existing analysis (which operates on BuildStream's own element-level log, not anything from inside a sandbox) - filed here as a design brainstorm for a future session, not attempted this session.

## The real constraint: no shared job-server, no remote-execution visibility

Confirmed in `UX-09`: BuildStream has no jobserver-style coordination across sandboxes (grepped the real installed source - zero matches), so there's no existing hook point to "ask" a running `make -jN` how it's actually using its job slots from the outside. And when BuildStream's remote-execution sandbox path is active (`sandbox/_sandboxremote.py` - real, confirmed), the actual compute happens on a remote worker entirely outside the local client's reach; only the CAS is observable. This means any real intra-element profiling tool can **only work for local (non-remote-execution) sandboxes**, and has to observe from *outside* the native build system's own process tree (no cooperative instrumentation available) - a genuine, non-trivial constraint on the design space, not an incidental detail.

## Real, concrete design options (brainstormed, not chosen)

1. **Wrap the native build command with a real process-tree sampler.** BuildStream elements' `build-commands` are just shell commands (`cmake --build ... -- -jN`, `make -jN`) - a wrapper script substituted in place of the real `make`/`ninja` binary inside the sandbox (via `PATH` shadowing, similar in spirit to how `examples/stage_cpp_toolchain.sh` stages real binaries) could sample `/proc/<pid>/stat`-style CPU/wall-clock data for every child process spawned, at a fixed interval, and emit a small structured log per element. Real, buildable with what's already in this repo's toolbox (a bwrap sandbox + staged binaries), but adds real per-build overhead (sampling cost) and needs careful handling of process trees that fork faster than the sampling interval.
2. **Parse `make`'s own `--trace`/`-d`/GNU Make's job-count debug output**, or `ninja -d stats`/`ninja -j`'s own build log (`.ninja_log` already has real per-target start/end timestamps!) - a much cheaper, cooperative approach *when* the underlying build system is one that already emits this kind of data (ninja's `.ninja_log` is real, already-structured, per-target timing - directly analogous to what `bga` already does for BuildStream's own log, one level down). Doesn't work for build systems that don't log this (plain recursive `make` has much weaker built-in introspection than ninja).
3. **`strace`/`perf` sampling** of the whole element's sandboxed process tree during "Running commands" - the most detailed data (real syscall/CPU-cycle level), but real overhead (strace can slow a build down significantly), real complexity (needs to run *inside* the bwrap sandbox, which may itself need `--cap-add` adjustments bwrap doesn't grant by default for tracing), and produces a much larger, harder-to-summarize data volume than options 1-2.
4. **A minimal, purpose-built "job accounting" wrapper**: replace `make`'s recipe shell (`SHELL := /path/to/wrapper.sh`, a real, standard Make mechanism) with a script that timestamps every recipe invocation - cheaper than full process-tree sampling (option 1), cooperative rather than adversarial, but only sees *recipe* boundaries, not real CPU occupancy during a recipe (a single `g++` invocation's own internal phases - parsing, optimization, codegen - stay invisible).

## What this tool would need to answer, concretely

- For a given element's "Running commands" span, real per-job (or per-recipe) start/end times, so genuine "is `make -jN` actually achieving N-way concurrency, or degrading to effectively serial partway through" questions have real answers (mirrors `bga`'s own occupancy/concurrency analysis, one level down inside a single element).
- Real CPU-time vs wall-clock-time per job, to distinguish "this job used its slot productively" from "this job was ready but stalled waiting for a CPU core" (the intra-element analogue of `bga`'s own `RESOURCE_WAIT`/`SCHEDULER_WAIT` categories).
- A real, empirical answer to "for *this specific* element, what's the actual CPU-core-count-aware optimal `max-jobs`, independent of what other elements are doing" - the input `UX-09`'s cross-element joint-optimization question needs but currently can't get.

## Out of Scope (this task - design only)

- Choosing between the four options above - each has real, different tradeoffs (overhead, coverage, implementation cost) that need a real prototype-and-measure pass, not an armchair decision.
- Any implementation - this is a brainstorm filed for a future session, per this session's own scope (real optimization-walkthrough work, not new tool-building).
- Integrating this tool's output into `bga`'s own report format - a real design question (a new report section? a separate companion tool, like `tools/bst_checkout_cost.py` already is for a different measurement?) to answer once the tool itself exists.

## Verification Log

Not applicable - this is a design brainstorm, not an implemented change. Filed 2026-08-15/16 following `UX-09`'s real, evidenced finding that `bga` currently has zero visibility inside a single element's native build system.
