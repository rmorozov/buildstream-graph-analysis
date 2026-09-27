# UX-1046: the rail shows the current chapter's sections, or every open chapter's — one rule

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3h, §6e.5 | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900; the rail before and after "Expand all":

```text
                         rail box  scrollHeight  section links  last chapter row bottom
macro_micro   landed       530 px       530 px              6            539 px
macro_micro   Expand all   848 px     2,239 px             76          2,152 px
74 elements   Expand all   848 px     2,601 px             87          2,458 px
1,202         Expand all   848 px     2,885 px             98          2,743 px
```

The rules-at-a-glance line says the rail shows "only the current
chapter's sections"; §3h's own mechanism says a rail row's disclosure
*is* the document's chapter fold, and §6e.5 says several chapters can
be open at once. The page follows the mechanism, so after "Expand all"
the rail is 2.6-3.4 of its own screens, growing with the run, and the
last chapter row sits up to 2.2 rail screens below the rail's bottom — §3h's round-90 measurement (1,902 px,
2.4 rail-screens) back, through the one path its guard does not press.

## Decomposition

Input classes: landed, one chapter opened, "Expand all", a fragment
into a folded chapter; both size classes.

## Required Fix

Decide: (a) the rail discloses only the chapter holding the scrollspy
mark, other open chapters showing their row alone, and the rail's
disclosure stops being the document fold; or (b) the rule reads "every
open chapter's sections" and the rail is bounded some other way.
Default, if no decision: (a), since it is the reading §3h was filed to
buy. Amend §3h and the glance line to one sentence.

## Out of Scope

The rail's entries and labels (`UX-1044`).

## Acceptance Test

`test_the_rail_is_a_source_list.py` presses "Expand all" and holds the
rail's scrollHeight to its box (a) or to the bound (b) chosen.
Mutation: restore the coupling, and the clause reds.

## Outcome

Not started.
