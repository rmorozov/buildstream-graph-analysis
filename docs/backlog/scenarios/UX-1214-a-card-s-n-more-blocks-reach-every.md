# UX-1214: a card's +N more Blocks reach every element it counts

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P8 (pre-existing): the toolchain card's "Blocks:" lists 40 links then "+1,160 more" as a plain span; the rest is unreachable from the card.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The +N more is a link to the rest, as a binaries +N more lands on binary_cost filtered (`UX-1183`).

## Out of Scope

The Blocks list's bound (`UX-1200`, closed).

## Acceptance Test

toolchain's +1,160 more is a link whose target shows 1,160 more elements; a guard beside `UX-1200`'s Blocks guard. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
