# UX-1275: the page says 2,300 elements wait rather than compute, and nothing says what they wait in

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), brainstorm B2 | **Serves:** R1, R2 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §B2).

The `jobs-waiting` finding reads "2,300 elements asked for 4 jobs and ran at a median 0.17 cores busy: waiting, not computing", and its step is "Find what these elements wait on". `by_binary` publishes CPU and wall per binary, but make's wall (2.9 h against 36.0 s CPU) is the sum of its children's lifetimes, so wall minus CPU cannot rank where time is blocked. Plane 2 has each process's own CPU and lifetime; the self time a process spends neither computing nor waiting on a child is the quantity the step asks for.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Plane 2's report publishes, per binary, blocked time (lifetime minus own CPU minus time with a live child) and its share; the page ranks it beside CPU, and `jobs-waiting`'s step names the top blocked binaries.

## Out of Scope

New capture mechanisms (off-CPU sampling); the jobserver.

## Acceptance Test

On this page make's blocked time excludes its children's lifetimes and the jobs-waiting step names at least one binary from that ranking. Mutation: compute blocked time as wall minus CPU, and the guard reds on make.
