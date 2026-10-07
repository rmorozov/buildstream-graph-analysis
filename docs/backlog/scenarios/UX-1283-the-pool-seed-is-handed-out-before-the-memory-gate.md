# UX-1283: the pool's seed tokens are handed out before the memory gate has a say

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's promotion question on round 166 (2026-10-02): what stands between `auto` and arbitrary configurations | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** owner:CodSpeed Graviton

**Guard:** `tests/unit/test_the_auto_seed_opens_at_bsts_own_max_jobs.py`

## Motivation

`bga capture run --jobserver auto --builders B` seeds the pool at
`min(cores - 1, cores - B)` (`bga/cli.py` `_translate_capture_jobserver`).
The tracer writes those tokens into the FIFO at start, and UX-1134's
gate only governs a `+` added after that. On memgiant at 8 builders
the seed is 8, so the giant opened at 9 jobs against `off`'s 8
(run 37031346135: `giant-peak 10`, 26.9 GB of 31 GB). The seed is
sized by cores alone. Two memory-heavy elements starting together
each draw from it unchecked; `pairs`/`cap3` pass no `--builders`, so
their seed is 15 on 16 cores. Unmeasured; inferred from the code.

## Decomposition

Input classes: one memory-heavy element at seed 8; two at once;
`--builders` absent (seed `cores - 1`); a host whose memory fits the
seed. Journey: the `auto` capture's first minute.

## Decision

```text
Route:     under `auto` with no plan and project_max_jobs read, the FIFO opens at min(cli seed, project_max_jobs - 1) - bst's own `off` width for one element - via a pure opening_seed(seed, project_max_jobs, mode, planned) in tools/jobserver/pool.py, called in the tracer right after read_jobserver_bst_show returns and before open_jobserver; the report carries seed_bound "max_jobs"|"cores". Widening only through the existing _handle_underload path (idle hold, then MemoryGate.withhold), so every token past the seed passes the gate. No max-jobs → seed unchanged, seed_bound "cores". An explicit --jobserver N or hand-typed --jobserver-seed is honoured (keyed on BGA_JOBSERVER_MODE == "auto").
Rejected:  seed 0 with the gate opening every token - withhold returns None with no sandbox live so it widens blindly anyway, and costs the win shapes two ticks per token; seed from MemAvailable / an assumed per-job peak - no END line exists at open, a proxy; clamping in bga/cli.py - the CLI never runs bst show, so has no max-jobs.
Files:     tools/jobserver/pool.py (new opening_seed only); tools/bst_native_build_tracer.py (seed resolve after the bst-show read, seed_bound report key); bga/schemas.py if the report schema needs the key; tests/unit/test_the_auto_seed_opens_at_bsts_own_max_jobs.py.
Guard:     that test - (a) opening_seed(15,8,"auto",False)==7, (8,8)==7, (3,8)==3, None max-jobs leaves 15, mode "n" leaves 15; (b) a 16-ceiling FIFO built as in test_the_pool_withholds_for_measured_rss_with_no_plan.py, seeded from opening_seed(15,8,...), drained, two giant-shaped sandboxes live, 2 GB finished peak vs 8 GB available: two low ticks hold with an `rss ...` reason and pool == 7 (today's seed 15 would give 17 jobs); (c) a tracer-seam assertion that the resolved seed is 7 with seed_bound "max_jobs".
Mutation:  opening_seed returns seed unchanged → (a),(b) red; drop the tracer call → (c) red.
Class:     product
Split:     one track, parallel with 1282/1284/1310/1314.
Owner reading: two memory-bound giants at once under auto on Graviton, plus memgiant/pairs/cap3 re-read against run 37031346135 (needs Ruslan's word to push to bga-bench); risk: pairs/cap3 now open at max-jobs - 1 so their win may shrink; outside noise → follow-up row, not a revert.
Question:  none
```

## Required Fix

The seed is the gate's first decision rather than a given: with no
plan, the pool opens at what the gate admits from `MemAvailable` and
the build's first measured jobs, or at bst's own max-jobs when it has
no reading yet, and widens from there.

## Out of Scope

Revoking tokens already handed out; the cgroup reading (UX-1282).

## Acceptance Test

A Graviton leg with two memory-bound giants built at once completes
under `auto` where today's seed would take both past memory; the
single memgiant and the win shapes keep their readings within noise.

## Outcome

**Gap measured.** `main` under `BGA_JOBSERVER_MODE=auto`, `--jobserver 16
--jobserver-seed 15`, bst-show max-jobs faked to 8, `opening_seed`
mutated to return its seed (today's behaviour): the FIFO opens at 15.
At 15 the controller never reaches the gate (`pool < ceiling - 1` is
`15 < 15`): the 15 seeded tokens are the only ones handed out, none of
them gated - the cores-sized seed, not a widening, is the exposure.

```text
test_main_resolves_the_seed_after_reading_max_jobs   E   assert 15 == 7
```

**Close measured.** Same fixtures, fix in: the FIFO opens at 7 and the
run-context `jobserver` block reads `seed 7, seed_bound "max_jobs"`. Two
giants live (0.5 GB each), 2 GB finished peak, at seed 7: 64 GB
available, the second low tick adds (pool 8); 8 GB available, it holds
`rss ...` (pool 7). A hand-typed `--jobserver-seed` under `bga capture
--jobserver auto` sets `BGA_JOBSERVER_SEED_TYPED=1`; the tracer then keeps
it (seed 15, `seed_bound "typed"`). `seed_bound` is documented in
`bga/schemas.py`'s `jobserver` block and classed `B:jobserver_seed_bound`
in `bga/disclosure.py`.

**Graviton reading** (bga-bench run 37606960927, 16x A72, 31 GB): two
memory giants ready at once (`twomemgiants`, `auto` at bst's builders)
open at bst's max-jobs - 1 and the gate holds the widening; pairs and
cap3 keep their wins (cap3 within 1% of run 37031346135's 261/112):

```text
twomemgiants auto-1  wall 851 s  mem 26785 M  peak 9  pool start 7 max 9 adds 2 rss-holds 1990
twomemgiants auto-2  wall 840 s  mem 26727 M  peak 8  pool start 7 max 8 adds 1 rss-holds 1987
pairs  off 138.0 136.9 137.0 s (giant-peak 8)   auto 107.4 107.2 107.0 s (16)
cap3   off 259.8 258.3 258.5 s                  auto 110.4 108.4 110.0 s
```

memgiant gave no reading: the runner lost communication (UX-1281).

```text
$ python3 -m pytest -q -p no:xdist tests/unit/test_the_auto_seed_opens_at_bsts_own_max_jobs.py
7 passed in 1.23s
$ dev_touching.py --base d0e434e2 --list   (368 files), pytest -n 2
10 failed, 7060 passed, 135 skipped, 10 errors
  fixed: the schema prose named a key, no cli.md row for the new
  variable, json-contracts.md 639 -> 640 keys and the block's row, the
  snapshot guard's block literal, the selector ceiling max 211 -> 212
  re-run of those files: 191 passed, 1 failed (the ceiling, then fixed:
  46 passed), 10 errors - `rendered`/`probed` fixture not found in
  test_the_palette_is_validated.py / test_the_mapping_is_law.py, files
  this diff does not touch
```

| Mutation | Reddened | Count |
| --- | --- | --- |
| `opening_seed` returns `seed` unchanged | `..._less_one`, `..._fit_widen_past_the_seed`, `..._do_not_fit_...`, `main_resolves_...` | 4 failed, 3 passed |
| opens at 7 but bypasses the gate (`withheld = None` in `_handle_underload`) | `two_giants_that_do_not_fit_get_no_token_past_the_seed` | 1 failed, 6 passed |
| drop the `opening_seed(...)` call in `main` | `main_resolves_the_seed_after_reading_max_jobs` | 1 failed, 6 passed |
| `opening_seed` ignores `typed` | `everything_else_keeps_its_seed`, `a_typed_seed_is_honoured_under_auto` | 2 failed, 5 passed |
| CLI never calls `_mark_typed_seed` | `the_cli_marks_a_typed_seed_and_only_a_typed_one` | 1 failed, 6 passed |
| `_jobserver_block` drops `seed_bound` | `main_resolves_...`, `a_typed_seed_is_honoured_under_auto` | 2 failed, 5 passed |
| all reverted from the scratchpad copies | - | 7 passed |
