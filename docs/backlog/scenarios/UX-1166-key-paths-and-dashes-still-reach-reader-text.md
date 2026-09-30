# UX-1166: key paths and dashes still reach reader text

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

`#document_shape` shows the raw key path "findings.[].evidence.blast_radius_distribution.deciles.p10"; " - " appears 140 times as a dash; null values print as dashes (`UX-1159`'s guard reads the page part at 1440 only).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The path reads as the label a reader knows, and neither " - " nor a null dash stands for a value.

## Out of Scope

The schema descriptions `UX-1159` fixed.

## Acceptance Test

At 1440 and 390 no reader text contains a key path or a spaced hyphen dash. Mutation: restore one, and the guard reds.

## Outcome

Open.
