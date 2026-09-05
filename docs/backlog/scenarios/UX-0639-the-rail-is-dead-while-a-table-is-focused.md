# UX-639: the rail is dead while a table is focused

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-638 (same module) | **Found by:** round 87, measuring what table focus hides | **Serves:** anyone who reaches for the rail to leave a focused table | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Table focus hides every section with `display: none`. The left-hand
rail is not hidden with them, so every one of its links stays drawn,
styled and clickable while pointing at a section that has no box.

Measured on round 87's three-plane run, served, 1440x900:

```text
rail links whose target has a client rect
  before focus                 87
  while a table is focused      7
  after leaving focus          87
```

Eighty of eighty-seven links — 92% of the rail — are inert. They do
not error and they do not move the page; the fragment resolves to an
element with no layout, so the click does nothing at all. The reader's
only working way out is the `<- back` breadcrumb, which is one control
in a page whose navigation is a rail of eighty-seven.

`nav.js` has no idea focus exists: `grep behind-focus bga/viewer/nav.js`
returns nothing, and the module imports nothing from `tablefocus.js`.

## Required Fix

Focus is entered and left in one place, so the rail's state is set
there too — `tablefocus.js` marks the rail inert on entry and clears it
on leave, and `style.css` shows that state. No `nav.js` change: the
rail does not need to know what focus is, only that it is in one.

Inert means visibly inert and not clickable — the reader can see that
the rail is not the way out right now, and the breadcrumb is.

## Out of Scope

- Restoring scroll — UX-638.
- Making the rail *work* under focus (each link leaving focus and then
  navigating). That is a larger decision about whether focus is modal;
  filed here as the alternative this row rejected, and the deciding
  question is whether a reader in focus wants to leave it by accident.

## Acceptance Test

Served: with a table focused, no rail link resolves to a laid-out
section, and the rail carries the inert state. Leaving focus restores
all 87. A mutation that drops the marking reddens it.

## Outcome (round 87, 2026-09-04) — 🟢 Done

**Premise:** held. The counts differ from the filing because this probe
opens the chapters with the rail's own "Expand all" first — 65 rail
links on `macro_micro`, not 87, and the state the reader meets is the
same one.

### The gap, measured

Served `macro_micro`, headless Chromium 1440x900, against pristine
`tablefocus.js`. Two instruments, not one: what a rail link *resolves
to*, and what a click at the link's own centre *reaches*, which is
`document.elementFromPoint`.

```text
                              before   focused   after
rail links                        65        65      65
   ...whose target has a box       65         0      65
   ...on screen                    22        24      23
   ...a click at them reaches      22        24      23
```

Every link on screen is clickable while **none** of them resolves to a
laid-out section. The filing's 7 survivors are 0 here: on this fixture
no rail entry names a section that ends up inside the focus.

### The close, measured

`enterTableFocus` sets `data-focus-inert="true"` on `nav.toc` and
`leaveTableFocus` removes it; `style.css` turns that into
`pointer-events: none` plus a dimming and a grayscale. `nav.js` is
untouched and imports nothing new — the rail does not learn what focus
is, it is told it is in one.

The rail is found through `root.ownerDocument`, because it is a sibling
of `#report` rather than inside it, and the module still imports
nothing.

```text
$ python3 -m pytest tests/unit/test_the_rail_says_it_is_not_the_way_out.py -q
8 passed in 3.24s
   focused: 24 links on screen, 0 reachable, 0 with a laid-out target
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| H | the rail never marked on entry | 2 — the state clause and the clickable clause, at 24 of 24 reachable |
| I | `pointer-events: none` dropped from the sheet, mark kept | 1 — the clickable clause only |
| J | the mark never cleared on leave | 2 — the cleared clause and the clickable-again clause |
| K | `pointer-events: none` → `display: none` | 1 — the still-drawn clause, at 0 links on screen |
| L | `nav.toc[data-focus-inert="true"]` → `nav.toc` | 2 — the before-focus clause and the clickable-again clause |

I is the pair that matters: the mark and the sheet are two halves and a
guard that read the attribute would have been green with the rule
deleted. The clause hit-tests instead, which is why I discriminates.

### Deviations

- The Acceptance Test's "no rail link resolves to a laid-out section"
  is asserted as filed (`targets` 0 under focus) **and** as the
  operational claim behind it — no link is reachable by a click. The
  first is a property of what focus hides and would pass without this
  fix; the second is what this fix does.
- `onScreen` is not held equal across the three states: `.toc-sub`
  opens the section being read and shuts the others, so the rail's own
  visible set moves with the reading position — 22, 24, 23 above. The
  clauses assert the count of *links* is unchanged and that at least
  ten are on screen, rather than an equality that would flake.
