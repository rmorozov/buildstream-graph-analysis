# UX-1180: values and console: a zero-length ratio, an epoch as hours, a tooltip-only explanation, a spaced hyphen, seven warnings

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer, bga/cli.py, bga/structural | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

"Cores busy 983564.29×" (toolchain.bst, 0 ms duration, 938 ms CPU) and "172805.32×" (all.bst) in the element cards: a ratio over a zero-length span. macro_micro occupancy and run_instance print the epoch start as "496481.0 h", a point in time as a duration. A threshold box holding "abc" sets `aria-invalid=true` and explains itself only in the `title` tooltip ("\"abc\" is not a threshold this column can read, so no filter is applied"). `bga/cli.py:1416` prints a spaced hyphen and "1.5s" in the marginal gate message (the `UX-1172` survey read reader text and the CPU-floor line, not this one). The two-plane page logs 7 console warnings "has no bga:quantity; guessed" (direct_count, blast_count, building_count, assembling_count, measured_us, element_count x2) and the console-clean guard reads golden only.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A zero-length span has no cores-busy ratio; a timestamp is not printed as a duration; an unreadable threshold says so on the page; the gate message has no spaced hyphen and a spaced unit; the two-plane page logs no quantity warning and the console guard reads it.

## Out of Scope

The schema's quantity vocabulary beyond the seven named keys.

## Acceptance Test

On the two-plane page no element card reads a cores-busy ratio over a 0 ms span, no duration cell is an epoch, an unreadable threshold shows text on the page, `cli.py`'s gate message reads "1.5 s" without a spaced hyphen, and the console guard reads the two-plane page with 0 warnings. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
