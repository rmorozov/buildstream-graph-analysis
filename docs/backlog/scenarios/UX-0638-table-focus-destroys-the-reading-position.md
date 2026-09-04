# UX-638: table focus destroys the reading position

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-284 (tools above the table), UX-318 (the rabbit hole announces its depth) | **Found by:** round 87, by the repository's owner pressing Expand twice | **Serves:** anyone who expands a table below the first screen | **Topic:** viewer

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
- Making the chapter boxes hide with the sections; that is a question
  about what focus *is*, and this row is about not losing the reader.

## Acceptance Test

Served, 1440x900: expand a table whose button sits more than one screen
down, collapse it, and the scroll offset is within one viewport of
where it started. A mutation that drops the restore call reddens it.
