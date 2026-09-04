# UX-639: the rail is dead while a table is focused

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-638 (same module) | **Found by:** round 87, measuring what table focus hides | **Serves:** anyone who reaches for the rail to leave a focused table | **Topic:** viewer

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
