# UX-1044: a chapter's fold sits at one place and says the same thing in the rail and the document

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3l, §6e.2, §6e.13 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

**Guard:** test_a_chapter_fold_has_one_place_and_one_label.py, test_a_new_control_class_lands_declared.py, test_one_click_from_investigation.py, test_labels_are_sentence_case.py · inferred r149

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

## Decision

Shaped with UX-1046 (its Decision): runs on top of it in the same track. The "same `aria-expanded` on both controls" clause is struck: it reads the coupling UX-1046 removes. Each control's ▸/▾ glyph follows its own disclosure (rail row: `data-current`; document control: `data-open`); both carry the count and the chapter title; `labelFold` stays the one label painter for both and reads the row's `data-current` for the rail glyph.

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

**Gap measured.** The Motivation's table (`814a2db8`): the document
control's x-centre ran 624-932 px at 1440, open label "Hide", no glyph.
Reproduced by mutation D below: offset in `h2.chapter-title` spread
303 px (from the left edge) / 312 px (right) at 1440x900.

**Close measured.** `place.py` (scratchpad): every `button.chapter-open`
clicked open, offset read against its `h2.chapter-title`, px spread
(max-min); pages as in `UX-1046`'s Outcome:

```text
                      dx left  dx right  dy   x-centre     h2 height
macro_micro 1440x900     10       0       0   1304-1309        43
macro_micro  390x844     10       0       0    295-299     43-108
74 elements 1440x900     17       0       0   1304-1313        43
74 elements  390x844     17       0       0    295-303     43-108
1,202       1440x900     17       0       0   1304-1313        43
1,202        390x844     17       0       0    295-303     43-108
```

Labels, macro_micro, folded -> opened (document) and landed (rail):

```text
document  "▸ 14 sections" -> "▾ 14 sections"   aria-label "14 sections: Where did the time go?"
rail      "▸ Where did the time go? · 14"     ("▾ ..." on the row holding data-current)
```

`test_a_chapter_fold_has_one_place_and_one_label.py`: 8 passed.
Adapted readers of the old label: `test_a_new_control_class_lands_declared.py`
(`^[▸▾] \d+ sections?$`), `test_one_click_from_investigation.py` (strips
the glyph before comparing titles).
`pytest -n 2` on every file matching `grep -lE "nav\.js|chapters\.js|
toc-chapter|data-chapter-open|scrollspy|data-toc|chapter-open"` plus the
styleguide, conformance and register guards: 1648 passed, 2 skipped.

**Mutation table** (the new file, both viewports):

| mutation | reddened | run |
|---|---|---|
| A: open label back to `"Hide"` | glyph clause (and count clause: "Hide" has no count) | 4 failed, 4 passed |
| B: document label drops the count (`▸ sections`) | count clause only | 2 failed, 6 passed |
| C: rail row drops the title (`▸ · 14`) | name clause only | 2 failed, 6 passed |
| D: `margin-left: var(--space-2)` for `auto` (control trails the title) | spread and right-edge clauses, 1440x900 | 2 failed, 8 passed |
| D2: `h2.chapter-title` loses `display: flex` | spread and right-edge clauses, 1440x900 and 390x844 | 4 failed, 6 passed |
| E: rail glyph from `isOpen(box)` instead of `data-current` | glyph clause only | 2 failed, 6 passed |

Reverted from the scratchpad copy: 8 passed, then 10 with the right-edge
clause (control's right edge within `EDGE = 2` px of its head's). D cannot
red at 390x844: it leaves that layout unchanged (`place.py` with D
applied, 390x844: dx right spread 0, dy spread 0, the edge clause green - each title
wraps and fills the flex line), so D2 is the mutation that reaches 390.
§7's `§3l` and `§6e` rows name the new file.

**Deviation.** The Acceptance Test's "same `aria-expanded` on both
controls" is struck, per the Decision: the rail row has no
`aria-expanded` after `UX-1046`, and each glyph follows its own control.
The document control's accessible name is its `aria-label`
(`"<n> sections: <title>"`, holding the visible count); the guard reads
`aria-label` or `textContent`, not the browser's computed name.

**Integration (round 143):** the fold's rendered label is "▸ Sections · 14", not
"▸ 14 sections": `test_labels_are_sentence_case.py` rejected the lowercase first letter on
golden, macro_micro and scale (3 failed); it now mirrors the rail row's "▸ <title> · 14".
The `aria-label` keeps "14 sections: <title>". Mutation: the old template back, 3 failed.
The wider label (115-124 px against 96-113) wraps two h2s at 390 px and lengthens
`UX-1042`'s J3 on both_scale 390 from 20.34 to 21.01 bits (wheel 57,400 to 57,550); per
§3l the lengthened journey is reported and `MEASURED` re-based, the headroom unchanged.
