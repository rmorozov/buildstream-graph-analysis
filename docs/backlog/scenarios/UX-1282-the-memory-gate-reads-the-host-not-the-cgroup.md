# UX-1282: the memory gate reads the host's memory, not the cgroup a container agent is capped at

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's question on round 166 (2026-10-02): "is it generally safe to use the jobserver on an arbitrary configuration?" | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** owner:CodSpeed Graviton

**Guard:** `tests/unit/test_the_memory_gate_reads_the_cgroup.py`, `tests/unit/test_memory_joins_the_sweep.py::test_the_advice_reads_the_cgroup_cap_when_it_is_below_the_host`

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

## Decision

```text
Route:     one stdlib reader read_build_memory(meminfo, cgroup_root, self_cgroup) -> (bytes, bound_by) in tools/jobserver/memory.py returns the lower of MemAvailable and the tightest limit-minus-usage over the tracer's own cgroup path (/proc/self/cgroup) and every ancestor - v2 memory.max/memory.current ("max" = none), v1 memory.limit_in_bytes/usage_in_bytes; it replaces read_mem_available_bytes at both call sites (PoolController lambda pool.py:303-310, Broker.tick pool.py:727), the cgroup root parameterised like psi_paths["meminfo"]; the tracer's host-samples header records mem_limit_kb and mem_bound_by, and _peak_rss_and_host_memory (bga/cli.py:357) uses min(mem_total_kb, mem_limit_kb).
Rejected:  patching only MemoryGate - Broker:727 reads the same host figure; an operator limit flag - declared, not measured; reading the cgroup at analyze time - reads the analysing host; leaf-only check - misses a tighter parent (Kubernetes pod nesting); psutil - hook side is stdlib only.
Files:     tools/jobserver/memory.py, tools/jobserver/pool.py, tools/bst_native_build_tracer.py (header ~:972, read_host_sample ~:899), bga/cli.py (:357-374), bga/disclosure.py (:421 key list, 2 new header keys classed "H"), tests/unit/test_the_memory_gate_reads_the_cgroup.py (new).
Guard:     tests/unit/test_the_memory_gate_reads_the_cgroup.py - scripted /sys/fs/cgroup fixture per input class: (a) no cgroup → MemAvailable, "meminfo"; (b) v2 max → MemAvailable; (c) v2 limit below MemTotal at leaf or parent → limit-current, "cgroup", and MemoryGate.withhold holds where meminfo-only grants; (d) v1 → limit-usage; (e) _peak_rss_and_host_memory returns the limit when header mem_limit_kb < mem_total_kb.
Mutation:  drop the min → (c),(d) red; stop ancestor walk at leaf → (c) parent red; cli back to mem_total_kb → (e) red.
Class:     product
Split:     one track, parallel with 1283/1284/1310/1314; the gate keeps Callable[[], Optional[int]].
Owner reading: memgiant under a 20 GB cgroup cap on Graviton (needs Ruslan's word to push to bga-bench); Reading stays owner:CodSpeed Graviton.
Question:  none
```

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

**Gap measured.** This container's memory cgroup is v1, capped at its
leaf (`/proc/self/cgroup` line `4:memory:/process_api/.../claude-code-bash`):

```text
$ cat .../claude-code-bash/memory.limit_in_bytes   14345031680   (parents: 9223372036854771712)
$ grep -E "MemTotal|MemAvailable" /proc/meminfo     16480968 kB / 15793204 kB
```

The old reader gave the gate the host's MemAvailable; the build could
use 14.35 GB minus what the cgroup already held.

**Close measured.** Headroom is limit minus the kubelet's working set:
usage less `inactive_file` (v2) / `total_inactive_file` (v1) from the
same cgroup's `memory.stat`, clamped at 0, plain usage when the stat is
missing. A real v1 child cgroup capped at 2 GiB (`mkdir` under the leaf,
`memory.limit_in_bytes` = 2147483648, the reading process moved in,
512 MiB ballast held), scratchpad `capped.py`:

```text
before: (11789062144, 'cgroup') 14345031680 meminfo-only 15926239232
4:memory:/process_api/01a11558-3716-757c-8450-2ef6c40f4692/claude-code-bash/ux1282
capped 2GiB, 512MiB ballast: (1609306112, 'cgroup') 2147483648 meminfo-only 15375335424
leaf: usage_in_bytes 3914866688, total_inactive_file 1367068672
```

`read_build_memory` 1.61 GB, `bound_by` "cgroup", against MemAvailable's
15.38 GB. At the leaf the page cache is 1.37 GB that limit-minus-usage
would have counted as spent. The tracer's header here reads
`{'mem_limit_kb': 14008820, 'mem_bound_by': 'cgroup'}` (MemTotal 16480968).
No v2 memory controller in this container, so v2 is the scripted
guard's alone.

**Graviton reading** (bga-bench run 37616908079, job 112777350313): the
`memcap` leg, memgiant's `autocap` arm inside a v2 cgroup at
`memory.max` 20 GB (`0::/bga-cap max 21474836480`), rung sized to the cap
(`mem_lines 240000`). The gate reads the cgroup, holds every add, and all
three builds complete with no OOM:

```text
autocap-1  wall 415.05 s  mem 16274M  peak 8  start 7 max 7 adds 0 rss-holds 933  cgroup peak 17736M oom_kill 0
autocap-2  wall 413.50 s  mem 16285M  peak 8  start 7 max 7 adds 0 rss-holds 937  cgroup peak 17955M oom_kill 0
autocap-3  wall 413.34 s  mem 16143M  peak 8  start 7 max 7 adds 0 rss-holds 920  cgroup peak 17955M oom_kill 0
```

At `mem_lines 320000` (run 37606960927) the opening width alone overran
the cap (OOM, `adds 0`, `withdraws 0`); filed as UX-1339.

**Mutation table** (18 tests over both guard files, scratchpad `mutate.py`,
reverted from a copy; reverted run `18 passed`):

| mutation | run | reddened |
|---|---|---|
| ignore `memory.stat` (`return usage`) | 2 failed, 16 passed | page cache is headroom, v1 |
| v1 reads `inactive_file`, not `total_inactive_file` | 1 failed, 17 passed | v1 |
| drop the min (`if False:`) | 6 failed, 12 passed | v2 leaf, v2 parent, page cache, v1, gate holds, pool+broker |
| ancestor walk stops at the leaf | 3 failed, 15 passed | v2 parent, gate holds, pool+broker |
| cli back to `mem_total_kb` | 1 failed, 17 passed | advice reads the cap |
| `Broker.tick` back to `read_mem_available_bytes` | 1 failed, 17 passed | pool+broker |
| `PoolController` lambda back to `read_mem_available_bytes` | 1 failed, 17 passed | pool+broker |

**Deviation.** Disclosure classes `mem_limit_kb` "C" (a measurement, as
`mem_total_kb`) and `mem_bound_by` "B" over `{meminfo, cgroup}`, not the
Decision's "H", which is time shifted to epoch 0. Caveat: on a hybrid
host the v2 tree at `/sys/fs/cgroup/unified` is not read (only
`<root>/memory.max`); the v1 memory controller, where hybrid hosts put
memory, still is.
