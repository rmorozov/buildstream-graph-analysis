# UX-1396: a recorded `--max-jobs 0` is read as missing

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** verifier on Ruslan's #353 review, 2026-11-27 | **Serves:** R6 | **Topic:** analysis | **Area:** bga | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_recorded_max_jobs_0_is_not_read_as_missing.py`

## Motivation

`--max-jobs 0` is BuildStream's automatic setting, `min(cores, 8)`, and `bga/analyzer.py` and `bga/correlate.py`
already say so. Three readers still treat a recorded 0 as no value: `bga/utilisation/envelope.py` (`(run.get("native_max_jobs") or 0)`
leaves `configured_capacity_cores` null), `bga/cli.py` `_builder_pool_recommendation` (`max_jobs_by_uid.get(uid) or native_max_jobs`,
then `width or 1`, then `all(chain_widths)`), which sizes the builders line as a `-j1` chain with no regime.

## Decomposition

Input classes: `native_max_jobs` 0, unrecorded, positive; element `max_jobs` 0, unset, positive. Surfaces: `bga/floors/cpu.py`
(one resolver), `bga/utilisation/envelope.py`, `bga/cli.py`. Journey: extends the walk's seed 7 class (UX-1390).

## Required Fix

`bga/floors/cpu.py` resolves a recorded 0 to BuildStream's `min(cores, 8)`; `bga/utilisation/envelope.py` and `bga/cli.py` call it where a width
is needed; `None` stays unrecorded.

## Out of Scope

`bga/analyzer.py`'s capacity checks, which already resolve 0; the printed `max-jobs 0 (BuildStream auto)` wording (UX-1390).

## Acceptance Test

A run with `native_max_jobs: 0` on 4 and on 16 cores sizes its builders line by a chain of 4 and of 8; the envelope's
`configured_capacity_cores` is `builders x min(cores, 8)`; a mutation restoring `or` reddens each.

## Outcome

**Gap measured** (`write_run_dir` of a base and four dependents, `native_max_jobs: 0`, no element override, `bga analyze <run>`):

```text
host 4 :  "Builders: 3 with --jobserver auto - ..."   no "Approaches sized" line
host 16:  "Builders: 15 with --jobserver auto - ..."  no "Approaches sized" line
envelope (64 cores, builders 2, max-jobs 0): configured_capacity_cores None, capacity_cores 64
```

**Close measured**, same runs:

```text
host 4 :  "Builders: 4 with --jobserver off, max-jobs 4 - a small host: 4 cores, ..."   "Approaches sized for 4 cores" present
host 16:  "Builders: 8 with --jobserver auto - ... the critical path's max-jobs=8 ..."    "Approaches sized for 16 cores" present
envelope: configured_capacity_cores 16, capacity_cores 16
```

`bga.floors.cpu.effective_max_jobs(jobs, cores)` resolves a recorded 0 to `min(cores, BST_MAX_JOBS_CEILING)` and passes `None`
through; the envelope resolves against the series' cores, `_builder_pool_recommendation` against `host_cpu_count`, and a per-element
0 now resolves instead of falling back to the global value. `BST_MAX_JOBS_CEILING` moved from `bga/correlate.py` to `bga/floors/cpu.py`.
No JSON key changed; `configured_capacity_cores` takes a value where it was null. `all(chain_widths)` is left: after the resolver
no width is 0, so `is not None` is an equivalent mutant.

| mutation | red |
|---|---|
| `if jobs != 0:` -> `if True:` | resolver, envelope and builders-line tests (8 failed, 4 passed) |
| ceiling `8` -> `4` | resolver 0/16, envelope, 16-core builders line (4 failed, 8 passed) |
| envelope reads the raw `native_max_jobs` | `test_the_envelope_caps_a_zero_max_jobs_at_the_automatic_width` (1 failed, 11 passed) |
| `cli.py` `get(uid) or native_max_jobs` | the two per-element builders-line tests (2 failed, 10 passed) |
| `cli.py` drops `effective_max_jobs` (width unresolved) | all four builders-line tests (4 failed, 8 passed) |

Reverted from copies; 12 passed after.
