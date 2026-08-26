# UX-316: exhibits drawn at annotation size

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-303 (the drawings), styleguide §2a | **Serves:** R1, R3 | **Topic:** viewer

## Motivation

The field pass, verbatim: the blast-radius distribution "is good as
sparkline — but very small and I don't see anything there"; the
store diagram "unreadable because everything is very small"; the
element-duration distribution "unreadable". Ground truth: every
drawing shares one geometry — `SPARK_HEIGHT = 20`, `STRIP_HEIGHT =
8` viewBox units (`bga/viewer/drawings.js:36-38`) — calibrated for
the sparkline beside a table cell and then applied to drawings that
are their section's entire answer. §2a names the split: annotation
grade and exhibit grade, one size cannot do two jobs — the token
lesson (§4.5) hitting geometry.

The graph-shape complaint rides here too: an exhibit is **always
paired with its table twin** (§2a), so the graph shape — and every
re-graded drawing — gets its "as table" toggle rendering the same
published values as rows.

## Required Fix

The size scale enters `style.css` as tokens; `drawings.js` takes
grade as an argument; the four named drawings (blast-radius
distribution, store diagram, element-duration distribution, graph
shape) become exhibits — container width, scale height, readable
tick labels, table twin — while the element-history sparkline and
in-table strips stay annotation grade. A guard holds every
drawing's geometry to the scale (no per-drawing constants outside
it).

## Out of Scope

- New drawings or new data — the same published values, at a size
  a reader can see.
- Axes/legends beyond §2's discipline (labels yes, apparatus no).

## Acceptance Test

On the golden and 1,202-element pages: the four exhibits measure
container width and scale height (asserted from the booted DOM's
geometry attributes); their table twins render the same published
values (equality walk); annotation-grade drawings are unchanged
byte-for-byte; mutation: an exhibit drawn at annotation height
reddens the scale guard; the §2 geometry-from-values guards stay
green.
