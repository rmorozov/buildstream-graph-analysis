# UX-1390: one capacity Note says `--max-jobs` is modelled and missing

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** walk seed 7 (2026-11-27) | **Serves:** R6 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_capacity_note_does_not_model_and_miss_max_jobs.py`

## Motivation

[`walk-seed-7.md`](../../audits/walk-seed-7.md) finding 5: `bga analyze
tests/fixtures/macro_micro/run --format text` (its `plane2.json` beside it), line
91, one Note: "native build-system parallelism (--max-jobs) is modelled for this
capture from its own Plane 2 measurements" and "Capacity checks ... did not run
for this run — missing: the --max-jobs value", while line 116 reads "max-jobs 4".

## Decomposition

Input classes: Plane 2 report beside the run, absent; `--max-jobs` given, not given. Journey: extends the walk's seed 7 class.

## Required Fix

The Note names one source for `--max-jobs`: the capacity checks run on the
modelled value, or the Note says why a modelled value does not count.

## Out of Scope

The capacity checks' own thresholds.

## Acceptance Test

On the fixture above, the text report's Note does not both model and miss
`--max-jobs`; a mutation restoring the two clauses reddens it.

## Outcome

Round 176, 2026-11-27.

**Reading chosen: the Note says why a modelled value does not count.**
`docs/guides/cli.md:1481` defines the capacity checks' `--max-jobs` as the
run's own value (`--native-max-jobs`, the wrapped log's invocation, else the
graph's resolved value). The "max-jobs 4" at line 116 is the recommendation's
per-element `max-jobs` (`UX-677`), a different quantity. Running the checks on
it would change what they certify, which is `Out of Scope`.

**Gap measured** (`bga analyze <copy of macro_micro/run + plane2.json> --format text`, line 91):

```text
... --max-jobs) is modelled for this capture from its own Plane 2 measurements; see the
capacity recommendation below. Capacity checks (...) did not run for this run - missing:
the --max-jobs value.
```

**Close measured**, same command, line 91:

```text
... --max-jobs) is modelled per element from this capture's Plane 2 measurements, in the
capacity recommendation below; that is not a recorded --max-jobs, so it does not feed the
capacity checks. Capacity checks (...) did not run for this run - missing: the --max-jobs value.
```

With `native_max_jobs: 4` added to `run-context.json` the original clause stands
and no skipped sentence prints. No JSON key changed (`floors.capacity_model_note`
is a string); no golden changed. `bga/analyzer.py` gained
`MODELLED_AXIS_UNRECORDED_CLAUSE`, `bga/cli.py` picks it when `native_max_jobs`
is in `capacity_check_skipped_inputs`; two history comments shrunk so
`dev_sizes.py --check` holds. `test_the_loop_stays_fast.py` `CEILING["max"]`
220 -> 221: the new guard names `bga.cli`, the widest module (selection 221).

First pass left (fixed in the rework below): line 28 reads "max-jobs unrecorded" while `run-context.json` carries
`"max_jobs": 4`; the checks read `native_max_jobs` only.

| mutation | red |
|---|---|
| `bga/cli.py`: always `MODELLED_AXIS_CLAUSE` | `test_a_missing_max_jobs_value_is_not_also_modelled` (1 failed, 1 passed) |
| `bga/cli.py`: always `MODELLED_AXIS_UNRECORDED_CLAUSE` | `test_a_recorded_max_jobs_value_keeps_the_modelled_clause` (1 failed, 1 passed) |

Reverted from a copy; both green after (2 passed).

### Review rework (2026-11-27)

Gap 1 (PR #353): on `macro_micro/run` + `plane2.json`, `capacity_recommendation.native_max_jobs`
is null and there is no `max_jobs_advice` (no `host-samples.jsonl`), yet the Note said the
per-element model was "in the capacity recommendation below". `_finish_capacity_recommendation`
now computes the advice first and picks the clause after: unrecorded with advice keeps
`MODELLED_AXIS_UNRECORDED_CLAUSE`; unrecorded without it says `UNMODELLED_UNRECORDED_CLAUSE`
("has no per-element estimate"). The with-advice case is `tests/fixtures/host_cpu` (run +
`host-samples.jsonl`) with `native_max_jobs` nulled.

Gap 2: line 28 reads `native_max_jobs` (null); `run-context.json`'s `max_jobs: 4` is
`--builders` (`RunContext.max_jobs`, `_capacity_recommendation`'s `builders`), not the native value,
so the line was right and its label was not. It now reads `builders 4 x native max-jobs unrecorded`;
a recorded value still prints `max-jobs N`. No JSON key changed; no golden changed
(`cli.md` examples updated, with one sentence naming the two quantities).

| mutation | red |
|---|---|
| advice ignored: always `MODELLED_AXIS_UNRECORDED_CLAUSE` | `..._with_no_advice_claims_no_model` (1 failed, 35 passed) |
| always `UNMODELLED_UNRECORDED_CLAUSE` | `..._with_advice_points_at_it` (1 failed, 35 passed) |
| always `MODELLED_AXIS_CLAUSE` | both unrecorded tests (2 failed, 34 passed) |
| never `MODELLED_AXIS_CLAUSE` | `test_a_recorded_max_jobs_value_keeps_the_modelled_clause` (1 failed, 2 passed) |
| `findings.py`: label back to `max-jobs unrecorded` | `test_an_unrecorded_max_jobs_is_named_rather_than_dropped` (1 failed, 35 passed) |

Reverted from copies; green after (36 passed).

### Second review rework (2026-11-27)

Gap 1: `tests/fixtures/host_cpu` + `native_max_jobs` null + first 4 `host-samples.jsonl` lines gave 11 advice rows, all
`recommended_max_jobs: null`, yet "modelled per element". Clause now keys on any row's estimate, rows kept.
Gap 2 (`cli.py` `get(uid) or native_max_jobs` reads 0 as 1, left): `native_max_jobs: 0` printed "native max-jobs unrecorded"; now `is not None`, 0 reads "max-jobs 0 (BuildStream auto)".
| mutation | red |
|---|---|
| `if estimated` -> `if advice` | all-refused test (1 failed, 4 passed) |
| `is None` -> `not jobs` | both zero tests (2 failed, 37 passed) |
