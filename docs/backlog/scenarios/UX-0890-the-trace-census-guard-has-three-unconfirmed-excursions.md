# UX-890: the trace-census guard has three unconfirmed CI excursions and no filing

**Flake:** tests/unit/test_the_trace_census_reads_both_ends.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691 | **Found by:** round 130 — `ec50169` appended the third excursion and shipped `main` red: `make test` fails `test_the_real_ledger_has_no_unfiled_repeat_excursion`, which is `UX-691`'s guard doing its job | **Serves:** the round whose push gate is blocked by a file nobody has named | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`UX-691`'s rule is that a file the flake ledger excurses on three times
names itself in a task. `tests/flake_ledger.json` now carries three
unconfirmed excursions for one file and `declared` is empty, so the
guard is red on a clean checkout:

```text
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[('tests/unit/test_the_trace_census_reads_both_ends.py', 3)]

$ python3 -c "
import json; d=json.load(open('tests/flake_ledger.json'))
print([(e['run_id'], e['shift']) for e in d['entries']
       if 'trace_census' in e['file']])"
[('35078687035', 1.573), ('35199472344', 1.601), ('35330268532', 1.535)]
```

Three runs, shifts 1.535–1.601, none confirmed — a tight band, which is
what a file sitting just over its tier floor looks like rather than a
race. `make test` is red for every branch until this is named, which is
how `UX-889` found it.

## Required Fix

Decide which this is, with a reading rather than a guess: re-time the
file alone and single-process against its `tests/tiers.py` floor. If it
has outgrown the floor, move it and say so. If the excursions are a
real race, fix the race. If neither — the band is CI's clock and the
file is at the boundary — that is a `declared` entry in the ledger with
the reason, not a task.

This file is the filing the guard asks for; it is not the fix.

## Out of Scope

Retiming any other file in the ledger. Changing `EXCURSION_FLOOR`.

## Acceptance Test

`python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"`
returns `[]` for a reason this task's Outcome states, and
`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py` is
green on the real ledger.

## Outcome
