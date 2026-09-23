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

## Outcome (round 138, 2026-09-23)

**Round 138, 2026-09-23.** **Premise:** held — neither a race nor a
tier move: the CI record was too low, and CI's adopt has already
refreshed it.

### The gap, measured

Alone and single-process, three times, against `tests/tiers.py`
(`MEDIUM`, 4.9s; `LARGE_FLOOR_S` 15.0), on a box five other tracks share:

```text
$ python3 -m pytest tests/unit/test_the_trace_census_reads_both_ends.py -q -p no:cacheprovider -o addopts=
run 1: wall 13.31s cpu 9.01s load1 9.3  23 passed in 12.77s
run 2: wall 13.15s cpu 8.96s load1 9.3  23 passed in 12.77s
run 3: wall 12.72s cpu 8.85s load1 9.5  23 passed in 12.42s
```

Under 15.0 even at a load of 9 on 4 cores, so the tier holds. On CI the
six excursions, read against the 8.71 record adopted 2026-09-02
(`0d288ebf`), are 13.21-14.82 s, and the three real readings since
`UX-924` are 12.66, 12.24, 12.53: one band, 12.2-14.8 s, over the
ledger's 2026-09-16..22 — a file sitting above a stale record, not a
race. By run (`UX-936`), five of its six excursions had at most two
other files beside them; the sixth was 35755437814's six.

### After

`0c166828`, CI's third post-`UX-924` adopt, moved the record 8.71 ->
12.24 (`median_low` of `[8.71, 8.71, 12.66, 12.24, 12.53]`):

```text
ledger reading against 12.24, over 1.5x and +5s:
35078687035 x1.12  35199472344 x1.14  35330268532 x1.09
35723802038 x1.21  35755437814 x1.08  35773916368 x1.18   all False
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[]
```

`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py`: 8
passed. The two remaining 8.71 copies leave the window in two adopts.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | this task's `**Flake:**` field deleted | `test_the_real_ledger_has_no_unfiled_repeat_excursion`, 1 of 8 |
| A2 | `**Flake:**` pointed at `test_tie_break.py`, which has no excursion | the same clause, 1 of 8 |

### Deviation from the Required Fix

No `declared` entry: the file is named here and its record is right now.
`tiers.py`'s 4.9s is stale (CPU alone reads 8.9s), but a loaded-box
wall is not a record; no tier boundary is crossed, so it is left.
