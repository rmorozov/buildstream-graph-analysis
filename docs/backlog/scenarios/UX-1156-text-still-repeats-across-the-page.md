# UX-1156: text still repeats across the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, items 4 and 11, and the verifier's `#capacity_verdict` read (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

The Shared-source sentence is drawn in 11 places; the element card's "Dominant binary" and "Ran one process at a time" list the same values; `#utilisation` says "6 rows" five times; `#confidence`'s gates table has a "Name" header over sentences and "Ordering violations 0" repeats its first gate; "Highest-criticality elements" and "Elements most worth optimizing first" are titles over list bodies; `plane2_coverage`'s "Process count", "Wall span" and "Peak processes" restate its lead (`test_no_key_is_terminal_only_in_silence` requires them drawn); `#capacity_verdict` reads "Skipped inputs none" under a sentence saying both checks ran.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each sentence is drawn once; a pair that restates a lead leaves the page and the guard that required it is re-read.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page no sentence of 8 or more words appears twice and no pair restates its section's lead. Mutation: restore the defect, and the new guard reds.

## Outcome

Open.
