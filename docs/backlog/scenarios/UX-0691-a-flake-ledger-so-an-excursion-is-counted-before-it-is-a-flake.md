# UX-691: a flake ledger, so an excursion is counted before it is a flake

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-442 (two-run confirmation), UX-495 (browser guards under load), UX-496 | **Serves:** the round reading a red gate on a file nobody touched | **Topic:** guards

## Motivation

```text
grep -in "flake\|excursion" tests/ tools/     39 hits, in code and comments
a ledger file                                 none (docs/audits/round-8*.md, round-9*.md: 0 hits)
```

The drift gate confirms over two runs and the browser family was
measured over six CI runs (`UX-495`), and the outcome of each
excursion lives in whichever task file happened to record it. A
file that excurses monthly and a file that excursed once look the
same to the next round.

## Required Fix

`tests/flake_ledger.json`, appended by the drift gate's CI step for
every unconfirmed excursion and every confirmed drift (file, run id,
shift, confirmed?), adopted like the tier reference; a guard that a
file with ≥ 3 excursions in the ledger has a filed robustness task or
a declared reason; the round document's Standing prints the ledger's
top three.

## Out of Scope

- Re-running to make a file quiet — the ledger counts; the task
  fixes.

## Acceptance Test

Two synthetic excursions of one file in the ledger and a third —
the guard names the file; mutation: drop the adopt step — the
ledger stops growing and the census guard reds.
