# UX-1134: `--jobserver auto` with no plan widens a memory-bound giant into the OOM killer

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1132 | **Found by:** round 152's Graviton arms, `memgiant` leg (bga-bench runs 36597448095 and 36602046680) | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** owner:CodSpeed Graviton

**Guard:** test_the_pool_withholds_for_measured_rss_with_no_plan.py, test_the_auto_advice_names_its_memory_bound.py

## Motivation

The default bga prints (UX-1005) is the safe builder cap plus
`--jobserver auto`. On `16-memory-bound-giant` at `mem_lines 320000`,
16 Cortex-A72 cores and 31 GB, the `off` arm completes and the `autocap`
arm fails, twice:

```text
memgiant off | wall 560.83s cpu 3214s mem 21597M giant-peak 8 ... giant:373.5/8/7.9
autocap-1 failed | [00:04:53][de3c7ed1][build:giant.bst] FAILURE Command failed | oom: 15 kill(s),
  Out of memory: Killed process 7931 (cc1) total-vm:2981624kB, anon-rss:2673060kB
```

The pool's memory withholding reads a `--plan`'s `peak_rss_bytes`
(`tools/jobserver/pool.py`, `read_plan_peak_rss`); with no plan it
withholds nothing, and the PSI memory withdraw did not fire before the
kernel killed cc1 (12 jobs at ~2.7 GB each on 31 GB). The shape is the
one UX-1132 built to exercise the withdraw; the default turns a build
that completes into one that fails.

## Decomposition

surfaces: the pool's admission of a new token (`pool.py`), the recommendation text (`bga analyze`, UX-1005)
guards: a giant whose running jobs' RSS times one more would pass `MemAvailable` gets no new token with no plan; the recommendation does not advise `auto` unqualified when the capture's peak RSS per job times the widened width exceeds the host's memory
gap: whether per-job RSS can be read live (the tracer's own process table) fast enough to withhold before cc1 grows
track: before UX-1100

## Required Fix

With no plan, the pool withholds a token when the running jobs'
measured RSS per job, times one more job, exceeds `MemAvailable`; and
`bga analyze` qualifies its `auto` advice by the capture's memory.

## Decision

```text
Route:     with no plan, PoolController asks a new stdlib gate, tools/jobserver/memory.py, before each `+` it would add in `_handle_underload`. The gate holds the add while any running element has a live job bigger than every job of that element that has finished (its peak is still unknown). Otherwise it adds only when per_job x (pool + running elements + 1) <= MemAvailable + the live RSS the build already holds. Tokens already handed out are never revoked; the gate only withholds new ones.
  Why PSI missed: the controller's CPU-underload adds (pool.py:356-364) widened the pool while 12 cc1 kept busy below capacity-1; `Broker._memory_gate` returns early with no plan (pool.py:561) and no Broker exists without a slack plan (tracer:2497). The memory-PSI withdraw is a trailing avg10 and its non-blocking FIFO read finds the FIFO empty (make holds the tokens), recording `withdraw_held`.
  Numbers: finished peaks are the END lines' `maxrss_kb` per `element=`, read from the live trace.log from a saved offset. Live RSS is a host /proc/*/stat walk (ppid, rss) of the descendants of each running sandbox's host pid; the shim adds `"pid": os.getpid()` to its decision row (execv keeps it for bwrap). The gate reads only on ticks where an add is pending (<= one per 250 ms). At 31 GB and 2.7 GB/job the giant stops at 11 jobs.
  Advice: `compute_builder_pool_recommendation` takes `memory=` from `_peak_rss_and_host_memory` (cli.py:335): the largest per-process peak per element against host MemTotal. When peak x pool_size > host memory, a `memory_bound` entry; the Builders line becomes "... with --jobserver auto - memory-bound: giant.bst peaks 2.7 GB per job x 16 = 43.2 GB > 31 GB; auto withholds past 11 jobs, --jobserver 11 pins it".
Rejected:  live RSS alone at add time (cc1 is small at start); trace-log pids in host /proc (namespace pids under --unshare-pid); the median of finished jobs (sh/make-sized); a lower or faster PSI (stalls already happening, FIFO still empty); revoking or killing jobs; cgroup memory.max (Out of Scope).
Files:     A: tools/jobserver/memory.py (new), tools/jobserver/pool.py, tools/native_trace/bwrap_shim.py, tools/bst_native_build_tracer.py (trace_log/decisions paths into psi_paths), tools/jobserver/ledger.py (pool.memory.rss_withheld, counted from the ledger's `rss` rows, never stored), tests/quality_reference.json (dev_sizes --adopt --force)
           B: bga/correlate.py, bga/cli.py (_builder_pool_recommendation, _builder_pool_text_lines)
Guard:     A: tests/unit/test_the_pool_withholds_for_measured_rss_with_no_plan.py - real FIFO, scripted /proc root, scripted meminfo, real END lines; tick(busy_cores=low) holds with reason `rss ...` when per_job x (n+1) > avail + live, adds when it fits
           B: tests/unit/test_the_auto_advice_names_its_memory_bound.py - peak x pool_size > host memory gives the memory-bound line and its fit; under it the line is unchanged
Mutation:  A1 treat live_max > finished peak as settled -> red; A2 per_job = live max only -> red; B1 drop memory= (or flip >) -> red
Reading:   the Graviton memgiant autocap arm completes at mem_lines 320000 with rss_withheld > 0 in its notice; mixed8 autocap within its noise. The 4-core CI step cannot witness it (fits in memory; pool starts at ceiling-1 and never adds).
```

## Out of Scope

Cgroup memory limits; swap policy.

## Acceptance Test

The `memgiant` Graviton leg's `autocap` arm completes at
`mem_lines 320000`, with its memory withholds counted in the notice.

## Outcome

**Track A - the pool.** Gap measured: the new guard against base
`c6c6e4ed`'s `tools/jobserver/pool.py` (the gate absent):

```text
$ python3 -m pytest -n 0 tests/unit/test_the_pool_withholds_for_measured_rss_with_no_plan.py
E   assert ('add' == 'hold'        (settled giant, 2 GB x 6 > 8 GB + 0.5 GB)
E   assert ('add' == 'hold'        (live 1 GB cc1 > every finished 4 MB job)
2 failed, 1 passed
```

Close measured: the same file on this branch, `3 passed in 0.41s`; the
touching selection (`dev_touching.py --base c6c6e4ed --list`, 148 files,
plus the guard) `1 failed, 3457 passed, 62 skipped in 138.59s` - the one
red is `test_every_doc_path_a_help_string_names_exists` naming
`docs/audits/mutation.md`, an ignored record the worktree lacks. One
`withhold` on this host's `/proc` (129 entries): 0.99 ms mean of 20. The
Graviton notice, on a scripted report:
`pool dynamic idle 0.00 starved 0.00 admit None wait 0.0s rank None psiw 0 rssw 7`.

| mutation (tools/jobserver/memory.py) | reddened | run printed |
|---|---|---|
| A1 `if live_max[element] > finished_peak` -> `if False:` | `test_a_live_job_bigger_than_every_finished_one_holds` | 1 failed, 2 passed |
| A2 `per_job = max(live_max.values())` | `test_a_settled_giant_that_does_not_fit_gets_no_token` | 1 failed, 2 passed |
| reverted from the copy | - | 3 passed |

Track B (advice), `tests/unit/test_the_auto_advice_names_its_memory_bound.py`: with peak 2.7 GB, pool 16, host 31 GB the Builders line names the bound and `--jobserver 11`; at 1.9 GB or with no memory reading the line is unchanged.

| Mutation (B1) | Result |
|---|---|
| `>` flipped to `<` in `peak * pool_size > host_memory` | 2 failed, 2 passed |
| `memory=` dropped | 1 failed, 3 passed |
| `>` relaxed to `>=` | 1 failed, 3 passed (exactly host memory) |
| revert | 4 passed |
