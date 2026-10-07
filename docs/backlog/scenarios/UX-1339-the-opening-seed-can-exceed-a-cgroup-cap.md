# UX-1339: the pool's opening width can exceed a cgroup cap, and nothing takes tokens back

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1282, UX-1283 | **Found by:** round 171's `memcap` Graviton leg (bga-bench run 37606960927, job 112744687340, 2026-10-07) | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** owner:CodSpeed Graviton

**Guard:** tests/unit/test_the_opening_seed_scales_to_a_cgroup_cap.py

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

## Decision

```text
Route:     the opening seed: under auto with no plan, opening_seed scales by share = min(1, cgroup limit / MemTotal) and opens at max(0, floor(max_jobs x share) - 1) (Graviton 8 x 20/31 -> seed 4); MemoryGate widens from there. Plus a headroom-negative withdraw from the gate's own reader: MemoryGate.over(pool) when per_job x (pool + live + MEMORY_RESERVE_JOBS) > available + live_total, and a tick reads one unread token back.
Rejected:  cgroup memory.pressure PSI - avg10 lags 10 s, a swapless cgroup OOM-kills on a failed charge without a stall, and 37606960927 had 0 idle tokens to take back.
Rejected:  a withdraw alone - make reads every seed token in wave 1, before any cc1 has a size; pausing is Out of Scope.
Rejected:  opening at 0 or 1 under a cap - throws away wave-1 width on every capped run.
Rejected:  a per-job estimate at open - the first build has none; --plan already is that cache.
Rejected:  a share from read_build_memory headroom - it moves with bst's startup memory.
Files:     tools/jobserver/pool.py, tools/jobserver/memory.py, tools/bst_native_build_tracer.py (seed_bound gains "cgroup"), tests/unit/test_the_opening_seed_scales_to_a_cgroup_cap.py
Guard:     tests/unit/test_the_opening_seed_scales_to_a_cgroup_cap.py - scripted v2 tree 20 GiB of 31 with max_jobs 8 opens at 4, no cap at 7, typed/n/plan unchanged; an over-width tick with 2 unread tokens reads one back, none when it fits or none are unread
Mutation:  opening_seed ignores the share (seed 7); delete the over-width withdraw branch; drop + MEMORY_RESERVE_JOBS from over - each reddens
Class:     product
```

## Required Fix

Open: when the jobs bst's max-jobs would run cannot fit the build's
memory, take back unread tokens. Candidates are withdrawing on the
cgroup's own `memory.pressure` / `memory.events` `high`, or a withdraw
when headroom goes negative with tokens still unread in the FIFO.

## Out of Scope

Killing or pausing jobs already running.

## Acceptance Test

The `memcap` leg at `mem_lines 320000` under a 20 GB cap completes
under `auto` 3/3 with `oom_kill 0`, the pool line at `start 4` and the
gate widening from there. 8 cc1 at 2.68 GB is 20.4 GiB, over the cap
however tokens move, so the pass comes from the opening, not a withdraw.

## Outcome

**Gap measured** (pre-fix, mutation 1 below: `capped_width` without the
share, a scripted v2 tree at 20 GiB of 31 GiB, max-jobs 8):
`opening_seed(15, 8, "auto", False)` (no share) returned 7, the seed that
ran 8 cc1 against the cap in run 37606960927; no tick withdrew at pool 8
(`withdraws 0`).

**Close measured** (`pytest tests/unit/test_the_opening_seed_scales_to_a_cgroup_cap.py`):
8 passed. `opening_seed(15, capped_width(8, 20/31), "auto", False)` returns 4; no cap and `typed`/`n`/plan stay 7/15/15/15.
An over-width tick (pool 8, 2 GiB per job, 19.5 GiB available) with 2 unread
tokens reads one back (pool 7, `memory_rss_withdraws 1`), none when it fits
or none are unread. `seed_bound` is `cgroup` when the share binds (added to
`bga/disclosure.py`, `bga/schemas.py`, `docs/guides/json-contracts.md`).

| Mutation | Reddened | Count |
|---|---|---|
| `capped_width` ignores the share (seed 7) | opens-at-four, main-names-the-cgroup | 2 failed, 4 passed |
| the over-width withdraw branch disabled in `tick` | reads-one-back | 1 failed, 5 passed |
| `over` drops `+ MEMORY_RESERVE_JOBS` | reads-one-back, fits-or-none-unread, reserve-jobs | 3 failed, 3 passed |
| `opening_share` reads the leaf cap only | tightest-cap-over-ancestors | 1 failed, 7 passed |
| the withdraw runs on any tick, not only a `hold` | add-not-relabelled | 1 failed, 7 passed |

**Acceptance (Graviton `memcap` leg, `start 4`, 3/3, `oom_kill 0`):** pending the session's run.

Deviation: the share lives in `capped_width` (pool.py), not an `opening_seed` argument (a sixth parameter trips PLR0913, a baselined family); the over-width withdraw is `_withdraw_over_width` (tick hit C901). Also `tests/unit/test_the_auto_seed_opens_at_bsts_own_max_jobs.py`
pinning `tracer.opening_share` so the container's own cgroup does not leak in.

Deviation: the over-width withdraw cannot fire before the first END line (an unsettled live element makes `over()` False), so the opening seed carries the memcap acceptance alone. `memory_rss_withdraws` reaches no report field; the pool line counts it with the PSI withdraws. The withdraw runs only on a tick that took no other action (`action == "hold"`).
