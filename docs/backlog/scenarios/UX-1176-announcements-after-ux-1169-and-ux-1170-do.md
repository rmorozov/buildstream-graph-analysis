# UX-1176: announcements after UX-1169 and UX-1170 do not reach a screen reader

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

The Jump no-match line (`<ul class="jump-hits"><li class="muted">Nothing matches "zzzq".</li>`) and the Ask no-match note (`Nothing in this run's 114 elements matches "zzzq"; ...`) carry no role or `aria-live`, and the input has no `aria-describedby`; the table badge beside them is `role=status`. 26 of 29 `role=status` badges are `display:none` at rest and are revealed in the same task their text changes (MutationObserver on `#resource_blast .badge`: childList, then `hidden=false`), so a region enters the tree already populated; the three always-visible badges (`wall_clock_share_us`, `binary_cost`, `elements`) are not affected (the structure is measured; no real screen reader was run). 33 of 33 tables have an empty accessible name (65 of 65 groups too). The drawing-values clip rule of `UX-1169` is unguarded: 129 tests stay green with it removed (about 110 B dead).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The Jump and Ask no-match lines are announced like the filter badge; a badge hidden at rest keeps its live region mounted and only its text changes; each table takes its section question as a name; the drawing-values clip rule has a guard.

## Out of Scope

The visible labels; the names `UX-1162` and `UX-1169` fixed.

## Acceptance Test

On the two-plane page the two no-match lines sit in a live region or are named by the input's `aria-describedby`; a badge that hides at rest is mounted when its text changes; no table has an empty name; removing the drawing-values clip rule reddens a test. Mutation: restore one defect, and the guard reds.

## Outcome

Open.
