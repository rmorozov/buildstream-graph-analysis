# UX-1191: a key column matches exactly, and a one-op task table says its op once

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 9 of the review.

1,202 of 1,202 tasks are BUILD, yet the op badge is drawn on every row, where §3d asks for one sentence; there is no op facet. The filter is substring-only: `cc` matches 1,201 rows in `binary_cost`, including `gcc` and `cc1plus`, and `ld` cannot be isolated. Controls: 902 on this page against a 900 bound (909 on the heavy page), so any new input has to replace one.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a key column filters exactly": a declared key column (element, binary, op) offers an exact or prefix match beside the substring box, for example `binary:ld`; a one-value op is stated once. Priced by folding the per-column thresholds into the one filter grammar (`> 5s`), -2 to -3 controls per table, so the page's control count falls.

## Decision

Class: product.

## Out of Scope

The key declaration (`UX-1186`); the threshold semantics themselves.

## Acceptance Test

`tests/unit/test_a_key_column_matches_exactly.py`: `binary:ld` on `UX-1182`'s page returns the `ld` rows only, the one-op task table states its op once, and the page's controls do not rise. Mutation: make `binary:` a substring match; the guard reds.

## Outcome

Open.
