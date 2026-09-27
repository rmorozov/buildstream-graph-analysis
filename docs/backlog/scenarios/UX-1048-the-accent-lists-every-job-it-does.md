# UX-1048: §4 lists every job the accent does, and the fills it takes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §4.2, §4.7, §6e.5, §2d | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

`grep -n 'var(--accent' bga/viewer/style.css` at `814a2db8`:

```text
--accent       links; hover borders (button, .investigate, .path-box, .chip); the focus
               ring (§6e.8, jump hits); a toggle that is on (UX-534); the decision
               panel's border; .reader-lead and section[data-promoted] borders
--accent-mark  button.primary fill (§6e.5); every drawing's marks - sparkline line and
               points, density ticks, interval marks, trend band, median and points,
               .band-strip, a decomposition's first part (§2d), the what-if .wf-fill
```

§4.2 (binding): "one hue does all of it: interaction, links, the
current focus, the promoted reader's border" — four jobs; the
stylesheet gives it about fifteen, most of them every drawing's marks.
§4.7 argues the promoted reader wears the accent "on a border, not a
fill — so rule 3's status tones keep every fill". §6e.5 (binding) gives
the primary control an accent **fill**, and every drawing fills its
marks with accent-mark. The round-141 audit rewrote §4.2's "the band"
as the reader's border (its A6); the drawings' band is what it named.
§4.6's one emphasis per block and §6e.5's one primary per chapter bound
two different things without saying how they meet.

## Decomposition

Input classes: the decision chapter (primary, verdict, bands), a
promoted section, a drawing with a band, print.

## Required Fix

§4.2 lists every accent job, §4.7's "status tones keep every fill"
becomes the true sentence (status tones, the primary control and the
drawing bands), and §4.6 says whether the primary control spends the
block's emphasis. A guard reads every computed accent use against the
list.

## Decision

Architect, 2026-09-27, at `71d3dcda`.

- **Route**: §4.2 rule 2 becomes a table, one job per row with its grade, channel and selectors. Eight jobs: accent (1) links `a`/color; (2) hover `button`, `button.primary`, `.investigate button`, `.path-box`, `.chip`/border; (3) toggle on `button[aria-pressed="true"]`/border, box-shadow; (4) current focus: the `:focus-visible` set, `[data-jumped]`, `.jump-hits li[data-active] > button`/outline, `.focus-bar`, `.mark-summary`/border-left; (5) decision and promotion `.decision`, `.reader-lead`, `section[data-promoted]`/border; (6) info/low severity `.finding`, `.advice`/border-left. accent-mark: (7) primary control `button.primary`/background, border; (8) drawing marks `.band-strip`, `.trend-band`, `.trend-point`, `.spark-point`, `.decomposition-part:first-of-type`, `.interval-mark`/fill; `.spark-line`, `.density-tick`, `.trend-median`/stroke; `.wf-fill`, `.horizon-bar`/background.
- §4.7 rule 7: "A promoted section wears rule 2's accent on a border, not a fill; fills belong to rule 3's status tones, the one primary control (§6e.5) and the drawings' marks (accent-mark)"; its "already spent on interaction, the current focus and the band" is fixed too. §4.6 gains: "A `primary` control spends none of the block's emphasis: §4.6 budgets type per block, §6e.5 affordance per chapter."
- **Rejected**: a hand-typed selector list in the test (UX-996); deriving the allowed set from `style.css` alone (a new rule would declare itself); extending `test_emphasis_is_a_budget.py` (another claim); counting primary as emphasis (no measured defect).
- **Files**: `docs/design/styleguide.md` (§4.2, §4.6, §4.7); `tests/unit/test_the_accent_does_only_its_listed_jobs.py` (new); `bga/viewer/style.css` 795-797 (stale comment only).
- **Guard**: static - the (selector, channel) pairs parsed from `style.css`'s `var(--accent(-mark)?)` declarations equal those parsed from §4.2's table, both ways. Booted - golden and `macro_micro`, 1440x900, dark, light and print: every element whose computed color, border colour, background-color, outline-color, box-shadow, fill or stroke is the accent or accent-mark `matches()` a §4.2 selector for that channel; at least one hit per at-rest job (1, 5, 7, 8).
- **Mutations**: (a) `.investigate button { background: var(--accent-mark) }` reds both halves; (b) `.density-end { stroke: var(--accent-mark) }` reds both (confirm `.density-end` renders on golden first); (c) delete `.wf-fill` from §4.2's table, the static half reds.
- **Class**: product. One track, implementer with `model: opus`.

## Out of Scope

The accent's value and the palette bands (§5).

## Acceptance Test

A booted guard: every element whose computed `color`, border colour,
`background-color`, `outline-color`, SVG `fill` or SVG `stroke` is the
accent or accent-mark is of a class §4.2 lists - stroke included, since
`.spark-line`, `.density-tick` and `.trend-median` wear it there.
Mutations: give a quiet button an accent fill, and the guard reds; give
an undeclared SVG line an accent-mark stroke, and it reds.

## Outcome

Not started.
