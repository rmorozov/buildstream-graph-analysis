# UX-1250: next-step commands carry a 100-character absolute run path

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), finding M5 | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §M5).

"What should I run next?" hands over `bga blast layer24/mod011.bst /tmp/.../big/.bga/runs/20260303T091500Z/run`: scroll width 1,246 px in a 288 px box at 390, so the reader sees "bga blast layer24/mod011.bst /tm". Three of five commands carry the path; the fifth already uses the alias grammar (`bga compare @prev @last`). On an exported page the path is the capturing machine's, so it cannot run elsewhere either.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A next-step command names the run by its snapshot id (or `@last` when it is the newest) and the project with `--project` only when it is not the working directory, as `bga compare` already does.

## Out of Scope

The command shape (§1d).

## Acceptance Test

On this page every next-step command is at most 60 characters and none contains `/.bga/runs/`; pasted in the store's project directory each resolves the same run. Mutation: restore the absolute path, and the guard reds.
