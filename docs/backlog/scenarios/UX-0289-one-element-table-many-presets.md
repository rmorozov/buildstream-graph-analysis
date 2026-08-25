# UX-289: one element table, many presets

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-288 | **Serves:** R1 and R7 | **Topic:** viewer

## Motivation

Filed from Direction 14, and the half of it the reader sees.

Measured on the 1,202-element synthetic run: **19 tables name elements
and they draw 13 distinct populations**, every one of them a subset of
the single 1,202-row element table `UX-268` built. Seven pairs overlap
100%:

```text
   100%      14  signals/critical_path   [2 cols]  <-> critical_path_detail [5 cols]
   100%     135  signals/leaf_analysis   [8 cols]  <-> structural/deferrability [6 cols]
   100%     135  signals/value           [2 cols]  <-> signals/value [4 cols]
```

Each is the same elements with a different column set — which is the
definition of a **view**, and the page has no way to say so. It has
bounds (`UX-262`'s `Top N`) and filters (`UX-205`), and **zero named
presets**: measured, no element on the page carries a preset role.

The cost is not only repetition. It is that the widest table carries
**13 columns** because one table has to serve every question, while a
reader asking one question wants four.

## Required Fix

1. One element table. A **preset** is a named `(filter, columns, sort,
   bound)` over it — "Critical path", "Leaves", "Latent heavies",
   "Choke points" — selectable, and named in the rail.
2. A preset is declared in the **schema's view-hints**, not in the page.
   `UX-201` established that sections, columns and units come from the
   published schema; a preset is the same kind of declaration and must
   not become the one thing the page decides for itself.
3. The current URL state (`UX-211`) carries the preset, so a link opens
   the view it names.
4. Every preset's population is a filter over published fields — which
   is what `UX-288` makes possible and why it comes first.

## Out of Scope

- Removing the element detail blocks. They answer a different question
  (one element, everything about it) and `UX-278` is about reaching
  them.
- Deriving a preset the payload cannot express. Direction 7's boundary
  holds: if a view needs a number the payload does not carry, the
  payload gains it (`UX-288`) rather than the page computing it.
- Doing this before `UX-288`. Deduplicating the page while the contract
  still publishes three copies makes the page and the payload disagree.

## Acceptance Test

On the 1,202-element run, no two tables carry identical element sets.
The critical path, the leaves and the choke points are presets over one
table, each reachable from the rail and from a link, and no table shows
more than eight columns by default.
