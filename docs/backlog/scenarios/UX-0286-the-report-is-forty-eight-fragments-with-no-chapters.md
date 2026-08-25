# UX-286: the report is forty-eight fragments with no chapters

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-285 | **Serves:** R1 and R7 — reading top to bottom before they know what they want | **Topic:** viewer

## Motivation

Filed from Direction 13, which was argued from a proposal to make every
block one screen. The measurement refuted that half and sharpened this
one. At 1440×900 in Chrome 141:

```text
                              1,202-element     macro_micro
sections                                48              39
document                          18.8 scr        20.1 scr
median section                    0.24 scr        0.35 scr
sections under 0.8 screens              46 (95%)        37 (94%)
sections over one screen                 2 (4%)          2 (5%)
```

The median section is **216 pixels**. The report is not a document with
chapters; it is forty-eight fragments averaging a fifth of a screen,
read by scrolling past them. Nothing groups them, so the rail lists
thirty-one top-level entries (`UX-271`) and the reader's only unit of
navigation is the fragment.

The nine items round 38 filed are symptoms of this at the leaf: the
identity blocks split across 12.5 screens (`UX-285`), the blast control
stranded at 19.9 of 20.1 screens, table tools scattered relative to
their tables (`UX-284`). Each is a placement bug on its own; together
they are the absence of a level in the document's structure.

`UX-207` already proved the shape works — the decision screen is one
coherent unit answering one question, and it is the part of the page
that reads well.

## Required Fix

1. The sections group into a small number of **chapters** — six to eight
   — each named for a question a reader has, not for a schema key.
2. Navigation moves chapter to chapter; the rail lists chapters, with
   sections nested inside as it already does one level (`UX-271`).
3. Chapters are as tall as their content. **No padding to a fixed
   height** — measured, that would add 31.3 screens to the synthetic run
   and 20.5 to the fixture, a 2.6× longer document made of whitespace.
4. Order is asserted by a guard, so a section cannot drift out of its
   chapter unnoticed (`UX-235` guards the order the page claims; this
   guards which chapter a section belongs to).

## Out of Scope

- **Pagination.** Direction 13 declines it with three reasons the page
  cannot give up: `Ctrl-F` over the whole export (`UX-195`), a link that
  opens what it names (`UX-211`, `UX-225`), and printing. Chapters are a
  change to the document's structure; slides are a change to its medium.
- **Fixed-height blocks**, declined on the measurement: section height
  spans 0.07 to 3.42 screens, a 49x range, because ten sections on
  each run size themselves from the run rather than the layout. A
  fixed cell has two options for a 1,202-row table and both are
  wrong - overflow it, or hide rows the reader came for. Rows are
  bounded instead, by `UX-187`'s cap and `UX-262`'s `Top N`.
- Deciding what the chapters *are* inside this item's Required Fix. That
  decision wants the reader's questions in front of it, and is the first
  thing this item does rather than something it inherits.

## Acceptance Test

The rail lists between six and eight chapters. Every section belongs to
exactly one, asserted by a guard. The document is no taller than it is
today — grouping adds structure, not height — measured on both runs.

## Outcome

🟢 **Done.** Seven chapters, each named for a question a reader has.

```text
chapter                                       sections (1,202 / fixture)
What should I do?                                    6 / 6
What if I change this?                               2 / 2   (3 with an inventory)
What changed since last time?                        - / -   (needs a comparison)
Where did the time go?                               7 / 6
Was the machine used well?                           4 / 4
Which elements, and how do they connect?            25 / 5
How much of this can I believe?                      1 / 1
Which run is this?                                   3 / 3
```

Seven drawn on both runs, and eight declared: the comparison chapter is
absent on a run with nothing to compare against rather than empty. Both
counts sit inside the acceptance test's six-to-eight.

**What decided the chapters.** The reader's questions, which the schema
already publishes: every payload section carries a `bga:question`, and
`findings` ("What did this run conclude?"), `headline` ("What should I
fix first, and what is it worth?") and `next_steps` ("What should I run
next?") are three spellings of *what should I do*. They are one chapter.

**Why the table is in the viewer and not the schema.** Measured, nine of
the forty-eight sections on the synthetic run are built by the page and
published by no contract at all — the decision panel, the drawn critical
path, the blast box, the element blocks:

```text
rail declared on the rendered sections, before this landed
-              9 sections   decision, evidence, overview, findings, blast,
                            critical-path-drawn, horizon, whatif, summary
decide         2            headline, next_steps
act            2            attribution, signals
prove          4            floors, capacity_verdict, occupancy, confidence
investigate   27            structural, utilisation, pipeline_overhead, element-*
raw            4            attribution_hints, critical_path_detail,
                            run_instance, producer
```

A hint can only name sections the schema has, so a chaptering that lived
beside `bga:question` would leave a fifth of the document unassigned.
The published `bga:rail` is the *fallback* instead: a payload key added
later lands in the chapter its rail already names, and only a section
with neither an entry nor a rail reaches "Everything else" — which is
empty on both runs, and guarded to be.

**Item 2, the rail.** It lists the seven chapters, each a link to the
chapter itself, with its sections nested underneath (7 chapter links +
48 section links at scale; 7 + 27 on the fixture). This also fixed a
disagreement nobody had noticed: `UX-209` grouped the rail by
`bga:rail`, and the nine page-built sections have none — so `decision`,
`findings` and `summary` were all listed under **raw**. The rail and the
document now use one grouping by construction.

**Item 3, and the acceptance's third clause: no height.**

```text
                        before      after
1,202-element run       18.51 scr   18.10 scr
golden mixed_task_kinds 11.00       10.99
golden + a source inv.  11.91       11.89
golden export, 1440x900 11.32       11.29
```

The document is *shorter*. Seven chapter headings cost 2.3–2.9% of the
page, and they are paid for by the space the sections no longer need
between them — inside a chapter the boundary carries that separation, so
`section > h2` drops from a 2rem top margin to 0.9rem. Direction 13's
refused alternative is guarded too: section heights still span 16× on
the fixture and 42× on a phone, so a layout that equalised them would
redden a test rather than pass as "chapters".

**Item 4, the order guard.** `test_the_report_has_chapters.py`, reading
the booted export's own document — which chapter each section is in,
that the chapters come in the declared order, that nothing sits beside
them, and that a block `UX-278` builds when an anchor is followed joins
its chapter instead of landing under the identity block.

**`UX-285` is now a chapter boundary rather than two placement passes.**
That item shipped `placeIdentityLast` and `placeBlast` a day earlier;
both are deleted. The identity closes the page because its chapter is
last, and the blast control sits beside `resource_blast` because the
chapter declares that order — measured after the change: identity at
97–99% of the scale run and 95–98% of the fixture, blast at 24% and 31%,
0.99 and 0.94 screens after the end of `findings`. Every guard `UX-285`
landed still passes, unchanged, against the new mechanism.

**A defect this item introduced and the guard that would not have caught
it.** `chapters.js` was not in the server's `ASSETS` tuple, so the
served page 404'd on the import, `boot` never ran, and the report was
the word "Loading…" in a real browser. The guard on that list named
`app.js`, `sql.js` and `perfetto_page.js` — the three entry points,
which are the part of a module graph that cannot go wrong. It now
follows every import from each entry and asserts the traversal reached
at least eight modules, so an import regex that matched nothing would
redden rather than pass.

**Falsification.** Eight mutations, each asserted to have landed:

```text
C1  boot never groups                          7 chapter guards red
C2  the identity chapter is declared first      8 red across two files
C3  two chapters folded into one (five left)    the count guard red
C4  `producer` loses its entry and its rail     5 red - it reaches
                                                "Everything else"
C5  fileInChapter does nothing                  the late-block guard red
C6  chapters get `min-height: 100vh`            the padding guard red
C7  chapters.js removed from ASSETS             the module-graph guard red
C8  every section gets `min-height: 100vh`      the 49x-range guard red
    (Direction 13's refused proposal)
```

**C1 first ran green on four of eleven guards**, because a page with no
chapters at all has no chapters to be wrong about: three tests iterated
over an empty list and passed. They assert the page drew some now — the
same vacuous-pass hole `UX-288`'s populations had, in a different shape.
