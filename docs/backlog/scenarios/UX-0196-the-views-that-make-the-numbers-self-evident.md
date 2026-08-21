# UX-196: the views that make the numbers self-evident

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-193 (the shell these views live in), UX-170 (the band), UX-171 (the blast table), UX-103 (cache-trend)

## Motivation

Direction 7's scenario list, filed as the second wave once UX-193's
shell exists. Three views where a drawing says what sentences have
been straining to:

1. **The band, drawn.** Compare's noise band as a horizontal strip,
   baseline runs as dots, the candidate as a marker — inside,
   outside, or in UX-170's disputed region (outside the band, inside
   the observed range: the marker lands *between* the strip's edge
   and the dots' extent, and the paradox that took a paragraph
   becomes one glance). The refusal verdicts render as the banner
   they are.
2. **The store trend.** The run store as a small timeline: per
   snapshot, total duration (dot), verdict against its baseline
   (color), cache-trend hit rate (line) — `--list` made visual, the
   "is this project drifting" question answered by shape. Failed /
   interrupted / suspended snapshots marked, not hidden.
3. **The blast explorer.** The Shared Sources table with each row
   opening its blast (direct elements, closure, kinds, work — the
   `bga blast` answer rendered); a search box accepting url / path /
   element, backed by the same resolution the CLI uses (served
   through a tiny query endpoint that calls the same function —
   still no viewer-side semantics).

All three render from published JSON plus at most one addition:
scenario 2 needs a `store/v1` listing payload (`--list`'s data as
JSON — which the CLI should gain anyway, one flag, same source of
truth).

## Required Fix

The three views, in the generic-rendering discipline (custom drawing
only where the generic table cannot say it — the band strip and the
trend line are the two custom SVGs, each under ~100 lines, no
library); `bga snapshot --list --format json` producing `store/v1`;
the blast query endpoint calling `bga/blast.py`'s existing function.

## Out of Scope

- The dependency-DAG view (Direction 7 defers it deliberately —
  waits for a concrete question and its own vendoring decision).
- Any recomputation in the browser beyond layout.

## Acceptance Test

The band view on the round-17 fixture store renders the disputed
region case with the marker between band edge and observed extent
(geometry asserted from the data attributes); the trend view marks
the failed and interrupted snapshots distinctly; the blast search
returns byte-identical JSON to `bga blast --format json` for the
same target (served endpoint vs CLI, digest-compared);
`--list --format json` validates against `store/v1` and the text
`--list` derives from the same rows.
