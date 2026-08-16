# UX-21: oversubscription guard has no memory/swap dimension - only CPU

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-12`, `UX-16`

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

## Fix Implemented

Took Required Fix item 1's "minimum, config-driven guard" - two new purely operator-declared `RunContext` fields, `memory_budget_mb` and `estimated_job_memory_mb` (no host-memory auto-detection tier at all, deliberately scoped out - unlike `cpu_budget`'s `host_cpu_count` counterpart, since there's no existing memory-measurement foundation to build on here). Wired through both producer tools via `tools/_run_context_common.py`'s new `add_memory_capacity_fields()` (the same shared-helper pattern `UX-18` established for the CPU-side fields, applied from the start here so this doesn't silently diverge between the two producers the way the CPU fields once did) - `--memory-budget-mb`/`--estimated-job-memory-mb` CLI flags on both `tools/bst_extract_run.py` and `tools/bst_run_context.py`.

`bga/analyzer.py`'s new `_check_memory_oversubscription` (called alongside `_check_process_oversubscription` in `analyze()`) computes `builders x native_max_jobs x estimated_job_memory_mb` and compares it against `memory_budget_mb`, reporting a new `memory_oversubscription` violation when it's exceeded - resolved per Required Fix item 3: **a genuinely separate violation type**, not folded into `resource_oversubscription`, since the two dimensions are independent failure modes (confirmed by a real test where a config is CPU-oversubscribed but memory-fine, and vice versa, and each check fires only its own violation). Reuses `UX-16`'s own `--max-jobs=0` auto-sentinel resolution (via the governing CPU-core count, `cpu_budget` or `host_cpu_count`) rather than treating the literal `0` as "no parallelism," which would silently understate real memory demand - the exact class of bug `UX-16` fixed for the CPU check. All four inputs (`builders`, `native_max_jobs`, `memory_budget_mb`, `estimated_job_memory_mb`) are best-effort/optional - the check only runs when all are present. `bga/report/text.py` labels the estimate explicitly as "config-driven estimate, not a real measurement" in the human-readable violation summary.

## Verification Log

Done for real, 2026-08-16. New `tests/unit/test_memory_oversubscription.py` (8 tests): a real plausible C++ LTO scenario (`builders=8, native_max_jobs=8, ~1000MB/job` vs an 8000MB budget) fires `memory_oversubscription` with the correct numbers; within-budget is not flagged; CPU-oversubscribed-but-memory-fine and memory-oversubscribed-but-CPU-fine each fire only their own violation type (Acceptance Test #2); the check is skipped when either declared input is absent, even with an extreme `builders x native_max_jobs`; the `--max-jobs=0` sentinel resolves correctly (mirroring `UX-16`) and is skipped (not silently treated as zero demand) when no governing core count is available to resolve it against; the report text names the estimate as config-driven, not measured (Acceptance Test #3). New tests in `tests/unit/test_run_context_common.py` (3 tests) and `tests/unit/test_bst_run_context.py` (1 test) cover the shared helper and CLI flag capture.

Full suite green: 538 passed (up from 526 - 12 new tests), same 7 pre-existing environment-only failures as `main`. `make lint` clean.

Real end-to-end re-verification against `examples/04-critical-path-optimization/optimized`, built fresh with real BuildStream 2.7.0 and extracted with `tools/bst_extract_run.py --native-max-jobs 8 --memory-budget-mb 4000 --estimated-job-memory-mb 1500` (builders=4, so estimated demand = 4 x 8 x 1500 = 48000MB vs a 4000MB budget):

```
memory_oversubscription violation: {'builders': 4, 'native_max_jobs': 8, 'estimated_job_memory_mb': 1500,
  'estimated_demand_mb': 48000, 'memory_budget_mb': 4000, ...}
```

`--format text` output: `"estimated memory oversubscription: builders=4 x native max-jobs=8 x ~1500MB/job (config-driven estimate, not a real measurement) = ~48000MB vs a declared memory budget of 4000MB - risk of swap, a qualitatively worse failure mode than CPU contention, see UX-21"` (Acceptance Test #1 and #3, real numbers, real run).
