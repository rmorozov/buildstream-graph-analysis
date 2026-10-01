# UX-1182: a synthetic example runs hundreds of fake binaries per element, drawn from named distributions

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py`

## Motivation

Finding: the owner's request after the review.

Ruslan: "as you pointed that current examples doesn't have many binaries per element I propose making several with hundreds of binaries inside elements in example - we can make fake binaries with different distributions of sleep that can simulate workload".

`bga gen-synthetic --help` lists only layers, width, builders, seed, run-id, store and runs, and every element runs one `/usr/bin/cc`: the review's 1,202-element page reads distinct binaries per element max 1, p90 1, median 1. The review's `heavy.py` rewrote that `plane2.log` (seed 7) to 5,849 processes and max 81, p90 4, median 4 distinct binaries per element, 8 named elements at 30-80. No committed fixture reaches the populations findings 1, 4 and 9 are about (`UX-1183`, `UX-1186`, `UX-1191`): `macro_micro` has 71 `binary_cost` rows and `tests/pages.py`'s `scale_two_plane_snapshot` cycles a caller's `programs` list with fixed 0.05 s processes.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A synthetic example in which several elements each exec hundreds of distinct fake binaries (for example 8 elements at 200-500 each, the rest at 3-10). Each fake binary sleeps, or burns CPU, for a time drawn from a named distribution - several of them (constant, uniform, exponential, lognormal, a heavy-tailed Pareto) - from a seeded RNG, so one seed gives one byte-identical capture. The example carries both planes, with Plane 2 inside each element's own window as `heavy.py` keeps it.

The route is the architect's. The two candidates:

- (a) a `gen-synthetic --store` option (`tools/gen_synthetic_scale_run.py`) that writes that Plane 2 directly: cheap, deterministic, and fast enough for `tests/pages.py`;
- (b) a real project under `examples/` whose elements run the fake binaries under the `LD_PRELOAD` hook (the shape of `examples/08-process-storm/`): a true capture, slower, and a reading of the hook rather than of the generator.

Consumers: a `tests/pages.py` page the guards of `UX-1183`, `UX-1185`, `UX-1186` and `UX-1191` read, and the next data-exploration review. The page-byte budget (`PAGE_BUDGET_B`, 160,000 B in `tools/bga_view.py`) reads the committed pages only, and the page half is code, so the heavy page does not move it. The heavy page is generated, never committed: it is priced by its readings (page and data half in bytes, controls, opened height) pasted in the Outcome against the 4,100 class of `test_the_page_has_a_volume_budget.py` and the `DATA_BUDGETS` class of `test_the_exports_data_half_has_a_budget.py`, and joins a budget only where the architect names it (heavy.py's page reads 909 controls against 900 today).

## Decision

Class: process - it moves no reader-facing output; it is the population the other rows' guards and the next review read.

Architect (round 158):

```text
Route:     (a) `gen-synthetic --store --workload binaries`: a second Plane 2 writer beside `_plane2_records`. 8 buildable elements (the 8 longest, never import/stack) exec 200-500 distinct fake binaries each and the rest 3-10. Each binary runs 1-3 times and has one of five named distributions (constant, uniform, exponential, lognormal, pareto). It sleeps (utime ~0) or burns (utime ~ wall), clamped inside the element's window. The writer uses its own RNG, `random.Random(f"workload:{seed}:{index}")`, so the default store stays byte-identical.
Rejected:  (b) a real capture under examples/ needs bst plus the hook, cannot run in CI, and at 8x300 sleeping binaries takes minutes. It reads the hook, which is not the population the guards need. See the Question.
Rejected:  keeping heavy.py out of tree. It is unseeded in the tree and unreviewed, and the four guards need a committed producer.
Files:     tools/gen_synthetic_scale_run.py (new DISTRIBUTIONS table, `_workload_records`, `_plant_store` selects the writer, `main` adds `--workload {cc,binaries}`, default cc); tests/pages.py (new `heavy_binary_run(into)` = `two_plane_run(into, ("--workload","binaries",*REVIEW_SHAPE), name="heavy")`); tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py; tests/tiers.py (small: two gens, ~0.6 s); docs/guides/cli.md (the gen-synthetic line, if it lists options)
Guard:     test_the_synthetic_workload_runs_hundreds_of_binaries.py: at least 5 elements with at least 200 distinct binaries in Plane 2; all five distribution names appear; every START/END lies inside its element's Plane 1 window; two runs with one seed give identical plane2.log.gz bytes (decompressed); the default `--store` Plane 2 is one cc process per building element.
Mutation:  cap distinct binaries at 81 -> reds; seed the RNG from time.time() -> reds; draw from the shared rng so the default store's Plane 2 changes -> the last clause reds.
Class:     bookkeeping (process, as its Decision says). It is the population the product guards of 1183/1185/1186/1191 read.
Split:     one track. It runs first or in parallel, and 1183/1185/1186/1191 rebase onto its tests/pages.py.
Question:  (b) as well? See the report's Question.
```

Budgets: none move. The page half, xl_both controls and height, and macro_micro words read the committed pages and xl_both, and the workload is opt-in. The heavy page joins no budget this round. Its readings (page and data bytes, controls, opened height) go in the Outcome against the 4,100 class and `DATA_BUDGETS`, because heavy.py's page already read 909 controls against 900.
Cost per test run: about 1.8 s CPU per build (gen 0.26 + capture report 0.45 + export 1.08, measured on the surrogate above). It is not disk-cached. Each consuming file builds it once in a module-scoped fixture: 4 files come to about 7 s CPU, spread over xdist workers. A browser drive adds the page's own open time.
Follows: nothing. 1183, 1185, 1186 and 1191 follow it because their guards need `heavy_binary_run`. 1184 and 1187-1193 name UX-1182 in their Input classes only.

Track: route (a) as shaped, with three departures. A binary's name and its draw share one lookup, and a clause reads each distribution's draws, because a names-only clause passed a mutation that drew from the wrong distribution. The architect's shared-rng mutation cannot move the default store, which never calls the writer, so the Plane 1 clause is mutated by the workload consuming the shared rng before `_durations`. The default store writes one `cc` for every element, `import`/`stack` included, and the clause says so. No tests/tiers.py row: that file belongs to the orchestrator, and the file reads 2.35 s.

## Out of Scope

The findings' own fixes (`UX-1183`..`UX-1193`); a new `gen-synthetic` distribution for durations of whole elements.

## Acceptance Test

`tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py`: the generated example has at least 5 elements with at least 200 distinct binaries each in Plane 2, every named distribution appears, both planes are present and matched, and two runs with one seed give identical Plane 2 bytes. Mutation: cap distinct binaries per element at 81, or seed the RNG from the clock; the guard reds.

## Outcome

### The gap, measured

```text
base 8a531cbb, gen-synthetic --seed 1 --store --layers 8 --width 14 (REVIEW_SHAPE):
  base --workload   exit 2  error: unrecognized arguments: --workload binaries
  base default      114 processes, distinct binaries per element max 1, median 1, elements >= 200: 0
```

### After

```text
tests/pages.py heavy_binary_run(into) = two_plane_run(into, ("--workload", "binaries", *REVIEW_SHAPE), name="heavy")
  build 1.43-1.61 s (gen + capture report --json), export() 0.90-1.03 s
  7,984 processes, 112 building elements; distinct per element top 8: 499 493 490 456 396 372 369 214, median 8
  plane2.log 2,630,156 B; plane2.json 453,384 B
  export(): bytes 394,199, page_bytes 144,202, data_bytes 249,997
  in-place page, 1440x900 (_LOOK), 4,100 class: opened 40,851 of 43,500 px, 12,475 of 13,200 words,
    780 of 900 controls, 6,623 of 7,500 nodes; _halves data 97,142 of DATA_BUDGETS 335,000 B
default store Plane 2, base vs HEAD, decompressed: 47,506 B and 47,521 B, both equal
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py -q
7 passed in 2.35s
```

`--workload binaries` writes Plane 2 with `_workload_records` and its own RNG,
`random.Random(f"workload:{seed}:{index}")`. It draws from a 600-binary pool named
`<distribution>-NNN` over constant, uniform, exponential, lognormal and pareto;
odd-indexed binaries burn (utime 0.95 x wall), even ones sleep. Each element's
fake binaries run under one `make` root.

### Mutations verified red and reverted (8)

| # | mutation (tools/gen_synthetic_scale_run.py) | reddened |
|---|---|---|
| M1 | cap distinct binaries at 81 | `test_several_elements_run_hundreds_of_distinct_binaries`, 1 failed |
| M2 | `random.Random()` (entropy) for the workload RNG | `test_one_seed_gives_one_plane2`, 1 failed |
| M3 | draw from `names[i % 4]` while named `names[i % 5]` | `test_each_binary_draws_from_the_distribution_it_is_named_for`, 1 failed |
| M4 | no clamp, wall x 20 | `..._named_for`, `test_every_process_lies_inside_its_elements_plane1_window`, 2 failed |
| M5 | `--workload binaries` consumes the shared rng before `_durations` | `test_the_workload_moves_plane2_alone`, 1 failed |
| M6 | default writer execs `/usr/bin/gcc` | `test_the_workload_moves_plane2_alone`, 1 failed |
| M7 | `element={uid[:-4]}` | `..._plane1_window`, `test_both_planes_join_on_every_building_element`, 2 failed |
| M8 | burners do not burn (`utime = 0.001`) | `..._named_for`, 1 failed |

Reverted from the saved copy: 7 passed.
