# UX-366: "All rows" shows 25 of 1,202

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-289 (one element table, many presets), UX-349 (the table tools scale with the table) | **Serves:** anyone whose project has more than 25 elements | **Topic:** viewer

## Motivation

Measured on the 1,202-element synthetic run (`bga gen-synthetic
/tmp/scale --seed 1`), exported and booted at 1440x900. Driving the
element table's two controls, re-reading the table after each change
because the handler replaces the node:

```text
control                            rows rendered
baseline                                     25
population = Choke points (1)                 1
population = Critical path (14)              14
population = Leaves (135)                   135
population = All elements (1202)             25
row limit  = All rows                        25
row limit  = Top 10 by element_durations     25
```

**The controls work.** Named sub-populations render in full, up to 135
rows. What does not work is the one a reader reaches for: the population
called **All elements (1202)** renders 25, and the row limit called
**All rows** does not lift it.

The cap is declared, in `bga/schemas.py`:

```python
{"name": "All elements", …, "bound": 25}
```

and `applyPreset` applies it: `preset.bound ? chosen.slice(0, preset.bound) : chosen`.
`Leaves` has no `bound`, which is why 135 rows draw.

The table's caption is honest — it reads **"25 of 1202"** — so the page
is not lying. It is offering two controls whose labels both promise the
whole population and a caption that quietly says otherwise. **1,177 of
1,202 elements cannot be reached from this table by any control.**

## Required Fix

Make "All rows" mean it, or stop calling it that. The two coherent
designs:

- **"All rows" clears the preset's bound.** The limit select is the
  reader's override, and an override that cannot override is furniture.
  Costs page height, which `UX-367` is the budget for.
- **The bound stays and the label states it.** "Top 25" rather than
  "All rows", and the population option reads "All elements (25 of
  1202)" — which is what the caption already says.

Either way the three statements — population label, limit label,
caption — have to agree. Today two of the three are wrong.

## Falsification

At 1,202 elements, select the population that names the full count and
the limit that names all rows, then count `tbody tr`. It must equal
either the population's count or the number the labels state. It is 25
against labels promising 1,202, which is the finding.

**Re-query the table between changes.** The first draft of this
measurement cached the `<table>` node, read 25 everywhere including
`Choke points (1)`, and nearly reported "no control works at all". The
handler replaces the element; a cached reference reads a detached tree.

## Out of Scope

The other tables. `leaf_analysis` draws 135 rows uncapped and
`consolidation_candidates` 26; if a cap is right anywhere it is right
there too, but this item is about the control that says "All".

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The gap, measured

On the seeded 1,202-element run, re-querying the table between changes:

```text
control                            rows visible
population = All elements (1202)             25
row limit  = All rows                        25
```

**1,177 of 1,202 elements could not be reached by any control.**

### After

```text
population        caption                         limit            badge         visible   on "All rows"
All elements      all 1202 elements               Top 25 by …      25 of 1,202        25            1202
Leaves            135 of 1202 elements            Top 25 by …      25 of 135          25             135
Critical path     14 of 1202 elements             All rows         14 rows            14              14
Choke points      1 of 1202 elements              All rows         1 row               1               1
```

### One bound applied twice

The preset carried `{"name": "All elements", …, "bound": 25}` and
`applyPreset` sliced to it **before** `buildTable` saw the rows — so
the reader's limit control was overriding a population already cut.
`buildTable` has bounded tables of more than
`TABLE_OPENS_BOUNDED_ABOVE` rows since `UX-262`, badge and "All rows"
included. The preset's copy was a second mechanism for the same thing,
one layer too high to be reachable. It is gone; the table's own limit
does the work, and `UX-262`'s rule now applies to every view
uniformly rather than to whichever preset happened to omit a bound.

### The caption, and two wrong rewrites

With the preset's bound gone `view.shown` is the whole view, so the old
caption said **"1202 of 1202"** over 25 visible rows — one disagreement
traded for another. Counting the *visible* rows was the second wrong
answer: the limit control changes that number and the caption is drawn
once, so pressing "All rows" left it claiming 25 over 1,202. The
caption states the view's size and the badge states what is shown —
one fact each, the division `UX-208` already made, and neither can go
stale.

### What it cost, and the budget that could not see it

```text
                 height    words  controls    DOM elements
before           54,968   33,864     1,922          12,305
after            54,968   35,031     1,925          22,977
```

Height does not move because a hidden row occupies none; controls move
by three; and **`words` is nearly blind to a table** — the cells carry
no whitespace between them, so `textContent` renders a whole six-column
row as `layer00/mod023.bst9.0 s645falsecmakefalse`, one "word". So
`UX-367`'s budget gained a fifth measure, DOM element count, bounded at
5,500 and 27,500 per size class. A budget that cannot see the page's
largest population double is not measuring volume, and this item is how
that was found — one round after the budget was set.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree.

| # | mutation | reddened |
|---|---|---|
| M1 | `"bound": 25` back on the `All elements` preset | 4 failed, 3 passed — `test_no_element_preset_carries_its_own_bound`, `…can_be_seen_whole`, `…still_opens_bounded`, `…say_different_true_things` |
| M2 | the caption counts `view.shown` again | 1 failed, 6 passed — `test_the_caption_and_the_badge_say_different_true_things` |
| M3 | the caption counts visible rows (stale on "All rows") | 1 failed, 6 passed — same clause, the other way |
| M4 | `TABLE_OPENS_BOUNDED_ABOVE` raised past the population | 4 failed, 19 passed — three in this file plus `test_the_whole_page_is_bounded_too[scale]` |
| M5 | the DOM-element bound set to 12,500 — just above the page **before** this item | 1 failed on the nodes clause alone: *"22977 DOM elements, over the 12500 budget"*. With the preset's bound restored and the same 12,500: **passes**. |

**M5 is the one that had to be designed twice.** The first attempt
deleted the `nodes` assertion and watched everything pass, which proves
nothing — removing an assertion is not a mutation. The question worth
asking about a *new metric* is whether it responds to the change the
old ones missed, and the pair above answers it: at a bound of 12,500
the nodes clause fires with this item in and is silent with it out,
while height, words and controls say nothing in either direction.

### Deviation from the Required Fix

- The filing offered two designs; this is the first ("All rows" clears
  the bound), because the second leaves 1,177 elements unreachable and
  only makes the page honest about it.
- **The round-58 measurement conflated DOM rows with visible rows.**
  Its table read "Leaves (135) → 135 rows" — those were rows in the
  DOM, of which 25 were visible, because `applyTopN` hides rather than
  removes. The defect it reported is real and its `Leaves` row was
  measuring something else.
- **`structured.js` is at 1,498 of `UX-337`'s 1,500-line ceiling.** The
  first draft of the comment on this change put it at 1,516 and the
  guard fired. The reasoning moved to the guard's docstring, which is
  where this repository keeps it anyway — but the module has two lines
  of headroom and the next item to touch it will have to split it.
