# UX-908: the drawing-grade guard has three unconfirmed CI excursions, and they are rising

**Flake:** tests/unit/test_a_drawing_is_graded.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691 | **Found by:** round 131 — `3c12c9eb` appended the third excursion and shipped `main` red: `make test` fails `test_the_real_ledger_has_no_unfiled_repeat_excursion`, which is `UX-691`'s guard doing its job | **Serves:** the round whose push gate is blocked by a file nobody has named | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`UX-691`'s rule is that a file the flake ledger excurses on three times
names itself in a task. `tests/flake_ledger.json` now carries a third
unconfirmed excursion for a second file and `declared` is empty, so the
guard is red on a clean checkout of `main`:

```text
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[('tests/unit/test_a_drawing_is_graded.py', 3)]

$ python3 -c "
import json; d=json.load(open('tests/flake_ledger.json'))
print([(e['run_id'], e['shift'], e['confirmed']) for e in d['entries']
       if 'drawing_is_graded' in e['file']])"
[('34933450749', 1.701, False), ('35507451517', 2.142, False), ('35536366563', 2.245, False)]
```

This is not `UX-890`'s shape. That file's three shifts sat in a 1.535 to
1.601 band — a file at its floor, read three times. These **rise**,
1.701 to 2.142 to 2.245, and the last two are consecutive `main` pushes
on 2026-09-20. A rising ratio against a floor recorded as

```text
tests/tiers.py:894  "tests/unit/test_a_drawing_is_graded.py",   #    3.1s
```

is a file that grew, or a cost that grew under it, not a runner's clock.

## Required Fix

Re-time the file alone and single-process against its `tests/tiers.py`
floor, and bisect the ratio rather than the wall clock: if 1.701 was
the honest cost and 2.245 is today's, something between those two runs
added the difference, and `git log` over the file and what it draws
names the candidates. If it has simply outgrown 3.1s, re-record the
floor and say by how much. If the growth is in what the drawing guard
renders rather than in the guard, the finding belongs there.

A `declared` entry is the wrong answer here unless the re-timing shows
the band is flat after all; a rising ratio declared as known is the
measurement this repository has already been wrong about.

This file is the filing the guard asks for; it is not the fix.

## Out of Scope

Retiming any other file in the ledger — `UX-890` holds the other one.
Changing `EXCURSION_FLOOR`.

## Acceptance Test

`python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"`
returns `[]` for a reason this task's Outcome states, and
`tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py` is
green on the real ledger.

## Outcome
