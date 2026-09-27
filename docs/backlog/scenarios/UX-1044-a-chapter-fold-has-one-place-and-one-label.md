# UX-1044: a chapter's fold sits at one place and says the same thing in the rail and the document

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3l, §6e.2, §6e.13 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900 and 390x844. The chapter's fold is one state with two controls (§3h):

```text
                      x-centre (1440)   label, folded            label, open
rail row              176, every row    "Where did the time go? · 14"   same
document control      624-932           "Show 14 sections"       "Hide"
```

The document control trails the chapter title, so it moves 300 px from
chapter to chapter; its open label "Hide" names neither content nor
count (§6e.13), and neither control wears §6e.13's ▸/▾ pair. Opening
every chapter from the document costs 684-829 px of travel and
8,067-9,521 px of wheel at 1440x900, 49,946-61,039 px at 390x844 (11 to
1,202 elements), because each opened chapter pushes the next control
below it. The synthetic pages have seven chapters; the control's x runs
556-859 on all three.

## Decomposition

Input classes: chapters with 4-24 sections, a title that wraps, both
size classes, the decision chapter (no control).

## Required Fix

Both controls share the glyph, the count and the state ("▸ 14
sections" folded, "▾ 14 sections" open) and each keeps the chapter's
title in its accessible name - the rail row keeps it visible, as
`chapters.js`'s `labelFold` writes it today, since two chapters can hold
the same count - and the document control sits at one place in every
chapter head, in `bga/viewer/chapters.js`, `bga/viewer/nav.js`
and `bga/viewer/style.css`.

## Out of Scope

The wheel cost of opening chapters in sequence; "Expand all" and the
rail already avoid it.

## Acceptance Test

`UX-1042`'s placement clause for `button.chapter-open`, and a booted
clause that the rail row and the document control carry the same glyph,
count and `aria-expanded` in both states, and that each control's
accessible name contains its chapter's title. Mutations: set the open
label back to "Hide", and the glyph clause reds; drop the title from the
rail row, and the name clause reds.

## Outcome

Not started.
