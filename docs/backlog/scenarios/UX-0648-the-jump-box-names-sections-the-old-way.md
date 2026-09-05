# UX-648: the jump box names sections the old way

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-223 (the jump box becomes a command palette), UX-640 (which fixed the rail's half) | **Found by:** round 87, track B, from the seam it did not cross | **Serves:** anyone who reaches a section through the palette | **Topic:** viewer | **Area:** bga/viewer

## Motivation

`UX-640` gave the rail one label authority: an entry now reads what
its destination's heading reads. `jumpTargets` (`nav.js:719`) was not
part of that change and still names sections `label(key)` — the
mangled payload key.

So the same two-authority defect `UX-640` measured at 39 of 46 and 52
of 66 rail entries now lives on in the palette, where a reader typing
"why is my build slow" against a list of keys has the same trouble the
rail had. The rail and the palette disagree with each other as well as
with the page.

## Required Fix

`jumpTargets` asks the same authority the rail now asks, so the three
lists — rail, palette, headings — carry one string per section. The
guard extends `UX-640`'s to the palette's population rather than
duplicating it.

## Out of Scope

- The palette's matching and ranking. This row is the label it shows,
  not how it searches; `UX-223` owns the behaviour.

## Acceptance Test

On both fixtures, every palette entry's label equals its destination
heading's label, and equals the rail's label for the same section.

## Outcome (round 88, 2026-09-04) — 🟢 Done

**One label authority for three lists.** `nav.js` grew
`sectionLabel(section, key)` — the rail's `UX-640` expression, named —
and both the rail and `jumpTargets` call it. `label(key)` survives as
that function's last fallback and nowhere else.

Counted with a browser over the exported page, sections a reader
reaches by typing what the page calls the section:

```text
                sections   reached before   reached after
golden              46            0              46
macro_micro         66            0              65
```

`label(key)` differed from the heading for **46 of 46** and **66 of
66** — every section, worse than the rail's 39 and 52, because the
palette had no `data-toc-label` fallback either. Of the entries that
are reached, 0 of 46 and 0 of 65 name their section anything the
heading or the rail does not.

`macro_micro`'s `summary` is the one section not reached: its heading
is `Run`, three characters, and `matches`' eight-row limit fills with
element uids before the section group. That is `UX-223`'s ranking,
which this row's Out of Scope names, so the guard asserts a floor of 40
rather than equality.

**Guard:** `tests/unit/test_the_rail_says_what_the_heading_says.py`,
extended rather than duplicated —
`TestThePaletteAsksWhatTheHeadingAsks`, two tests over the same two
fixtures. It drives the palette by typing, because the export ships the
modules inside a `<script type="module">` and `jumpTargets` is not
callable from an evaluated expression.

**Mutations verified red and reverted (3):** `anchor(root).slice(0, 3)`
in `jumpTargets` — reached 3 of 46 and 3 of 66, population red,
agreement green; a `" (x)"` suffix on the palette's text — 46 of 46 and
65 of 65 differ, agreement red, population green; and the defect
itself, `label(key)` — reached 0 of 46 and 0 of 66.

**Deviation:** none. The palette's matching and ranking are untouched.
