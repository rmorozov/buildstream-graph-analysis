# UX-316: exhibits drawn at annotation size

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-303 (the drawings), styleguide §2a | **Serves:** R1, R3 | **Topic:** viewer

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

## Log

**Ground truth first.** Every drawing in the viewer, and the geometry
they shared, read off the source and off two booted exports:

```text
drawing                                        viewBox     CSS box
blast-radius distribution      (strip)        0 0 100 8    9rem x .9rem
element-duration distribution  (strip)        0 0 100 8    9rem x .9rem
graph shape, width_at_level    (sparkline)    0 0 100 20   7rem x 1.4rem
store diagram, the trend       (bespoke)      0 0 100 40   100% x 5rem
the compare band               (bespoke)      0 0 100 74   100% x 5rem
element history                (bespoke)      0 0 100 20   7rem x 1.4rem
```

Two of those six are `views.js` writing the box out by hand, and one of
them - the element history - had copied the sparkline's `0 0 100 20`
into a file that could not import the constant. That is the
per-drawing constant §2a abolishes, and it was invisible to every
guard.

**The split, as landed.** `drawings.js` owns `SCALE`, and the grade is
a **required argument**: a call with no grade throws, because the
defect was a call site that never chose and a default is how the next
one does not choose either. Two grades, three drawing kinds:

```text
                 width   spark   strip   figure
annotation        100      20       8        -
exhibit           100      60      26       74
```

`figure` is the third *kind*, not a third grade - a composed drawing
with lanes is as different from a line over an order as a strip is.
The band keeps the 74 it always drew at; what it gains is the grade,
the twin, and a height that is read rather than written.

**Which drawings are exhibits, and the rule that decides.** Not depth
and not placement: a value the schema declares a `bga:series` or a
`bga:distribution` renders as that drawing *because the drawing is the
value*, so it is the answer wherever the nesting puts it. The two
annotation-grade drawings left are exactly the two that annotate
something else - `columnStrip` beside a table, and the per-element
history beside an element's row.

**What the reader gets.** Container width, the scale's box, tick
labels under the ends, and the table twin §2a requires - `as table`,
closed by default, printing open because paper has no toggle. Measured
on the two committed exports: 4 exhibits, all four with an axis row and
a twin whose rows are the same published numbers the drawing carries in
its own `data-*`.

```text
                        before          after
CSS height, exhibits    1.4rem/.9rem    9rem / 3.5rem
store diagram           5rem            9rem
viewBox, sparkline      0 0 100 20      0 0 100 60
viewBox, strip          0 0 100 8       0 0 100 26
```

**Annotation grade did not move** - asserted coordinate for coordinate
rather than claimed: the annotation polyline, the strip's bar and its
end ticks all draw the numbers they drew before, and `UX-303`'s 27
clauses pass unchanged apart from the grade they now pass in.

**Deviation from the Required Fix, recorded.** It asks for
annotation-grade drawings "unchanged byte-for-byte"; they carry one new
attribute, `data-grade="annotation"`. The geometry is identical - every
coordinate, both CSS boxes - and the attribute is what lets the grade
walk read a drawing's grade off the page instead of off the source,
which is what `UX-320` needs.

**Three guards this reddened, each a real hole:**

1. `test_one_accent_hue` counted every custom property as a hue, so
   seven *lengths* read as seven new accents. It now splits colour
   tokens from the rest by their declared value, and a second clause
   holds the split in both directions.
2. `test_no_library_and_no_arithmetic_beyond_layout` forbade every
   `import` in `views.js`. The rule's subject is a *library*: it now
   forbids a bare specifier and anything outside the viewer directory,
   which is what "no dependency" was protecting.
3. `test_the_element_tables_the_report_is_about_are_among_them` read
   `data-table` off every `<table>` and crashed on the twin, which
   deliberately has none - a twin is not a §3 table (no columns, no
   sort, no state key), and the probe now says so.
