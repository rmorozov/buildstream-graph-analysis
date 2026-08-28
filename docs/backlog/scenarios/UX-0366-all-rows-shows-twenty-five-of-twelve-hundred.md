# UX-366: "All rows" shows 25 of 1,202

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-289 (one element table, many presets), UX-349 (the table tools scale with the table) | **Serves:** anyone whose project has more than 25 elements | **Topic:** viewer

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
