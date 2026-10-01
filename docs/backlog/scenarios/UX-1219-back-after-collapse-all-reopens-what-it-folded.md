# UX-1219: Back after Collapse all reopens what it folded

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-160 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `a69d1d88`, Chromium 1440x900 and 390x844.

Walk P2 (pre-existing; the round-159 export behaves the same): Back after Collapse all keeps all 79 sections collapsed, at 1440 and 390, against `UX-1203`'s "one step Back". At 1440, reading at 3000, Collapse all, Back lands at 333.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

Back after Collapse all reopens the sections it folded and lands where the reader was.

## Out of Scope

Expand all's Back (`UX-1203`, closed).

## Acceptance Test

At 1440, from y 3000, Collapse all then Back: no section collapsed that was open before, and the reader's place kept; a guard in a new `test_back_after_collapse_all_reopens_what_it_folded.py`. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     The history entry saves section folds as well as chapter folds: `collapsible()` returns `shut()` (collapsed section keys) and `restore(keys)` (applies them, writes storage); `keepPlace` stores `sections: controls.shut()`; popstate calls `controls.restore(saved.sections)` before `scrollTo`.
Rejected:  Re-running `all(false)` on Back: it would open sections the reader had folded by hand.
Rejected:  Moving section folds into chapters.js `foldSnapshot`: chapters.js would have to know the section layer `collapsible` keeps to itself.
Files:     bga/viewer/nav.js, bga/viewer/app.js (keepPlace, popstate), tests/unit/test_back_after_collapse_all_reopens_what_it_folded.py
Guard:     In Chromium at 1440 and 390, from y 3000: Collapse all, then Back; the set of `data-collapsed=true` sections equals the set before, scrollY 3000±1.
Mutation:  Drop `sections` from keepPlace's state; all 79 stay collapsed, red.
Class:     product
Split:     Second in track H.
Question:  none. Default: storage follows the restored folds (reversible: remove `writeCollapsed` from `restore`).
```

## Outcome

Open.
