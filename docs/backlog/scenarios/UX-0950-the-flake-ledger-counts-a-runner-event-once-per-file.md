# UX-950: the flake ledger's excursions cluster by run, and the census counts a runner event once per file

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-691, UX-936 | **Blocks:** — | **Found by:** round 138 — `UX-936`'s reading of `tests/flake_ledger.json` grouped by run id | **Serves:** the next round whose push gate reads a file the census names, and the reader of the round document's Standing | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`dev_flake_census.py` counts ledger rows per file. The rows are not
independent per file: grouped by run, they cluster.

```text
# tests/flake_ledger.json at dcbe4615, grouped by run_id; 20,000 draws per N
runs with >=1 excursion: 21 entries: 44 files per run: {1: 8, 2: 6, 3: 6, 6: 1}
N=37: observed VMR 1.58, zero-runs 16, max 6; independent files: P(VMR>=obs)=0.0029 P(max>=obs)=0.0211 P(zeros>=obs)=0.0435
N=58: observed VMR 2.01, zero-runs 37, max 6; independent files: P(VMR>=obs)=0.0001 P(max>=obs)=0.0030 P(zeros>=obs)=0.0046
```

`N` is the runs that could have written a row: 58 `CI` push runs on
`main` from the ledger's first run id on (the Actions runs API, 31
`success`, 27 `failure`), and 37 counting only those known to reach the
gate (31 green plus 6 red ones that did write rows). Each file is drawn
as an independent Bernoulli at its own ledger rate, 20,000 times: a
Poisson-binomial's variance-to-mean is below 1, and the ledger's is
1.58-2.01. Run 35755437814 put six files over at once.

So some runs are slow for several files at once in a way the run's
median shift does not divide out, and the census reads each such run as
one excursion for every file it touched. `UX-936` showed it is not the
fixture-heavy files moving together (that row's Outcome); what does
move together is not named yet — candidates are `-n auto`'s
co-scheduling (which heavy files share a worker and a minute) and a
runner-level cost such as `UX-944`'s 910 MB clone, whose dear mode
fell on two of the five post-`UX-924` adopts.

## Required Fix

Give the census a per-run reading: files per run, and which runs are
improbable under independent files at the ledger's own rates, printed
beside the per-file Standing. Then decide, with that reading, whether a
row from such a run counts toward `EXCURSION_FLOOR` as a file's own
excursion. The count of runs `N` needs a source the census can read
offline; the ledger records only runs that wrote a row.

## Out of Scope

`EXCURSION_FLOOR`, `CI_DRIFT_FACTOR`, `CI_DRIFT_SECONDS`. The files
`UX-890`, `UX-917` and `UX-936` closed.

## Acceptance Test

A unit test on a synthetic ledger with one run of six files and
eighteen runs of one: the census names that run and not the others, and
a mutation that drops the per-run reading reddens it. The real
ledger's reading pasted with its command.

## Outcome
