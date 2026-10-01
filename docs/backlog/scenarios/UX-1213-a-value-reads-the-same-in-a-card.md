# UX-1213: a value reads the same in a card, a table, a badge and a sentence

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk, pre-existing: P5 the on-demand card reads "Is a leaf false", "Observed critical false" where the table reads "no". P6 badge "10 of 1,202" for a filter matching 10 is the same text as an unfiltered Top 10 window; "matched" appears only when the matches exceed the window (binary_cost focus "8 of 11,683"). P7 density sentence "across 1202 rows" beside the badge's "1,202".

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Cards print booleans as the tables do; a filtered badge says matched whatever the window; counts carry a thousands separator.

## Out of Scope

The filter grammar (`UX-1206`).

## Acceptance Test

No card text matches /\b(true|false)\b/; a filter matching 10 under Top 10 reads "matched"; no visible text matches /\b\d{4,}\b rows/; a guard in `test_a_value_is_what_it_names.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
