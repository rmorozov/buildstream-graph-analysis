# UX-1282: the memory gate reads the host's memory, not the cgroup a container agent is capped at

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's question on round 166 (2026-10-02): "is it generally safe to use the jobserver on an arbitrary configuration?" | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

## Motivation

UX-1134's gate holds a token when per-job peak x (jobs + 1) exceeds
`MemAvailable` plus the live RSS the build already holds.
`read_mem_available_bytes` (`tools/jobserver/pool.py:158`) reads
`/proc/meminfo`, which reports the host. A build agent in Kubernetes
or Docker with a `memory.max` below the host's RAM gets the host's
figure. The gate then sees memory the container cannot use, and the
cgroup's OOM killer fires where the gate meant to hold. The advice
side does the same: `_peak_rss_and_host_memory` (`bga/cli.py:355`)
compares peak RSS against the host's memory, not the cgroup's. This
is inferred from the code, not measured on a capped agent.

The Graviton reading (runs 37022814276, 37031346135) was bare metal
with no cgroup cap, so it cannot tell the two apart.

## Decomposition

Input classes: no cgroup (bare metal); cgroup v2 with `memory.max` =
`max`; cgroup v2 with `memory.max` below MemTotal; cgroup v1
`memory.limit_in_bytes`. Journey: the `auto` capture on a capped
agent, and `bga analyze`'s Builders line.

## Required Fix

Both sides read the memory the build can actually use: the lower of
`MemAvailable` and the build cgroup's limit minus its `memory.current`
(v2; v1's `limit_in_bytes` and `usage_in_bytes`), and the lower of
MemTotal and the limit for the advice. The capture records which one
bound it.

## Out of Scope

Setting cgroup limits from bga; swap policy.

## Acceptance Test

The memgiant Graviton leg run inside a cgroup capped at 20 GB: the
`autocap` arm completes with memory holds counted and its peak width
below the uncapped run's 10. A scripted guard per input class.

## Outcome
