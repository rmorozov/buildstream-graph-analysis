# UX-1053: a two-plane page's growth with the run is bounded by the section that grows

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1050's architect (2026-09-27), styleguide §3e, §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

From UX-1050's table, on `bga gen-synthetic <d> --store --seed 1` with
`capture report --json` beside the run, 1440x900, the volume guard's
`_LOOK`: from 74 to 1,202 elements with both planes, landed height grew
7,521 → 8,504 px (+983) and controls 711 → 1,053 (+342). Words grew
only 12,424 → 12,974. A population that grows with the run is §3k's
case, and no section cap caught it; moving the size-class bound would
hide it.

## Decomposition

Input classes: both planes at 74, 1,202 and 4,002 elements, with a
store; the journey extended is UX-1050's volume walk over `scale_both`
and `xl_both`.

## Required Fix

A per-section census of landed height and controls on the 74-, 1,202-
and 4,002-element two-plane pages, splitting the store and history
from Plane 2's sections (`binary_cost`, `plane2_coverage`,
`element_join`, native findings). The section(s) that grow get a §3k
cap (a row cap or a fold), so the 1,202 and 4,002 pages land under
`LANDED_HEIGHT_PX` and the controls bound without moving either.

## Out of Scope

The pages and labels themselves (UX-1050); Plane 2's analysis.

## Acceptance Test

The census table pasted in the Outcome; the capped section's guard
green on the two-plane scale page; mutation: lift the cap and the
volume guard's landed or controls clause reds on `scale_both`.

## Outcome

Not started.
