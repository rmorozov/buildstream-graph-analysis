# UX-1275: the page says 2,300 elements wait rather than compute, and nothing says what they wait in

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B2 | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_binary_that_waits_is_told_from_one_that_computes.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B2).

The `jobs-waiting` finding reads "2,300 elements asked for 4 jobs and ran at a median 0.17 cores busy: waiting, not computing", and its step is "Find what these elements wait on". `by_binary` publishes CPU and wall per binary, but make's wall (2.9 h against 36.0 s CPU) is the sum of its children's lifetimes, so wall minus CPU cannot rank where time is blocked. Plane 2 has each process's own CPU and lifetime; the self time a process spends neither computing nor waiting on a child is the quantity the step asks for.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Route:     a streaming `_BlockedTime` fold in the tracer (beside `_ConfigurePhase`'s sandbox+pid parent map) gives each process lifetime - own CPU - union of live-child intervals clipped to its lifetime (pid reuse resolved by the parent whose span holds the child's start); `binary_cost[e].binaries[]` gains `blocked_us`, `plane2.binary_totals` sums it with `blocked_share` (of the binary's own wall), `by_binary` draws a Blocked column beside CPU (rank stays CPU), and `jobs-waiting`'s step names the top 3 binaries by blocked time among the waiting elements.
Rejected:  wall - CPU (make's 2.9 h is its children's - the bug the row names); off-CPU sampling (out of scope); a plane2/v4 bump (additive key; v3's precedent bumps on removal only); re-ranking by_binary by blocked (CPU is the cost answer UX-1247 fixed).
Files:     tools/bst_native_build_tracer.py, bga/plane2.py, bga/findings.py (_plane2_findings jobs-waiting step), bga/schemas.py (by_binary column + property), bga/disclosure.py (binaries[].blocked_us), tests/unit/test_a_binary_that_waits_is_told_from_one_that_computes.py
Guard:     fold on hand-built records (make 100 s life, 1 s CPU, children live 90 s -> blocked 9 s) and on the `--workload binaries` two-plane page: make's blocked_us < its wall - CPU, and the jobs-waiting step names a binary in by_binary's blocked top 3; a report without blocked_us leaves the column absent, not zero.
Mutation:  blocked = duration - cpu_us (drop the child-interval subtraction): the make assertions red.
Class:     product
Split:     one track; the tracer fold and the page/finding half are one claim, do not split.
Question:  Default taken; Ruslan may reverse: additive `blocked_us` under plane2/v3, no schema bump (reverse = plane2/v4 with v3 in SUPERSEDED). If dev_sizes/page budget reds on the new column, the track raises it by the measured bytes and pastes them.

## Required Fix

Plane 2's report publishes, per binary, blocked time (lifetime minus own CPU minus time with a live child) and its share; the page ranks it beside CPU, and `jobs-waiting`'s step names the top blocked binaries.

## Out of Scope

New capture mechanisms (off-CPU sampling); the jobserver.

## Acceptance Test

On this page make's blocked time excludes its children's lifetimes and the jobs-waiting step names at least one binary from that ranking. Mutation: compute blocked time as wall minus CPU, and the guard reds on make.

## Outcome

**Gap measured** (`gen-synthetic --seed 1 --store --runs 2 --workload binaries --layers 40 --width 60`, 2,402 elements, `bga capture report --json` on the newest snapshot: 39,854 processes, 601 binaries): `by_binary`'s make row was `wall_us` 10,369,732,000 against `cpu_us` 36,000,000 and nothing else; the jobs-waiting step read "Find what these elements wait on before raising their job count."

**Close measured** (same page): make `blocked_us` 7,406,439,126 (2.06 h), `blocked_share` 0.714, against wall minus CPU 10,333,732,000; `by_binary` draws Blocked and Blocked share beside CPU, rank unchanged (make, uniform-421, ...). Step: "Start with what make (2.1 h), uniform-096 (18.6 s) and uniform-086 (17.7 s) wait on: the most time these elements spent alive, off CPU and with no child running." Hand-built: make 100 s, 1 s CPU, children live 5-95 s -> 9,000,000 us. `pytest tests/unit/test_a_binary_that_waits_is_told_from_one_that_computes.py` -> 5 passed.

Report cost (`bga capture report --json` on that log, 3 runs each, fresh child, `ru_maxrss`; 4 cores shared with five tracks, so wall is noisy): before 4.05/3.00/3.92 s, 150/152/152 MB; after 4.24/4.90/4.17 s, 157/157/157 MB. The fold alone (tracemalloc): 4,693 kB held after the stream (120 B/process: 20 B of arrays, the rest the 21k-pair (element, binary) index), 6,028 kB peak in `finish`. Sandbox, pid, ppid and CPU are read from `_ConfigurePhase`'s rows, not kept twice.

| Mutation | Reddened | Printed |
|---|---|---|
| `blocked = life - cpu` (drop the child-interval subtraction) | make 9 s, recycled pid, page make (5,279,388,513 < 0.9 x 5,279,412,000 fails) | 3 failed, 2 passed |
| parent = latest occupant of the pid, no span check | `test_a_recycled_pid_bills_the_occupant_alive_at_the_childs_start` (sh 20 s, not 12 s) | 1 failed, 4 passed |
| jobs-waiting step back to the fixed sentence | `test_the_waiting_step_names_a_binary_from_the_blocked_ranking` | 1 failed, 4 passed |
| `binary_totals` sums an absent `blocked_us` as 0 | `test_a_report_without_blocked_time_leaves_the_column_absent` | 1 failed, 4 passed |
| step ranks by `cpu_us` (verifier round; file now 7 tests) | `test_the_waiting_step_names_the_waiting_elements_top_three_by_blocked_time` (cc1, ld, make) | 1 failed, 6 passed |
| step reads every element, not the waiting ones | same (zzz, make, sh) | 1 failed, 6 passed |
| unparented children not collected | `test_a_child_whose_parent_was_missed_is_counted_where_blocked_time_is_published` | 1 failed, 6 passed |
| each sandbox's root counted as unparented | `test_make_waits_nine_seconds_not_ninety_nine` (root-only element gains the key) | 1 failed, 6 passed |

Verifier round: a child whose ppid names no recorded process is not subtracted from its real ancestor (make reads 99 s of 100 s blocked in the hand-built case). Counted, not re-attributed: `binary_cost[e].blocked_unparented` (processes with no recorded parent beyond each sandbox's earliest), and `by_binary.blocked_us`'s description calls blocked time an upper bound for that reason.
