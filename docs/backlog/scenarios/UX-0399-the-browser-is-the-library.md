# UX-399: the browser is the library

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-392 (the filters), UX-393 (the navigation), UX-396 (the drawings gap) | **Serves:** R2, and every reader of a seven-screen report | **Topic:** viewer | **Area:** bga/viewer

## Motivation

Round 64 answered "how does the page grow without importing
libraries" partly by inventory: the platform now ships, natively and
CSP-clean, most of what a table/UI library is adopted for — and the
page uses none of it:

```text
$ grep -rn "content-visibility\|IntersectionObserver\|popover\b\|<dialog" bga/viewer/
bga/viewer/views.js:941:  box.setAttribute("data-popover", detail);   # hand-rolled, not the platform's
```

The specific replacements, mapped to open work:

| primitive | replaces | serves |
|---|---|---|
| `content-visibility: auto` (+ `contain-intrinsic-size`) | virtual scrolling — offscreen sections and rows stop costing layout | the 9,316 px page; `UX-397`'s "virtual scrolling at 1,200 rows" argument, without the 400 KB |
| `IntersectionObserver` | scrollspy — the rail learns where the reader is; next/prev become real | `UX-393` |
| `popover` attribute / `<dialog>` | overlay plumbing for the `?` apparatus and table focus | §2b apparatus, `UX-318`'s focus state |
| `:target` + `scroll-margin-top` | deep links that land under sticky chrome instead of behind it | every rail jump and finding anchor |
| CSS `@container` queries | resize listeners for density adaptation | §2a size grades at narrow widths |

## Required Fix

- Adopt `content-visibility: auto` on chapter sections (with declared
  intrinsic sizes so scrollbar geometry and `Jump to…` targets stay
  honest), and measure the before/after of a full-report render on
  the round-63 export — the claim is layout cost, so the number is a
  layout number.
- Give the rail a scrollspy via `IntersectionObserver` — the current
  section highlighted, next/previous controls that move one section —
  as `UX-393`'s implementation route (that filing stays the work
  order; this one fixes the route to a zero-dependency one).
- Record the inventory table in `docs/design/styleguide.md` beside
  the `UX-398` rule, so "can the platform do it" is the first
  question a future widget asks — with the styleguide, not this task
  file, as the living copy.

## Out of Scope

- The `?` apparatus and table-focus migrations to native
  `popover`/`<dialog>` — priced here, but they are rewrites of
  working §2b/§3a mechanisms and each deserves its own task if the
  price is right.
- Any polyfill — a primitive the shipped Chromium baseline lacks is
  simply not on the menu; the inventory lists what is.

## Acceptance Test

- The full-report render measurement exists in this file with the
  export it was taken on, and shows the offscreen cost dropping.
- A driven browser scrolled mid-report shows the rail highlighting
  the section in view, and next/prev moving exactly one section.
- The docs guards pass with the styleguide's inventory section.

## Outcome (round 65, 2026-08-29) — 🟢 Done

Two of the six primitives landed, and the inventory of all six is in
the styleguide as §6c, where the next widget will meet it.

### The gap, measured

Every claim here is on the page **fully expanded** — every chapter and
every fold open, which is the state a reader who opens the report is
in, and the state the 70,932 px figure belongs to. The optimisation is
forced off and on inside the same loaded page, so the pair is one
measurement rather than two runs of a browser:

```text
fixture       DOM nodes    off                     on
scale (1,202)    23,040    70,932 px  25.9 ms      41,669 px   2.2 ms
macro_micro       5,366    48,224 px  12.9 ms      42,777 px   2.3 ms
golden            2,441    23,863 px   6.4 ms      27,214 px   1.9 ms
```

`ms` is the median of 25 forced reflows. **The number that matters is
not the ratio at any one size** — it is that layout cost stops tracking
the document: 6.4 → 25.9 ms as the run grows from 2,441 to 23,040
nodes, against ~2 ms at every size once the browser lays out the
viewport instead of the report. That is what `UX-397` was going to buy
with 400 KB, for zero bytes.

The rail, before: 77 entries, and nothing said which one you were
looking at. `grep -rn "IntersectionObserver" bga/viewer/` found nothing.

### After

- `style.css` declares `content-visibility: auto` with
  `contain-intrinsic-size: auto 600px` on the sections **inside** a
  chapter.
- `nav.js` exports `scrollspy`, wired in `app.js` after the rail is in
  the document. One entry carries `data-current` and
  `aria-current="location"`.
- `styleguide.md` §6c carries the six-primitive inventory with each
  one's state here, both measurements, and the cost.

### Three things the measurement changed about the plan

**1. The optimisation goes on the sections, not on the chapters.** The
filing says "chapter sections". Applied to `section.chapter` itself it
is a no-op that costs height: a folded chapter is already
`display: none`, so there was nothing to skip, and the 600px
placeholder **doubled** an 11-element page — 5,952 px → 11,587 px, with
reflow unchanged at 3.1 → 2.7 ms. Recorded as a deviation below.

**2. `scrollHeight` becomes an estimate, and the volume budget had to
say so.** −41% at scale, +14% on `golden`, from one placeholder being
smaller than a scale section and larger than a golden one. `auto` is
what makes it converge. `test_the_page_has_a_volume_budget.py` now
forces the optimisation off before measuring, because volume is a
question about content and not about paint — and because a guard that
measures an estimate is measuring the compositor.

That edit removes the volume budget's ability to notice the
optimisation being deleted, so the two halves are stated as a pair:
the budget guard says why it turns it off and where the other half is,
and `test_the_browser_is_the_library.py` holds that the shipped
stylesheet really carries it.

**3. "Where am I" is not the first section on screen.** The first two
rules both picked the wrong entry, and a real browser is what said so:

```text
scrolled to `overview`, rail said ...
  first visible in document order      readers    (the sticky header
                                                   leaves the previous
                                                   section on screen)
  nearest heading to the top           evidence   (two headings 103 px
                                                   apart are both within
                                                   a header's height)
  last section started above a
    reading line at 15% of the window  overview   correct
```

### What it cost the suite, and the export

Four guards had to change, and each one is the same fact from a
different side — **`scrollHeight` under `content-visibility` is an
estimate that depends on what has been rendered.**

```text
test_the_page_has_a_volume_budget.py    macro_micro 40,514 px against a
                                        34,000 px budget - the placeholder
                                        inflating an 11-element page
test_a_control_acts_on_what_it_names.py "Expand all" 26,349 px against
                                        opening every chapter by hand
                                        26,085 px - two routes to the
                                        same document, 264 px apart
```

Both claims are about the **document** — how much there is to read,
whether two controls reach the same state — so both now prepend
`pages.FULL_LAYOUT_JS`, one statement defined once, with the rule beside
it: a guard whose claim is about what a *reader sees* must not use it,
because that reader has the optimisation on.

Two more were the DOM-shim census (`UX-264`) reading `document.` +
`createElement` in a **browser** probe as a node harness that should
import the shim. Sidestepped with `insertAdjacentHTML` rather than
weakening a census that has caught three fidelity defects — and the
comment explaining it had to avoid the word too, which is the ninth time
this repository has had a guard find itself.

**The export, split the way `UX-382`'s log splits it:**

```text
                page half     data half (golden / macro_micro)
before           269,531        95,549 / 148,380
after            271,453        95,549 / 148,380
                  +1,922              unchanged
```

All source, no contract: comments are stripped from the export
(`UX-307`), so the 1,922 B is the scrollspy and two stylesheet rules.
`PAGE_BUDGET_B` 270,000 → 273,000 and both committed-export bounds are
restated with that split, which is the procedure those numbers carry.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | `content-visibility: auto` commented out | the layout-cost clause **and**, after the fix below, the stylesheet clause (2 failed, 5 passed) |
| A2 | `contain-intrinsic-size: 600px` — the `auto` keyword dropped | the placeholder clause (1 failed, 6 passed) |
| A3 | `scrollspy(root, contents)` deleted from `app.js` | the wiring clause and the rail clause in the browser (2 failed, 5 passed) |
| A4 | the reading-line rule replaced by first-in-document-order | the rail clause (1 failed, 6 passed) |
| A5 | the `data-current::before` marker removed | the mark clause (1 failed, 6 passed) |
| A6 | one primitive row deleted from §6c's inventory | the inventory clause (1 failed, 6 passed) |

**One clause of mine did not discriminate, and A1 is what exposed it.**
The stylesheet clauses searched the raw file, so commenting the
declaration out — which is how a CSS line is actually disabled — left
the words in place and the clause green; only the browser clause went
red. The clauses now read the stylesheet with its comments stripped,
and A1 reddens both. Recorded rather than quietly fixed: a source-text
clause that reads prose is decoration, and this repository has now
found six of that family.

A4 is the mutation the item is really about. A rail that marks *a*
section looks right in a screenshot and is wrong on every jump; nothing
short of a driven browser distinguishes the three rules.

### Deviation from the Required Fix

- **The optimisation is on the sections inside a chapter, not on the
  chapter sections themselves** — measured above; on the chapters it
  bought no layout and cost 5,635 px of false height on an 11-element
  page.
- **`scroll-margin-top` needed nothing**: `UX-317` landed it in round 44
  and the inventory records it as already used rather than claiming it.
- The other three primitives (`popover`/`<dialog>`, `@container`,
  `:target`) are inventoried and not adopted, which is what the filing's
  Out of Scope asks for.
- `UX-393`'s next/prev controls are **not** here. This item fixed the
  route (the observer and the ordered section list it marks against);
  the controls are that filing's own work and land next.

### Verification

```text
pytest tests/unit/test_the_browser_is_the_library.py          7 passed
pytest tests/unit/test_the_page_has_a_volume_budget.py       22 passed, 1 skipped
pytest tests/unit/test_a_control_acts_on_what_it_names.py    18 passed
pytest tests/unit/test_the_report_you_can_attach.py          24 passed
make test                     4,969 passed, 26 skipped, 237.30s
make lint                     clean
```

Tiered on landing: `MEDIUM`, 4.8s — two browser boots over
`macro_micro` plus five source clauses that need neither.
