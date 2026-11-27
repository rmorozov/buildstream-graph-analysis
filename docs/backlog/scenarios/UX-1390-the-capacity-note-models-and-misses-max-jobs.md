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

Not fixed: line 28 reads "max-jobs unrecorded" while `run-context.json` carries
`"max_jobs": 4`; the checks read `native_max_jobs` only.

| mutation | red |
|---|---|
| `bga/cli.py`: always `MODELLED_AXIS_CLAUSE` | `test_a_missing_max_jobs_value_is_not_also_modelled` (1 failed, 1 passed) |
| `bga/cli.py`: always `MODELLED_AXIS_UNRECORDED_CLAUSE` | `test_a_recorded_max_jobs_value_keeps_the_modelled_clause` (1 failed, 1 passed) |

Reverted from a copy; both green after (2 passed).
