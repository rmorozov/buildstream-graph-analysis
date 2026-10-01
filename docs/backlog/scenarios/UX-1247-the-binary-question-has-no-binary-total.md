# UX-1247: "Which binaries cost this build its time?" has no per-binary total to answer with

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M2 | **Serves:** R1, R2, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_binary_question_has_a_binary_total.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M2).

`#binary_cost` answers "make cost the most, 2,400 calls, 36.0 s of CPU" over a table of 21,064 element x binary pairs whose top row is `lognormal-223` in one element; `make` is not on its first page. `#by_binary` is the only per-binary table and carries calls alone (`{"make": 2400, ...}`). A reader asking which tool to speed up must sum 21,064 rows by hand; the page never shows the CPU, wall or element count behind its own answer sentence.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     bga/plane2.py gains `binary_totals(native_report)`: sums `binary_cost` per binary into `{binary, cpu_us, wall_us, calls, elements}` rows ranked by CPU, calls from the capture's `by_binary`; report/json.py publishes them AS `by_binary` (breaking: analyze/v7); the pair table stays the drill-down.
Rejected:  a second `binary_totals` key (one population published twice, UX-288); totals written by the tracer (stored plane2.json lacks them, UX-996); grouping in the viewer (a second analyzer, Direction 7).
Files:     bga/plane2.py, bga/report/json.py:534, bga/schemas.py:402,:4810 (v7 + architecture.md:395 row), bga/disclosure.py:448, bga/viewer/sections.js:788 (answer sentence reads by_binary[0]), tests reading `by_binary` as a map (~25 files).
Guard:     tests/unit/test_the_binary_question_has_a_binary_total.py — macro_micro and a constructed report where make has most calls but cc most CPU: row 0 is the CPU leader, cpu_us = sum of its pair rows, answer sentence names it.
Mutation:  rank by calls; restore the sum in sections.js.
Class:     product
Split:     one track. Old reports with only top-N by_cpu leave cpu_us absent, not partial.
Question:  none; v7 bump is the reversible default.
```

## Required Fix

Plane 2's report publishes per binary its CPU, wall, calls and element count, ranked by CPU; `#by_binary` (or `#binary_cost`'s opening view) draws that table, and the pair table stays the drill-down.

## Out of Scope

The pair table's paging (`UX-1185`); real-capture fixtures (`UX-1205`).

## Acceptance Test

On this page the first row of the per-binary table is the binary the answer sentence names, with its CPU equal to the sum of its pair rows. Mutation: rank by calls, and the guard reds.

## Outcome

The gap measured, on the Motivation's page (`gen-synthetic --store --seed 1 --layers 40 --width 60 --workload binaries`,
`capture report` on the newest snapshot: 39,854 processes, 601 binaries), exported at `92a48946` and read in Chromium at
1440 and 390 (`scratchpad/<worktree>/accept.py`):

```text
before  by_binary heads ['Binary', 'Calls in run']   first row make   cpu (none)
        binary_cost answer: "601 binaries ran in 2,400 elements; make cost the most, 2,400 calls, 36.0 s of CPU ..."
```

The sentence's 36.0 s existed only as a browser-side sum of 21,064 pair rows; `by_binary` was `{binary: calls}`.

The close measured, same page and probe, both widths:

```text
after   by_binary heads ['Binary', 'CPU', 'Wall', 'Calls in run', 'Elements']   first row make   cpu 36000000
        binary_cost answer: "601 binaries ran in 2,400 elements; make cost the most, 2,400 calls, 36.0 s of CPU in 2,400 elements."
        make's binary_cost pair rows: 2,400, cpu_us sum 36,000,000 = by_binary[0].cpu_us
page    1,418,423 -> 1,424,690 B; page half 159,875 -> 159,859 B (PAGE_BUDGET_B 165,000); data half +6,283 B
```

`analyze/v7`: `by_binary` changed shape, `analyze/v6` joins `SUPERSEDED` (schemas, run_store, README, spec Part 32,
architecture.md row and log, cli.md, CHANGELOG Unreleased row `breaking`); both committed analyses regenerated with
`dev_refresh_analysis.py --write` (schema id and `document_shape` leaf counts only). macro_micro's `plane2.json`
carries the two top-5 rankings only, so its rows publish calls alone, ranked by calls, and the sentence says "ran
the most" without a CPU figure.

| mutation | reddened | run printed |
|---|---|---|
| `binary_totals`: rank by calls (`-calls, binary`) | row order `make` first; answer and first row name `make` | 2 failed, 2 passed |
| `sections.js`: restore the pair sum in `binary_cost`'s answer | answer reads "6 calls" (pair rows), not by_binary's 9 | 1 failed, 3 passed |
| reverted, each | | 4 passed |

`test_no_document_serves_a_retired_contract.py` now stops at a `## Verification Log` heading: the log is
append-only (`UX-653`) and 16 of its entries name `analyze/v6`; dropping that cut reddens 17 findings.

The macro_micro clause compares the payload with `binary_totals` itself, so it guards the projection, not the
ranking; the constructed report is what discriminates.

