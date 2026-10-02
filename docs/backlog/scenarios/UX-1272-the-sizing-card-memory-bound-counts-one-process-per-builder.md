# UX-1272: the sizing card calls builders x one process's peak "at most", while an element runs many processes at once

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-164 view UI re-review on a 2,402-element two-plane page (2026-10-02), finding R3 | **Serves:** R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `319539f0`, Chromium 1440x900 and 390x844 (view UI review, round 164, `view-ui-review/round-164/review.md` §R3).

`#agent_sizing` reads "Memory: at most 256.0 MiB, if all 4 builders peak together at 64.0 MiB (process peak)". 64.0 MiB is the largest single process (`#peak_memory` says it is deliberately not summed), but an element runs several at once: Plane 2 saw up to 33 alive together and every element asked for 4 jobs. So 256 MiB is a floor for four simultaneous peaks, not a ceiling, and "at most" is the wrong direction. An agent sized from it can OOM (cf. UX-1134).

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The memory line reads as what it is (a per-process peak per builder, a lower bound) or is computed from a measured concurrent quantity (per-element peak of summed RSS across live processes, or processes alive at once x process peak) with its direction stated.

## Out of Scope

New memory sampling (host series); the cores and builders lines.

## Acceptance Test

On this page the memory line does not say "at most" over builders x process peak; where a concurrent bound is published, its value is at least that product. Mutation: restore "at most", and the guard reds.
