# UX-564: Parts 23 and 27 exist in the spec and nowhere else

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Serves:** the maintainer deciding the spec's edge | **Topic:** analysis

## Motivation

```text
$ git grep -il "resource_mix\|CACHE_IO\|wait_to_execution\|wait_share" -- bga tests docs/backlog
bga/findings.py  bga/schemas.py   (both `largest_wait_share`, a different quantity —
                                   round 83: the grep names two files, not one)
specification.md:1175-1202   Part 23, wait-to-execution ratio
specification.md:1338-1370   Part 27, resource mix
specification.md:1619-1625   both listed as `signals` keys of analysis/v9
bga/analyzer.py:1434         never writes either
```

No row, tracker line or comment records a decision to drop them; the
progress tracker's "backlog complete" line does not mention them.
They are the only two analysis Parts with nothing behind them.

## Required Fix

Decide, and record it in Part 32: implemented (two `signals` keys,
an addition under `UX-190`, with the guard the spec's 36.x pattern
gives every other Part) or declined (a registry note naming both
Parts as not published, so the next spec review does not find them
again).

## Out of Scope

- The other `signals` keys — ~~verified present~~. **Round 83 falsified
  this by re-measuring.** Of 32.4's ten declared keys only four appear
  verbatim in what the analyzer publishes (`ready_queue`,
  `criticality_probability`, `blast_radius`, `fetch_build_overlap`);
  three are published under another name or in another section
  (`wall_clock_share`→`wall_clock_share_us` by `UX-345`,
  `leaf_critical_tasks`→`leaf_analysis`,
  `concurrency`→`occupancy['average_concurrency']`); and
  `duration_variability` is computed and reaches no consumer. The claim
  that Parts 23 and 27 are the only two with *nothing* implemented
  still holds — the other eight all compute something. 32.7.2 records
  the whole mapping so the next review does not re-derive it.

## Acceptance Test

The registry says which, and a guard reads the `signals` key set
against the registry's list.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Declined**, and recorded in spec Part **32.7.2**. Nothing computes
either quantity; the two Parts stay as design intent and publish
nothing.

```text
$ git grep -il "resource_mix\|CACHE_IO\|wait_to_execution\|wait_share" -- bga tests docs/backlog
bga/findings.py
bga/schemas.py
docs/backlog/scenarios/UX-0564-...md
$ git grep -in "resource_mix\|CACHE_IO\|wait_to_execution\|wait_share" -- bga/schemas.py bga/findings.py
bga/findings.py:1110:                      'largest_wait_share': pct / 100},
bga/schemas.py:1429:    "largest_wait_share": ("share",
```

Two files, not the one the Motivation named, and both are
`largest_wait_share` — the different quantity it already excluded. The
finding stands.

**A premise falsified: "the other `signals` keys — verified present".**
Measured against a real run plus every literal `signals[...]` store
site in `bga/`:

```text
$ python3 -c "sorted(analyze_run('tests/fixtures/macro_micro/run').signals)"
live 19   stored 11   union 20   stored-only ['fetch_build_overlap']
```

Four of 32.4's ten declared keys appear verbatim; three are published
under another name or in `occupancy` rather than `signals`; and
`duration_variability` is computed and read by nothing. Only *Parts 23
and 27 have no implementation at all*, which is the filing's real
claim. The Out of Scope line above is corrected in place, and 32.7.2
carries the whole ten-row mapping so the guard can read the key set
against it rather than against two names.

| mutation | applied to | reddened | run |
|---|---|---|---|
| an eleventh key `a_new_signal` in 32.4's block | `specification.md` | `test_every_declared_key_has_a_row_in_the_registry_order` — `assert 11 == 10` | 1 failed, 3 passed |
| `signals['ready_queue']` → `signals['ready_queue_depth']` in the mapping cell | `specification.md` | `test_each_row_pointing_at_signals_points_at_a_real_key` | 1 failed, 3 passed |
| `// wait_to_execution_top` prepended to a viewer module | `bga/viewer/chapters.js` | `test_no_module_computes_a_declined_signal` only | 1 failed, 3 passed |
| `signals['critical_path' + '_resource' + '_mix'] = {}` — published, but the literal is in no source file (`grep -c` = 0) | `bga/analyzer.py` | `test_neither_declined_key_is_published` only; the text scan was blind to it, which is the discrimination between the two | 1 failed, 3 passed |

All reverted; `4 passed in 0.64s`.

**A guard of mine that did not discriminate, and was deleted.**
`test_the_rows_that_point_at_signals_are_not_the_declined_ones` asserted
`"signals[" not in cell` when `cell == "declined"` and `cell !=
"declined"` otherwise — both tautologies of the branch that selected
them. It could not fail for any content of the table. Removed rather
than repaired; the two claims it gestured at are held by the two
declined-part tests above, which read the code.

**Acceptance Test** — "the registry says which, and a guard reads the
`signals` key set against the registry's list":

```text
$ PYTHONPATH=. python3 -m pytest tests/unit/test_the_declared_signals_are_the_published_ones.py -v
...TestTheTableIsTheDeclaredBlock::test_every_declared_key_has_a_row_in_the_registry_order PASSED [ 25%]
...TestEveryPublishedRowNamesAKeyTheToolWrites::test_each_row_pointing_at_signals_points_at_a_real_key PASSED [ 50%]
...TestTheDeclinedPartsReachNothing::test_no_module_computes_a_declined_signal PASSED [ 75%]
...TestTheDeclinedPartsReachNothing::test_neither_declined_key_is_published PASSED [100%]
============================== 4 passed in 0.61s ===============================

$ make test-touching
19 file(s) selected · 423 passed, 4 skipped in 9.39s
```

**Deviation:** the published set is a real run's keys plus the literal
store sites, so a key stored under a name computed at runtime is
invisible to the AST half — mutation four is exactly that case, and the
live half caught it. No fixture in the tree produces
`fetch_build_overlap`, which is why the AST half is there at all.
