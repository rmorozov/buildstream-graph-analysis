# UX-955: a population entry keeps the tree size its seconds no longer describe, so the gate scales the growth twice

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-716, UX-803, UX-924 | **Blocks:** — | **Found by:** round 138 — `UX-929`'s reading: `c2fbf2b6` restarted `test_docs_links_and_commands.py` at 34.03 and left its `population` at 737 | **Serves:** every branch that makes the backlog guard slower, which the gate should name | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-716` defines `population` as each entry's tree size "when its
seconds were last set", and `against` scales `expected` by
`population_size() / population`. Since `UX-924`, `adopt` sets the
seconds on every push to `main`, and it never writes `population`:

```text
$ git show <sha>:tests/ci_reference.json    # docs_links: files [samples] population
ad666b2c^   18.54 [18.54, 18.54, 18.55, 18.54, 18.54]   737
c2fbf2b6    34.03 [34.03]                               737   # UX-803 restart
dcbe4615    34.03 [34.03, 35.29]                        737
backlog now (dev_close_task._backlog_counts()['scenarios'])  942
```

34.03 was read on a tree of 934 rows, and is then scaled by 942/737 =
1.28 as if it had been read on 737. Measured with `against()` on the
committed reference, every other file at its record (shift 1.0):

```text
docs_links reading   ratio to 34.03   verdict
50.0 s               x1.47            ok
60.0 s               x1.76            ok
65.0 s               x1.91            ok
66.0 s               x1.94            drift
60.0 s, population set to 942         drift
```

So a 1.9x regression of the backlog guard reads `ok` today, and the
slack grows with every row filed. `test_a_guard_reads_only_what_a_clone_has.py`
has the same shape: `population` 496 against 582 test files now, while
its seconds are re-added by each adopt from a run on the bigger tree.

## Required Fix

Keep `files` and `population` describing the same tree: either `adopt`
normalises each reading to the recorded population before it enters
`samples`, or it records the population beside each sample and
`against` scales by the one `files` came from. Say which, with the
number that chose it. `adopt`'s own `UX-803` step check reads
`over_gate` without the population — say whether that is right too.

## Out of Scope

Which guards belong in `POPULATION_CLASS` (`UX-929`'s Outcome: the
backlog guard's cost per row grew 1.45x, so the population is not its
whole cost). `EXCURSION_FLOOR` and the drift constants.

## Acceptance Test

On the committed reference, a `test_docs_links_and_commands.py`
reading 1.6x its `files` on the current tree is reported by `against`;
a mutation that drops the fix (population left at its recorded value
while `files` moves) reddens a guard that says so.

## Outcome
