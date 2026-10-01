# UX-1205: a real capture of fake sleeping binaries under the LD_PRELOAD hook

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Owner follow-up of `UX-1182`'s route (b), unanswered: `UX-1182` generates the binaries workload synthetically (112 elements, top-8 200-500 binaries); no capture has run fake sleeping binaries under the LD_PRELOAD hook. It needs a BuildStream host and cannot gate CI (runs158.md DECISION).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A captured run of fake sleeping binaries under the hook, on a BuildStream host, whose page matches the synthetic workload's shape.

## Out of Scope

CI gating; the synthetic generator (`UX-1182`).

## Acceptance Test

A `bst`-marked test drives the capture and compares calls per element to the plan; a guard in a new `test_a_captured_workload_matches_its_plan.py`, skipped off a BuildStream host. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
