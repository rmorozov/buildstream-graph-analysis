# UX-908: the drawing-grade guard has three unconfirmed CI excursions, and they are rising

**Flake:** tests/unit/test_a_drawing_is_graded.py
**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-691 | **Found by:** round 131 — `3c12c9eb` appended the third excursion and shipped `main` red: `make test` fails `test_the_real_ledger_has_no_unfiled_repeat_excursion`, which is `UX-691`'s guard doing its job | **Serves:** the round whose push gate is blocked by a file nobody has named | **Topic:** guards | **Area:** tools | **Shape:** bounded

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

## Outcome (round 131, 2026-09-22) — 🟢 Done

**Premise:** falsified in part — the file grew and it is not a runner's
clock, but it does not *rise*: the ledger's fourth row, appended after
this task was filed, reads 2.114 against the third's 2.245.

### The gap, measured

```text
$ python3 -m pytest tests/unit/test_a_drawing_is_graded.py -q
39 passed in 10.27s, then 8.73s, then 8.41s   against tiers.py's 3.1s
in-suite, PYTEST_XDIST= pytest -m medium:      7.88s against 3.1s   x2.54
this box against tiers.recorded(), 171 files at or above SHIFT_FLOOR_S:
                                        median x0.828, p25 0.493, p75 1.192
```

The box is 17% *faster* than the one the floors were taken on and the
file still reads 2.5x its own. The ledger's ratio is against
`ci_reference.json`'s 6.47, not the 3.1s floor, so its four rows are
11.01 / 13.86 / 14.53 / 13.68 s on that document's clock. The file's
text is byte-identical (`8e1243d6`) across the last three readings and
`HEAD`. What changed sits on 2026-09-15, after `82b6249d`:

```text
82b6249d  26 tests  715 lines  run 34933450749  x1.701  11.01s
16a85b4c  27 tests  748 lines  UX-862
4a056a7d  33 tests  871 lines  UX-863
96c49cb9  36 tests  967 lines  UX-868, the file's first two @needs_browser
98967fc9  36 tests  967 lines  run 35507451517  x2.142  13.86s  docs only
395ebdc0  36 tests  967 lines  run 35536366563  x2.245  14.53s  docs only
5a10155e  36 tests  967 lines  run 35664785880  x2.114  13.68s
```

+38% tests, +35% lines, +26% seconds, nothing else touched the file,
and the three post-growth readings span 6% with no trend: one step,
then a flat band.

### After

`tiers.py` 3.1s -> 8.7s, the alone-single-process median, and
`ci_reference.json` 6.47 -> 13.86, the median of the three readings
above, samples flat at it (`UX-716`'s shape, and round 121's):

```text
$ python3 -c "from tools import dev_flake_census as c; print(c.unaccounted(c.load()))"
[]
$ # the same three readings, judged against the entry as committed
35507451517  13.86s against 13.86 recorded  x1.00  over both gates: False
35536366563  14.53s against 13.86 recorded  x1.05  over both gates: False
35664785880  13.68s against 13.86 recorded  x0.99  over both gates: False
```

Against the old 6.47 those three are x2.14 / x2.25 / x2.11, all over
both gates — four ledger rows and this task.

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | this task's `**Flake:**` field deleted | `test_the_real_ledger_has_no_unfiled_repeat_excursion`, 1 of 8 |
| A2 | `**Flake:**` pointed at `test_tie_break.py`, which has no excursion | the same clause, 1 of 8 |

**No guard reads either number this task moved.** Nothing in the suite
asserts that a `ci_reference.json` entry still matches what the runner
reads, and the entry sat 2.1x low for seven days while 37 adopt commits
carried it at 6.47/6.48. Why it could not correct itself is measured
and filed as `UX-924`: `adopt` reads the candidate's `files`, which is
already `median_low` of that candidate's own samples, so a full flat
window feeds the committed value back into itself.

### Deviation from the Required Fix

The ten tests are attributed as three commits, not split per commit:
the pre-growth copy does not run on today's tree (`UX-863` changed what
it asserts). The `declared` route the Fix warns against was not taken.

```text
<make test>
<make lint>
```
