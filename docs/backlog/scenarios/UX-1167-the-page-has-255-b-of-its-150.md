# UX-1167: the page has 255 B of its 150,000 B budget left, and every viewer row now pays with cuts

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk; the page-byte and control budgets at `8b7e3d3b` (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

At `8b7e3d3b` the golden page is 149,745 of 150,000 B (255 B left); `xl_both` controls 886 of 900; `macro_micro` opened words 12,483 of 13,200; `xl_both` height 42,002 of 43,500. Round 155's seven tracks summed +990 B against ~849 B of headroom and the merge sat 34 B over before it recovered with no budget raised.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The owner decides whether the 150,000 B budget and the 900 controls cap stay. The row names the decision; it does not take it: keep both (each viewer row pays for its bytes with cuts), raise one with a measured reason, or move the weight (the exporter's minifier, the shared strings) so the ceiling is not the constraint.

## Out of Scope

Any change to the budgets before the owner decides; the viewer rows that spend it.

## Acceptance Test

The owner's answer is written into the budget guards' docstring line and this row's Outcome, and the next viewer row is briefed against it.

## Outcome

Open.
