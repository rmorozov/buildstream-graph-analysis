# UX-936: a heavy-fixture guard excurses three times on a record that is not too low, so the ledger is reading the runner

**Flake:** tests/unit/test_the_view_parses_nothing.py
**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691, UX-442 | **Blocks:** — | **Found by:** round 136 — `408235c7` appended run 35755437814's excursions and took this file to `EXCURSION_FLOOR`, reddening `main` on `test_a_file_with_three_excursions_has_a_filed_task.py` for every branch | **Serves:** every branch whose push gate reads a suite `main` has already reddened, and the next reader of the ledger | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`tests/unit/test_the_view_parses_nothing.py` reached the floor, and it
is **not** `UX-929`'s shape. That row's files are population-sized
guards whose committed record is too low; this one's record is if
anything too high:

```text
tests/ci_reference.json    files 8.91   samples [8.91, 8.91, 8.91, 8.91, 7.38]
ledger, none confirmed     34888036702 x1.988  35536366563 x2.386  35755437814 x1.713
```

The one real reading in the window is **7.38 s** against a committed
8.91 — the file is faster than its record, not slower. So the three
excursions are not a record lagging a growing population. They are
three runs where this file took 15-21 s, a month apart, with no two
consecutive runs agreeing, which is `UX-442`'s definition of
unconfirmed.

What the guard does is the likely reason. `UX-296` built it to catch a
2 GB snapshot killing `bga view`, so it **writes a store with a
million process records** and then starts `bga view` in a subprocess
against it. The work is dominated by building and reading that fixture,
not by the assertion. A runner whose disk is slower moves that cost in
a way a CPU-bound guard's is not moved, and `shift_of` compares against
a median taken on other runners.

So the hypothesis is about the instrument, not the file: the drift gate
reads one number per file per run and cannot tell "this file got
slower" from "this runner's disk was slower for the files that touch
it". If that is right, the fixture-heavy guards should excurse
*together* on the same run ids, and 35755437814 put six files over at
once — which is the cheap test and is not yet run.

## Required Fix

Read the ledger's run ids as a population rather than per file: for
each run that appears, how many files excursed on it, and whether the
files that did are the ones with the heaviest fixtures. Say which of
the two readings the data supports — a genuinely variable file, or a
per-run signal the per-file gate is reporting as per-file drift — and
either file the per-run finding or record this one as a file to leave
alone with the reason beside it.

Do not re-record the entry to make the excursions stop: 7.38 against
8.91 says the record is already right, and raising it would hide the
next real regression by exactly the margin raised.

## Out of Scope

`UX-929`'s three files, whose records *are* too low and whose fix is a
refreshed reading. `UX-934`'s unchecked adopt commits, which is how
this reached `main` rather than a pull request.

## Acceptance Test

A reading of the ledger grouped by run id, pasted with the command that
produced it, showing for run 35755437814 and the other run ids here how
many files excursed and which; and a stated verdict on whether
`test_the_view_parses_nothing.py`'s three excursions share their runs
with other fixture-heavy files. If they do, the per-run finding is
filed with its own guard; if they do not, this file gets a `declared`
reason in the ledger naming the measurement that cleared it.

## Outcome
