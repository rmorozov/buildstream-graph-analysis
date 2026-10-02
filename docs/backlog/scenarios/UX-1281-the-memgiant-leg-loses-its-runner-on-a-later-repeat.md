# UX-1281: the memgiant Graviton leg outlives its runner on the third repeat, and its readings die with it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** round 166's Graviton re-reads of UX-1134 (bga-bench runs 37022814276 and 37031346135, 2026-10-02) | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** owner:CodSpeed Graviton

**Guard:** none — open, no guard named yet

## Motivation

With UX-1134's idle hold in, memgiant's first `autocap` arm completes
(run 37031346135, read from the job log by the owner):

```text
autocap wall 562.87s cpu 3286s mem 26915M giant-peak 10 ... rssw 1004
off     wall 559.74s cpu 3185s mem 21557M giant-peak 8
```

The owner read run 37022814276's log as well: two more autocap
repeats completed (560.26, 560.45 s, rssw 1007, 1009), and the job
ended at its time limit before the arms' exit notices. Both
memgiant jobs ended 69 minutes after they started, each with one
annotation and no arm notice:

```text
The self-hosted runner lost communication with the server.
```

Three repeats of two ~560 s arms plus ~4 min of staging is ~60 min of
a 69-minute life, so time, not memory, took the runner (inferred from
the walls, not measured). The arms write their notices only at exit,
so a job that dies keeps every reading it made in the log alone, and
GitHub serves no log for a lost job (`get_job_logs` 404).

## Decomposition

Input classes: the memgiant leg's three repeats on CodSpeed Graviton
(16 A72, 31 GB, no swap). Journey: UX-1014's shape x host x arm table.

## Required Fix

The memgiant leg fits the runner's time (fewer repeats, or the leg
split across jobs), and each build's line becomes a notice as the
build ends, not one per arm at exit.

## Out of Scope

The pool's gate itself (UX-1134), unless a repeat's memory reading
says the gate let the build past its reserve.

## Acceptance Test

A memgiant run whose job completes with every repeat's notice, run id
pasted.

## Outcome
