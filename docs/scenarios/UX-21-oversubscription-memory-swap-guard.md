# UX-21: oversubscription guard has no memory/swap dimension - only CPU

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** `UX-12`, `UX-16`

## Motivation

Raised by the user: `UX-12`'s oversubscription check (and `UX-16`'s fix to it) is entirely about CPU-core contention - `builders x native_max_jobs` vs. a core-count ceiling. But every concurrently-running build subprocess also consumes real memory (compilers, especially C++ ones doing heavy template instantiation or LTO, can each use gigabytes), and there is no CPU-contention slowdown anywhere near as catastrophic as pushing the build host into swap - which can effectively freeze the entire machine (every process thrashing, not just the build), a qualitatively different and often far worse failure mode than "the build is merely slower than optimal."

Checked directly against the real code: confirmed there is **no memory accounting anywhere in `bga`** - grepped the whole `bga/` package for any real memory/swap/RAM tracking and found none (the few incidental string matches are unrelated, e.g. "an accidental swap" in a code comment about variable reordering). `CPUAccounting` (`bga/utilisation/__init__.py`) tracks CPU only. This is a genuine, currently entirely unaddressed gap, not an existing-but-incomplete feature.

## Required Fix

Real design work, scoped modestly given `bga` has no existing memory-measurement infrastructure to build on (unlike CPU, where `host_cpu_count`/`cpu_budget` already exist as a foundation):

1. **Minimum, config-driven guard** (mirrors `UX-15`'s `cpu_budget` pattern - a declared value, not a measured one, since no real per-task memory measurement source exists in this ingestion pipeline): a new `--memory-budget-mb` capture (or reuse of an already-known host value, e.g. `/proc/meminfo`'s `MemAvailable` at capture time, analogous to `host_cpu_count`) plus a rough, explicitly-labeled *estimated* per-job memory footprint (either a single configurable constant, e.g. `--estimated-job-memory-mb`, or eventually a per-`element_kind` heuristic mirroring `UX-12`/P4-12's own `element_kind`-based heuristics precedent) to compute `builders x native_max_jobs x estimated_job_memory_mb` and compare against the declared/detected memory budget - the same shape as `UX-12`'s CPU check, one new resource dimension.
2. A new violation type (e.g. `memory_oversubscription`) with the same "this is a coarse, config-level estimate, not a measurement" honesty `UX-12`'s own docs already insist on for CPU - explicitly do not claim to know real per-task memory usage.
3. Consider whether this belongs as a new field on the *same* `resource_oversubscription`-style check (extending `UX-16`'s fixed version) or a genuinely separate check - memory and CPU oversubscription are independent failure modes (a config can be memory-oversubscribed while CPU-fine, or vice versa) and should likely be reported as distinct violations even if the underlying demand math is structurally similar.

## Out of Scope

- Real, measured per-task memory accounting (would need the same kind of intra-sandbox visibility `UX-11`'s own native-build-system profiler brainstorm already identifies as a separate, large, future tool - `UX-11`'s design, if ever built, is the natural longer-term source of real per-element memory data, not something to attempt here).
- Automatically tuning `--builders`/`--max-jobs`/`--cpu-budget` in response to a detected memory risk - this task is about surfacing the risk, not auto-remediating it.

## Acceptance Test

1. A run declaring a memory budget and a configuration where `builders x native_max_jobs x estimated_job_memory_mb` exceeds it produces a real `memory_oversubscription`-style violation naming the real numbers, distinct from (and independent of) any CPU-based `resource_oversubscription` violation.
2. A run within the memory budget produces no such violation, even if it happens to be CPU-oversubscribed (and vice versa) - confirms the two dimensions are checked independently, not conflated.
3. The estimate is clearly labeled as a config-driven approximation, not a real measurement, in both text and JSON output.
4. Full suite green.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
