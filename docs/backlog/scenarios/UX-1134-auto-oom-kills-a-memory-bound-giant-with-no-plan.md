# UX-1134: `--jobserver auto` with no plan widens a memory-bound giant into the OOM killer

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1132 | **Found by:** round 152's Graviton arms, `memgiant` leg (bga-bench runs 36597448095 and 36602046680) | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

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

## Out of Scope

Cgroup memory limits; swap policy.

## Acceptance Test

The `memgiant` Graviton leg's `autocap` arm completes at
`mem_lines 320000`, with its memory withholds counted in the notice.

## Outcome

Not started.
