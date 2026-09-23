# UX-942: the touching selector misses a guard that reads a record through a tool's constant

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-336, UX-730 | **Blocks:** — | **Found by:** round 136 — choosing which guard `UX-934`'s ledger adopt job runs; `make test-touching` on a `tests/flake_ledger.json` edit selects 31 files and not the one that reds | **Serves:** every session whose inner loop is `make test-touching` on a change to a committed record | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`dev_touching.py` selects by grep over the changed path, plus the census
and the map. A guard that reaches a record through a tool's own constant
names neither the path nor a module the diff touched, so it is never
selected — and the selector says so as a finding only when it finds
nothing at all:

```text
$ echo " " >> tests/flake_ledger.json && python3 tools/dev_touching.py --list
No test file names any of 1 changed file(s):
  tests/flake_ledger.json
...
$ python3 tools/dev_touching.py --list | grep -c .      # 31, census only
$ python3 tools/dev_touching.py --list | grep -E "excursion|flake"
$                                                      # nothing
```

On the same tree the guard it skips is red
(`test_a_file_with_three_excursions_has_a_filed_task.py::test_the_real_ledger_has_no_unfiled_repeat_excursion`,
`tests/flake_ledger.json` at `8090a99d`). It reads the ledger through
`dev_flake_census.LEDGER = REPO / "tests" / "flake_ledger.json"`: the
path split into parts, in a module the diff did not touch.

`UX-730` closed this shape for a guard whose *population* is a named
index, with six curated delegates; a guard whose *subject* is a named
record, reached through a tool's constant, is the other half.

## Required Fix

A changed record selects the guards that load it through a tool. Measured
while filing: the widest derivation — every unit file importing a
`tools/dev_*` module whose source names the record's basename — selects
13 files for the ledger, 15 for the reference and 12 for the map, 40 s
serial each; the files that assert on the committed record itself are
1, 2 and 2. Say which the selector takes, and why that is not a proxy.

## Out of Scope

`UX-934`'s declared guards in `tools/dev_adopt_check.py`, which answer a
different question (what an adopt job must not push past) and are read
by their own guard.

## Acceptance Test

A change to `tests/flake_ledger.json` alone selects
`test_a_file_with_three_excursions_has_a_filed_task.py`; a mutation that
reverts the selector's new clause reddens.

## Outcome

**Round 138, 2026-09-23.** **Premise:** held — the ledger's own guard
was unreachable from a ledger edit.

### The gap, measured

`delta.py` (scratch): `select([p])` from `dcbe4615`'s `dev_touching.py`
against this one, same tree, every tracked non-`.py` path:

```text
1678 paths; ... moved 8
  tests/flake_ledger.json: 32 -> 33  +['test_a_file_with_three_excursions_has_a_filed_task.py']
  tests/ci_reference.json: 35 -> 36  +['test_the_suite_holds_its_shape_budget.py']
  tests/touch_map.json: 33 -> 35  +['test_a_slow_file_says_which_file.py', 'test_a_track_costs_what_it_reads.py']
  docs/contributing/fixing-guide.md: 44 -> 46  +['test_a_track_costs_what_it_reads.py', 'test_every_task_names_its_area.py']  (+ four docs paths, +1 each)
```

### After

`dev_touching.select([record])` - what `--list` runs on that record alone:

```text
tests/flake_ledger.json: 34 selected, 3 naming, 1 by the clause
  test_a_file_with_three_excursions_has_a_filed_task.py  <- dev_flake_census.load()
tests/ci_reference.json: 37 selected, 8 naming, 2 by the clause
  test_a_slow_file_says_which_file.py  <- dev_tier_drift.CI_REFERENCE
  test_the_suite_holds_its_shape_budget.py  <- dev_shape_budget.ledger_problems()
tests/touch_map.json: 36 selected, 7 naming, 7 by the clause
  (every one through dev_touching.select() / main() / spread() / touch_map())
```

**The narrow set, derived.** `tools/_record_readers.py` reads each `tools/*.py`
naming the record's basename: a module constant whose `REPO / ...` chain
spells the record's *path*, a function defaulting a parameter to it, a
parameterless body spelling it, and, closed over the tool's own calls,
any function calling one of those without passing the path. A test
selects when it reaches one of those through an import of that tool
and leaves the path to its default; `census.load(tmp_path)` does not.
Not a proxy: the edge is the call that opens the committed file, not
"imports a module that mentions it" (the widest derivation) and not a
list. Serial, `-n 0`, load average 13.8 on 4 cores:

```text
tests/flake_ledger.json: clause 1 files 1.1s  | widest 12 files 81.1s
tests/ci_reference.json: clause 2 files 18.4s | widest 12 files 86.2s
tests/touch_map.json:    clause 7 files 87.4s | widest 9 files 88.9s
```

The map's 7 are the selector's own guards, each calling `select()`; a
map edit really does move what they assert (the cost row's figure).
Only non-`.py` paths take the clause, so `--spread` holds at 31-163;
its file count moved 582 -> 583 with this guard. Mean `select()` over
the 1678 paths: 95 ms before, 89 ms after (same run, noise).

### Mutations verified red, reverted from a snapshot, 11 passed (6)

| # | mutation in `tools/_record_readers.py` | reddened |
|---|---|---|
| M1 | the clause reverted (`choose` returns early; or its call deleted) | the ledger and reference cases, 2 |
| M2 | `_on_default` always true | `..._on_its_own_path_does_not`, 1 |
| M3 | no call closure (`grew = False`) | reference, `..._calling_the_loader_selects`, 2 |
| M4 | constant access ignored | `..._constant_itself_selects`, `..._elsewhere...`, 2 |
| M5 | basename match, not path | `..._same_named_record_elsewhere...`, 1 |
| M6 | `_tree` lets a `SyntaxError` out | `..._mid_edit_is_skipped_not_fatal`, 1 |

### Deviation from the Required Fix

None: the narrow set, with a call closure the filing's 1/2/2 count
did not take - the map reads 6 (7 with this guard), not 2, because
`select()` reads it.

```text
$ make test-touching
54 file(s) selected (21 census + 33 naming the change) · 2216 passed, 4 skipped in 179.86s (0:02:59)
$ make lint
clean: 573 finding(s) match .../tests/quality_baseline.json; ...
```

`make test` ran on the pushed HEAD; its line is in the track report.
