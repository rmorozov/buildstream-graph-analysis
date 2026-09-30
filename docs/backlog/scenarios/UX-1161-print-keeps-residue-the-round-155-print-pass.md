# UX-1161: print keeps residue the round-155 print pass left

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

Print at 794 px, `emulateMedia({media: 'print'})`: one SQL code line in `#perfetto-questions` runs to x=846; the "I am" label prints with no control; closed-fold markers "▸ Why #1" print above open content; 187 `.description` nodes, 16 visible in print (unopened descriptions never reach paper); rows held back by a table or card limit print only their count; at 390 in print 18 plain code elements overflow the right edge (pre-existing).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each named print defect is gone: code wraps inside the sheet, a label prints only with its control, no fold marker prints over open content, unopened descriptions and held-back rows print or say what is held.

## Out of Scope

The screen layout; the fold-more control (intended by `UX-1154`).

## Acceptance Test

In print at 794 px and 390 px no element's right edge passes the sheet, no control-less label prints, and every description and held-back row is on paper or counted. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
