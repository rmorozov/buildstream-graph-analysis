# UX-1152: folds, table tools and element-card links repeat what is already on screen

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M9, M10, M11, M12 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M9, M10, M11, M12).

Long-text folds show a "... 254 chars" preview and repeat it once opened; Why #2's fold opens beside its row where #1 and #3 open below; table tools say "2 rows" three times and a one-row `#resource_blast` stays a 13-column table; the element card's "Also in:" links read section ids ("batch opportunities", "whatif"), and "Dominant binary" repeats "Ran one process at a time".

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

An open fold hides its preview and is labelled by what it holds; every Why fold opens below its row; at two rows or fewer the tools strip drops its counts and a single row renders as pairs; element-card links use section titles.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: the four shapes each measured absent, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome
