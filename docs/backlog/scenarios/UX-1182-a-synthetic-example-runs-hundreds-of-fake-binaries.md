# UX-1182: a synthetic example runs hundreds of fake binaries per element, drawn from named distributions

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Out of Scope

The findings' own fixes (`UX-1183`..`UX-1193`); a new `gen-synthetic` distribution for durations of whole elements.

## Acceptance Test

`tests/unit/test_the_synthetic_workload_runs_hundreds_of_binaries.py`: the generated example has at least 5 elements with at least 200 distinct binaries each in Plane 2, every named distribution appears, both planes are present and matched, and two runs with one seed give identical Plane 2 bytes. Mutation: cap distinct binaries per element at 81, or seed the RNG from the clock; the guard reds.

## Outcome

Open.
