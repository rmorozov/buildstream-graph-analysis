# UX-15: a declared CPU budget must govern `bga`'s capacity checks over raw host detection

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-12`

## Motivation

Raised directly by the user after `UX-12`/`UX-13` shipped: `bga`'s oversubscription check (`UX-12`) compares declared concurrency demand against `host_cpu_count`, a value *detected* from the execution environment (`os.sched_getaffinity`, falling back to `os.cpu_count()`). The user's proposal: a `bga` user may deliberately want the tool's analysis to respect their *own* declared CPU budget - the number of cores they intend a build to use - rather than raw hardware detection, and the tool's "whole optimization process" should honor that.

Asked to evaluate this with real facts before implementing. Two real, independent lines of evidence support it - one stronger than mere preference:

1. **cgroup CPU limiting has two independent mechanisms, and `bga` only detects one.** `cpuset.cpus` restricts *which* cores a process may run on - `os.sched_getaffinity()` reads this. But CFS bandwidth control (`cpu.max` in cgroup v2; `cpu.cfs_quota_us`/`cpu.cfs_period_us` in cgroup v1 - what `docker run --cpus=N` and Kubernetes `resources.limits.cpu` actually configure) limits CPU *time*, not core *identity*. A container with a 2.5-CPU quota typically keeps full affinity to every host core - `os.sched_getaffinity()` on that container returns the host's full core count, not the quota. Quota-based limiting is the more common mechanism in Docker/Kubernetes/most hosted CI (including GitHub Actions runners) - cpuset pinning is the exception. `UX-12`'s own docstring claim ("`os.sched_getaffinity`... correct under a cgroup/container CPU-share limit") is only true for the cpuset case - a real, previously-uncaught gap in what had just shipped.
2. **`bga`'s own architecture already treats capacity as declared, not detected, everywhere else** - `resource_capacities.PROCESS`/`DOWNLOAD`/`UPLOAD` (`builders`/`fetchers`/`pushers`) are all user/BuildStream-configured values, not auto-detected. A declared CPU budget is architecturally consistent with this existing pattern, not a special case.

A real caution, not a rebuttal: silently replacing the detected value with a declared one would defeat exactly what `UX-09`/`UX-12` were built to catch (real physical contention happening regardless of operator belief). The resolution: keep both values, always. `cpu_budget` (when declared) governs the analysis, since it reflects operator intent; `host_cpu_count` (when detected) stays recorded for transparency; and a mismatch between the two (a declared budget bigger than what the environment can actually provide) is itself a new, real, honestly-surfaced signal - not silently discarded.

## Fix Implemented

1. **`bga/ingest/models.py`/`loader.py`**: new `RunContext.cpu_budget: Optional[int]`, parsed from a new `cpu_budget` run-context.json field.
2. **`tools/bst_extract_run.py`**: new `--cpu-budget INT` CLI flag - purely operator-supplied, no detection path (there's nothing to detect; it's a declaration of intent). Not folded into the run-identity manifest (like `host_cpu_count`, it's a policy/environment property, not something that changes what was actually built).
3. **`bga/analyzer.py`, `_check_process_oversubscription`**: computes a `governing_cores` value - `cpu_budget` when present, `host_cpu_count` otherwise - and uses *that* (not the raw detected value) for both the oversubscription default-demand comparison and the undersubscription check. Every violation records `governing_cores`, `capacity_source` (`'declared_cpu_budget'` or `'detected_host_cpu_count'`), and both `host_cpu_count`/`cpu_budget` (whichever are known) - full transparency, nothing silently discarded. A new `cpu_budget_exceeds_host_capacity` violation fires when a declared budget exceeds the detected host capacity - the budget itself being unrealistic is a real, distinct signal.
4. **`bga/report/text.py`**: violation/caveat text names the real governing source accurately (`"a declared CPU budget of N cores"` vs. `"an N-core host"`) rather than always implying real hardware.
5. **`bga/analyzer.py`, `_build_capacity_model_note` (`UX-13`)**: the Certified Floors caveat's enriched form also names the declared budget, not the host, when that's what governed.

## Out of Scope

- Per-element `cpu_budget` overrides - a single global declared value, mirroring `UX-12`'s own scoping decision for `native_max_jobs`.
- Using `cpu_budget` anywhere in `LB`'s own math (`bga/floors/capacity.py`) - `LB`'s `PROCESS` capacity is about BuildStream's own dispatch-slot dimension (`builders`), a different, orthogonal concept from real/declared CPU cores - conflating them was exactly the confusion `UX-13` clarified. `cpu_budget` only feeds the oversubscription check, not `LB`.
- Clamping `bga sweep`'s default capacity range to `cpu_budget` - `UX-14`'s own scope is a caveat, not a change to what capacities get swept; a user can already bound the range manually with `--max-capacity`.

## Acceptance Test

1. A run with `native_max_jobs`/`host_cpu_count` that would *not* be flagged on raw host detection alone is flagged once a smaller declared `cpu_budget` is present, and vice versa.
2. A declared `cpu_budget` exceeding the detected `host_cpu_count` produces its own `cpu_budget_exceeds_host_capacity` violation.
3. The Certified Floors report note (`UX-13`) names the declared budget, not the host, when a budget governed the check.
4. Full suite green.

## Verification Log

Done for real, 2026-08-15. New tests: `tests/unit/test_cpu_budget.py` (6 tests - a declared budget governs instead of the detected host count in both directions, absence falls back to detected `host_cpu_count`, a budget exceeding host capacity is itself flagged, a budget within host capacity is not, and the Certified Floors note names the budget accurately). Full suite green (`make lint`, `pytest` - 490 passed, same 7 pre-existing environment-only failures as `main`).

Real re-verification against `UX-09`'s own `examples/05-cmake-cpp-toolchain` `8×8` build log (real 4-core host): `bst_extract_run.py --native-max-jobs 8 --cpu-budget 4` correctly captured all three fields (`native_max_jobs=8`, `host_cpu_count=4`, `cpu_budget=4`). Re-running `bga analyze` after editing the captured `run-context.json`'s `cpu_budget` to `2` tightened the oversubscription violation's `default_demand` from `16` to `8` and the Certified Floors note switched to `"vs your declared CPU budget of 2 cores"` - confirming the declared value, not the detected one, drives the comparison. Setting `cpu_budget` to `16` (exceeding the real 4-core host) produced both violations simultaneously: `cpu_budget_exceeds_host_capacity` (budget=16, host_cpu_count=4) and `resource_oversubscription` (governed by the declared 16, not the real 4).
