# UX-850: memory is a second resource the pool reads

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-845, UX-849 | **Found by:** round 117, Direction 20 | **Serves:** R5 (a machine that overcommitted memory before) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

A token is a core; nothing in the protocol says bytes. `UX-678` put
memory in the sweep and `max_jobs_advice` refuses a row whose overlap
peak RSS exceeds the host's memory - after the fact. Under the mode
the server knows each element's peak RSS from the plan before its build
starts and the host's free memory now.

## Required Fix

`tools/bst_native_build_tracer.py`: before the broker grants a
proxy's first token beyond the implicit one, it checks free memory
(`/proc/meminfo` `MemAvailable`) against the element's planned peak
RSS times the tokens it would hold; below that it withholds, recorded
as `memory_withheld` in the ledger; where `/proc/pressure/memory`
exists, `some avg10` above a bound reads tokens back from the pool the
way `UX-845`'s CPU bound does.

## Decomposition

Input classes: a plan with peak RSS, a plan without (no withholding),
PSI present and absent, an element whose peak exceeds the machine
(one implicit token only); the journey it extends is R5's "does this
machine fit this build" question.

## Out of Scope

Swap accounting and cgroup limits - declined until a capture shows
them binding.

## Acceptance Test

`tests/unit/test_the_pool_withholds_for_memory.py` drives the broker
with a scripted `MemAvailable` series and a plan; mutation: ignore the
plan's peak - red.

## Outcome

**Gap measured.** `git show 7a2c08cd:tools/bst_native_build_tracer.py |
grep -c "memory_withheld\|psi_memory\|JOBSERVER_POOL_MEMORY_PSI_BOUND\|
read_mem_available"` = 0 - nothing compared `MemAvailable` (already
sampled by `HostSampler` every 2s) against any element's planned peak
RSS, and `PoolController` read only `/proc/pressure/cpu`.

**Close measured.**
`python3 -m pytest tests/unit/test_the_pool_withholds_for_memory.py -v`:

```text
TestTheBrokerWithholdsByPlannedPeak::test_below_the_bound_withholds PASSED
TestTheBrokerWithholdsByPlannedPeak::test_above_the_bound_grants PASSED
TestTheBrokerWithholdsByPlannedPeak::test_a_plan_without_peak_rss_withholds_nothing PASSED
TestTheBrokerWithholdsByPlannedPeak::test_a_peak_that_alone_exceeds_the_machine_grants_nothing PASSED
TestTheBrokerWithholdsByPlannedPeak::test_memory_returning_grants_a_previously_withheld_element PASSED
TestThePoolReadsMemoryPSI::test_absent_does_nothing PASSED
TestThePoolReadsMemoryPSI::test_present_under_the_bound_does_nothing PASSED
TestThePoolReadsMemoryPSI::test_present_over_the_bound_withdraws PASSED
test_count_memory_psi_withdraws_reads_the_shared_ledger PASSED
9 passed in 0.78s
```

`test_the_broker_grants_by_slack.py` (7), `test_the_pool_follows_the_
machine.py` (11, two lines updated for `PoolController`'s own arg-count
cap - `psi_path` folded into `psi_paths`) all green; `dev_baseline.py
--check` clean (one new `PLR0913` avoided by the same `scratch`/dict-
bundling convention `Broker` already used, not forced); `dev_sizes.py
--check` clean after `--adopt --force` (`longest_function` 498->511,
`file_lines` 8192->8329 - `tests/quality_reference.json` in this
commit); `ruff check bga/ tools/ tests/ .claude/hooks/` and `make
lint`: `All checks passed!`.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `_memory_gate`: `if True: return grant_n` (ignore the plan's peak) | below-bound, peak-exceeds-machine, memory-returning | 3/9 red |
| `PoolController.tick`: `psi_mem_over = False` (drop the memory-PSI branch) | present-over-the-bound withdraw | 1/9 red |

Reverted from the pre-mutation copy (never `git checkout --`); both
green again after.

**BGA_SKIP_SELECTOR=1**, this commit only. The pre-commit selector runs
`tests/unit/test_sandbox_stderr_and_replay.py::TestTheDefaultPathStill
Execs::test_the_shim_only_tees_under_diagnose` red - `main()` in
`tools/native_trace/bwrap_shim.py` now calls a split-out `_exec_or_run`
rather than naming `run_teed` in its own source, which the guard reads
literally (`inspect.getsource`). `git show 7a2c08cd:tools/native_trace/
bwrap_shim.py` has the identical split already - pre-existing at this
item's own base commit, in a file this diff never touches.

Deviation (merge): `psi_path` became `psi_paths` (cpu, memory) under
the argument cap, and every pinned guard on the round branch now pins
both files - CI's runner has `/proc/pressure/memory` too; the guide's
prose for `jobserver_pool.memory` was added at merge; an unreadable
`/proc/meminfo` grants (fails open), a withheld element writes one row
per tick, and the gate is per element - two elements each under the
bound can jointly exceed the host, noted for a later row.
