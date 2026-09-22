# UX-942: the touching selector misses a guard that reads a record through a tool's constant

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336, UX-730 | **Blocks:** — | **Found by:** round 136 — choosing which guard `UX-934`'s ledger adopt job runs; `make test-touching` on a `tests/flake_ledger.json` edit selects 31 files and not the one that reds | **Serves:** every session whose inner loop is `make test-touching` on a change to a committed record | **Topic:** guards | **Area:** tools | **Shape:** judgement

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
