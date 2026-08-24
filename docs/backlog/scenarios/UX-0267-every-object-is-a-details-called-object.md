# UX-267: every object renders as a `<details>` labelled "object"

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R1 and R3 | **Topic:** viewer

## Motivation

Reported: *"tables where the left column contains a JSON object name
and the right column is a collapsed value object, and when expanded it
shows the internals as a string — it looks quite ugly … the great
example is 'what shape is this dependency graph?' where you need to
click on every object to open it — quite inconvenient and puzzling"*.

One line of `app.js` is responsible:

```js
} else if (value !== null && typeof value === "object") {
  cell = el("details", {}, el("summary", {}, "object"),
            el("pre", {}, JSON.stringify(value, null, 2)));
}
```

`typeof value === "object"` is also true for arrays, so this branch
produces **four** of the reported problems at once: a summary that says
`object` and nothing else, raw JSON behind it, arrays read as JSON, and
nothing searchable, sortable or bounded.

Measured on a served 44-element run:

```text
opaque "object" cells    34
characters of <pre>      32,393
largest single block     8,191
tables (the good case)   6
```

`signals.blast_radius` alone is 8,191 characters here and, extrapolated
by keys, **~224,000 at 1,202 elements** — behind a label that says
`object`.

The array-of-objects case is already right (`UX-208`'s `renderTable`),
which is exactly why the reader singled out `critical path detail` as
*"quite good"*. The fix is to make the other shapes as good, not to
invent a new idea.

## Required Fix

The rule is **width, not depth** — see Direction 12 for the
measurement that settles this.

1. A small object of scalars renders **inline**, as `name value ·
   name value`. Nothing to click, because there is nothing to hide.
2. A wide map renders as a **table**: one row per key, reusing
   `renderTable` so the filter, the thresholds, the sort, the
   `Top N` bound (`UX-262`) and the `n of m` badge (`UX-208`) all come
   for free.
3. An array of scalars: short, inline; long, the same bounded table.
4. Whatever still folds says **what it holds** — `Blast radius · 44
   entries`, never `object`.
5. A generated map table gets its own bounded height and scroll, so it
   cannot push the page down.

## Out of Scope

- The `<details>` element itself. The reported defect is the *label*
  and the raw JSON, not the fold — see the numbers below.
- Merging the element-keyed maps into one table. That is `UX-268`, and
  it subsumes several of these cells rather than rendering them better.

## Acceptance Test

Zero cells whose summary reads `object`, zero `<pre>` of raw JSON, and
the document no longer than it was — all three, since the first two are
trivially satisfiable by making the page enormous.

## Notes from a spike (not landed)

A spike implemented items 1–5 and measured each step, which is why the
Required Fix above is specific. The numbers are worth keeping:

```text
state                                opaque cells   <pre> chars   document
before                                         34        32,393   13.8 screens
tables, unbounded                               0             0   35.5 screens
+ Top N row bound                               0             0   32.3 screens
+ bounded height and scroll                     0             0   20.8 screens
+ folded, with a summary that names it          0             0   14.9 screens
```

**The trap is in row two.** Replacing folds with tables removes the raw
JSON and makes the page nearly three times longer, because a collapsed
`<details>` is one line and a table is not. Anyone implementing this
who stops at "render it as a table" will make the report worse while
fixing the complaint.

A second finding, and the reason the spike was **not** landed: with the
maps rendered as tables, one of them contained a `section[data-section]`
and the table of contents listed `summary` twice — `nav.js` finds
sections by `querySelectorAll` at any depth. The renderer must
guarantee it emits *cells*, never sections, and that needs more care
than the spike gave it. Better a filed item with the measurements than
a landed change that breaks navigation.

## Outcome

**Fixed**, and the second attempt landed because the first one's
failure was diagnosed rather than worked around.

**The whole fix was one function.** `renderTable` returns a
`<section data-section=…>`, which is right for a top-level view and
wrong for a cell. The spike called it for nested maps, so twenty-two
sections appeared inside table cells and `nav.js` — which finds
sections with `querySelectorAll` at any depth — listed `summary` twice,
because `summary` is both a map key and the run's own section.
`buildTable` is the same builder without the wrapper; `renderTable` is
now `buildTable` in a section. Every existing caller is unchanged.

Measured on the served 44-element run, in Chrome 141:

```text
                          before    after
opaque "object" cells         34        0
characters of <pre>       32,393        0
document                13.8 scr  13.6 scr
sections                      34       31
sections inside cells          0        0
```

The document is **shorter** than before, not longer — the trap the
spike found is avoided by keeping the fold and labelling it. Summaries
now read `Downstream count · 44 entries`, not `object`. 22 bounded
boxes and 45 filter inputs, so every map is searchable and none of them
can push the page down.

Small things need no click at all: an object of four or fewer scalars
renders inline as `Average depth 0 · Peak depth 0`, and a short array
as `import, stack, cmake`.

**A guard that did not discriminate, and was fixed rather than
counted.** Every test drove `renderStructured` directly, so restoring
the original `<details><summary>object</summary><pre>` at the *call
site* left all of them green — the mutation that reinstates the exact
reported defect passed. Three guards on the wiring were added; that
mutation now reddens three tests. Six mutations in total, all
discriminating.
