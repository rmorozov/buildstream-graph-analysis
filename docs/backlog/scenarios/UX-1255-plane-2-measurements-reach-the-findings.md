# UX-1255: 39,854 Plane 2 processes produce no finding

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B3, filed at Ruslan's request | **Serves:** R1, R2, R5 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_plane_two_reaches_the_findings.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B3).

The 14 findings are all Plane 1 or graph findings (`wait-category` ... `efficiency-score`). Plane 2 measured that `make` is the costliest binary (36.0 s of CPU in 2,400 elements), that building elements draw 0.21 cores each, and that configure is 0.0% of CPU. Each of these is in a section, and none reaches the findings or the decision, so a reader of the first screen never learns that Plane 2 ran.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     new `_plane2_findings(result)` on result.plane2_report: costliest binary from 1247's binary_totals; elements whose cores busy is below a named fraction of requested jobs (per_element_parallelism); configure's share above a named line. Each carries section, step, FINDING_READERS entry.
Rejected:  new Plane 2 measurement (out of scope); reading viewer sentences.
Files:     bga/findings.py (new fn, compute_findings :2128, FINDING_READERS :87); reads bga/plane2.py from 1247.
Guard:     tests/unit/test_plane_two_reaches_the_findings.py — macro_micro: binary finding cpu_us == by_binary[0].cpu_us; Plane 1-only golden emits none.
Mutation:  function returns [].
Class:     product
Split:     after 1247 and 1256.
```

## Required Fix

Where Plane 2 covers the run, the analysis emits findings from it with the same bounds as Plane 1's: the binary that costs most CPU, elements whose cores busy is far below their requested jobs (waiting, not computing), and configure's share when it is material. Each finding names its numbers and links its section.

## Out of Scope

New Plane 2 measurements; the per-binary table (UX-1247).

## Acceptance Test

On this page at least one finding cites a Plane 2 figure equal to its section's; a Plane 1-only run emits none of them. Mutation: gate the findings off, and the guard reds on this page only.

## Outcome

The gap measured, on the Motivation's page (`gen-synthetic --store --seed 1 --layers 40 --width 60 --workload binaries`,
`capture report` on the newest snapshot), `bga analyze @last --format json` at `c98a8e3d` with `_plane2_findings`
gated off (`scratchpad/<worktree>/accept.py before`):

```text
before 14 findings; Plane 2 ones: []
  by_binary[0] make cpu_us 36,000,000; configure_share 0.0
  element_join rows under 1.25 with jobs > 1: 2,300, median 0.17054389866718134
```

The close measured, same page and probe (`accept.py after`):

```text
after 16 findings; Plane 2 ones: ['jobs-waiting', 'costliest-binary']
  costliest-binary '36.0 s of CPU in make, the costliest of 601 binaries, across 2,400 elements' -> #by_binary
  jobs-waiting '2,300 elements asked for 4 jobs and ran at a median 0.17 cores busy: waiting, not computing' -> #element_join
  equal: True True    (evidence cpu_us = by_binary[0].cpu_us; element_count = the join's rows under the line)
macro_micro (export, the volume guards' instruments), before -> after: data half 100,075 -> 100,075 B,
  opened height 39,346 -> 39,346 px, words 13,162, controls 872, nodes 6,889 - unchanged: no Plane 2 finding fires there
golden (Plane 1 only): none of the three
```

The lines. `PLANE2_BINARY_FLOOR_SHARE` is `OPPORTUNITY_FLOOR_PCT` (1%): a binary under Plane 1's own floor for a
wait category is noise, and `make` at 1.5% of 601 binaries' CPU clears it. `jobs-waiting` reads each element's own
CPU over its own wall - `correlate._plane2_view`, the `element_join` row's `cores_busy` - and reuses
`correlate._COMPUTE_BOUND_CORES` (1.25), so it and `bga correlate`'s "waiting, not computing" never disagree on one
run; only elements that asked for more than one job count, a `-j1` element being `pinned_to_one_job`'s finding. A first
cut divided run-wide `cores_busy` by builders, a proxy (fixing guide §5): 0.98 on the heavy run, which is 3.9 cores
busy. On `macro_micro` every multi-job element ran at 1.38+ and `core.bst` (0.90) asked for one: nothing fires.
`PLANE2_CONFIGURE_SHARE` 0.10: one CPU second in ten re-deriving the build system, `TRANSFER_SHARE_NOTABLE`'s line
for the other non-build cost.

| mutation | reddened | count |
|---|---|---|
| `_plane2_findings` returns `[]` | binary, waiting, line, configure[0.1] | 4 failed, 4 passed |
| binary reads `rows[1]` | binary row zero | 1 failed, 7 passed |
| waiting `<` -> `<=` the line | the line is correlate's | 1 failed, 7 passed |
| `requested_jobs > 1` gate dropped | line/one-job; macro_micro emits none | 2 failed, 6 passed |
| median -> mean | join rows and their median | 1 failed, 7 passed |
| configure `>=` -> `>` | configure[0.1] | 1 failed, 7 passed |
