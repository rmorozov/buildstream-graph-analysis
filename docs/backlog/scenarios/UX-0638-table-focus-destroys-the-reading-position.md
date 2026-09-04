# UX-638: table focus destroys the reading position

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-284 (tools above the table), UX-318 (the rabbit hole announces its depth) | **Found by:** round 87, by the repository's owner pressing Expand twice | **Serves:** anyone who expands a table below the first screen | **Topic:** viewer

## Motivation

`Expand` is not an expand. It is **table focus**: a single global slot
that hides every other section with `display: none`, and nothing in
either direction restores the reader's scroll position.

Measured on round 87's three-plane run, 1440x900 headless Chromium,
the export served over HTTP:

```text
Expand buttons on the page                          17
document height, before -> focused    42,936 -> 1,681 px   (25x collapse)
button text after entering focus               "Expand"    (unchanged)
aria-pressed                                       null    (no state)
```

The collapse is `style.css:879` — `[data-behind-focus="true"] {
display: none; }` — applied to every section by `tablefocus.js:131-134`.
Neither `enterTableFocus` nor `leaveTableFocus` contains a scroll call:
`grep scrollIntoView bga/viewer/*.js` returns four hits, all in
`app.js`. So the document collapses to a twenty-fifth of its height,
the browser clamps the scroll offset, and re-expanding restores the
height but not the position.

On the `macro_micro` export the displacement measured **4,199 px — 4.7
screens**, with the table the reader had been reading 3,360 px below
the fold. The identical displacement occurs by the supported `<- back`
breadcrumb, so it is `tablefocus.js` and not the button.

Two things compound it. The button never says it is pressed — still
`Expand`, still "Open this nested table full width, with a way back",
no `aria-pressed` — so nothing signals that a second click means
collapse. And the seven `section.chapter` boxes are *not* hidden
(`chapters.js:384-386` gives them `data-chapter`, never `data-section`),
so what fills the screen on return is seven chapter headings.

**Why no guard caught it.** `test_the_fold_says_how_deep_it_goes.py`
drives table focus, but its served probe clicks Expand **once** and
then uses the breadcrumb — never the same button twice — and its
strongest clause compares a DOM dump. Scroll position is not in the
DOM.

## Required Fix

`enterTableFocus` records the scroll offset before it hides anything;
`leaveTableFocus` restores it after the sections come back. The
focused table is scrolled to the top of the viewport on entry, so
focus starts where the reader is looking rather than wherever the
clamp left them.

The control says what it is: `aria-pressed` on the button, and a label
that changes when focus is entered.

## Out of Scope

- The rail going dead while focused — UX-639, same module, its own row.
- Making the chapter boxes hide with the sections — that is a question
  about what focus *is*, and this row is about not losing the reader.

## Acceptance Test

Served, 1440x900: expand a table whose button sits more than one screen
down, collapse it, and the scroll offset is within one viewport of
where it started. A mutation that drops the restore call reddens it.

## Outcome (round 87, 2026-09-04) — 🟢 Done

**Premise:** held, and one figure in it is *not reproducible the way
the Motivation implies*. See "the gap" below — the number is real, the
route to it is one step longer than filed.

### The gap, measured

Served `macro_micro`, headless Chromium 1440x900, chapters opened with
the rail's own "Expand all", the first `data-expand` more than one
screen down, pressed twice — against pristine `tablefocus.js`:

```text
                       enter, leave        enter, read, leave
document height    40,578 -> 1,681 px      40,578 -> 1,681 px
scroll offset       5,954 -> 5,954         5,954 -> 14,497
the table's top       300 ->   300 px        300 -> -8,242 px
```

The left column is the trap: **Chrome restores the offset a shrinking
document clamped, by itself**, when the document grows back and nothing
scrolled in between. A probe that enters focus and leaves measures that
restoration and passes on the unfixed page. One scroll inside focus —
which is what focus is *for* — spends it, and the displacement is
8,543 px, 9.5 screens. Round 87's 4,199 px is the same defect at a
different reading position.

### The close, measured

`enterTableFocus` records `window.scrollY` after its own leave and
before anything is hidden; `leaveTableFocus` restores it last, after
the sections are back and the document is its full height again. Entry
scrolls the focus section to the top — `.table-focus` gets the same
`scroll-margin-top` every anchor on this page has, so "the top" is
under the sticky header and not behind it. The control gets
`aria-pressed` and `Expand` → `Collapse`, both restored on leave:
removed rather than set to `false`, because `UX-318` promises the
document comes back byte for byte and
`test_the_fold_says_how_deep_it_goes.py` reads exactly that.

```text
$ python3 -m pytest tests/unit/test_focus_keeps_the_reading_position.py -q
9 passed in 2.78s
   scroll offset   6,024 -> 6,024 px   the table's top  300 -> 300 px
   focus section entered at 104 px, which is --head (96) + .5rem
```

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A | the restore call dropped | 2 — the offset and the reading position, at 8,542 px |
| B | `section.scrollIntoView()` dropped | 1 — entry, at 404 px from the top against a 112 px tolerance |
| C | `Collapse` → `Expand` in the label swap | 1 — the label clause |
| D | `aria-pressed` set to `false` on entry | 1 — the pressed clause |
| F | the focus section not removed on leave | 1 — the second-press clause |
| G | `data-behind-focus` set to `"no"` | 3 — the collapse clause here, entry, and `UX-639`'s out-of-focus clause |

A reddens two clauses because they are two readings of one claim: the
offset is the Acceptance Test's number, and the table's viewport-top is
the reading position that number stands for. A page whose height is
re-estimated on the way back can satisfy the first and lose the second,
which is why both are there.

### Deviations

- `title` moves with the label (`Open this table full width…` →
  `Close this table and go back`). Not asked for; a button reading
  `Collapse` with a tooltip reading `Open` is a contradiction this
  change would otherwise have introduced.
- `test_the_page_has_a_button_below_the_fold` and
  `test_focus_collapses_the_document` are non-vacuity controls, not
  claims. The first was seen red for free — this guard's first run
  returned `{'found': False, 'buttons': 13}`, because every
  `data-expand` on a fresh load is inside a shut chapter and has no box
  at all. The probe presses "Expand all" first for that reason.
- This file's own Out of Scope entry failed
  `test_docs_links_and_commands.py` at `15a038a`: it states its reason
  after a semicolon, and the guard reads `(…)`, `—…`, `: …` or a second
  sentence. Repunctuated to an em-dash; the wording is unchanged.
