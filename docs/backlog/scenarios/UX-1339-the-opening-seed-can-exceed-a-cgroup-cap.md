# UX-1339: the pool's opening width can exceed a cgroup cap, and nothing takes tokens back

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1282, UX-1283 | **Found by:** round 171's `memcap` Graviton leg (bga-bench run 37606960927, job 112744687340, 2026-10-07) | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

## Motivation

memgiant at `mem_lines 320000` (sized from the host's 31 GB) run inside a
20 GB cgroup under `--jobserver auto --builders 8`:

```text
memcap        | 0::/bga-cap max 21474836480
autocap-1 pool | start 7 max 7 ticks 1087 adds 0 rss-holds 182 idle-holds 903 withdraws 0
autocap-1 failed | [00:04:35] build:giant.bst FAILURE Running commands | oom: 3 kill(s),
               Memory cgroup out of memory: Killed process 5950 (cc1) anon-rss:2679800kB
```

UX-1282's gate read the cgroup and held every add (182 `rss` holds, 0
adds), but the pool opened at 7 tokens (UX-1283's bst max-jobs - 1), so
make ran 8 cc1 at ~2.7 GB each, about 21.4 GB against a 20 GB cap. Holding
adds cannot help when the opening width is already over the cap; no
withdraw fired (`withdraws 0`), because the PSI withdraw reads the
host's `/proc/pressure/memory`, not the cgroup's `memory.pressure`
(`_PSI_MEMORY_PATH`, `tools/jobserver/pool.py:37`).

## Decomposition

Input classes: an opening width whose jobs fit the cap; one that does
not, with a per-job size known only after the first END lines; a cap
with headroom gone mid-build. Journey: the `memcap` leg at 320000 lines.

## Required Fix

Open: when the jobs bst's max-jobs would run cannot fit the build's
memory, take back unread tokens. Candidates are withdrawing on the
cgroup's own `memory.pressure` / `memory.events` `high`, or a withdraw
when headroom goes negative with tokens still unread in the FIFO.

## Out of Scope

Killing or pausing jobs already running.

## Acceptance Test

The `memcap` leg at `mem_lines 320000` under a 20 GB cap completes
under `auto`.

## Outcome
