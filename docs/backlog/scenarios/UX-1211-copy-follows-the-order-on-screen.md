# UX-1211: Copy follows the order on screen

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P2 (pre-existing): task table sorted Duration ascending shows toolchain, all.bst, mod017, mod014, mod013 (400 ms), mod050 (450 ms); Copy gives payload order with all.bst last. Elements sorted by depth shows all.bst first; Copy puts it last.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Copy writes the rows in the order the table shows them, sort included.

## Out of Scope

Which rows Copy takes (`UX-1189`, closed).

## Acceptance Test

After a sort on the task and elements tables, Copy's row keys equal the shown rows' keys in order; a guard in a new `test_copy_follows_the_order_on_screen.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
