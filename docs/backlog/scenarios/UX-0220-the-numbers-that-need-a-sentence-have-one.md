# UX-220: the numbers that need a sentence have one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-201 (the description channel that already renders)

## Motivation

The round-24 review proposed "Why?" popovers on headline metrics and
called them almost free, "because the schema already carries
descriptions". Measured on `main`, that is false exactly where it
matters:

```text
floors             own description: no    described children:  0 / 0
capacity_verdict   own description: no    described children:  0 / 0
occupancy          own description: no    described children:  0 / 0
utilisation        own description: no    described children:  0 / 3
signals            own description: no    described children:  0 / 3
headline           own description: yes   described children:  4 / 6
confidence         own description: no    described children:  2 / 4
```

`floors.certified_us` is the most misreadable number this tool
publishes — a **lower bound certified by the graph and the observed
work, not a prediction** — and the schema says nothing about it at all.
`T∞`, headroom, efficiency and the capacity verdict are in the same
state.

The viewer already renders `description` as a popover, recursively, at
every depth (`UX-201`). The renderer is not the missing piece. **The
descriptions are the deliverable.**

## Required Fix

1. A description on every published node whose meaning is not evident
   from its name — every floor, every capacity-verdict field, the
   occupancy and utilisation members, the three signal arrays. Written
   in the register the tool already uses: what it is, what it is not,
   and what it cannot support.
2. Each says its own bound where it has one — `certified_us` is a
   floor, `chain_ratio` is a share of wall-clock, `efficiency` is a
   ratio against a floor and not against an ideal.
3. `bga analyze`'s text report and `--help` take the same sentences
   from the same constant, so a reworded description cannot leave two
   different explanations in the tool.
4. A guard that a published leaf carrying a `bga:quantity` also carries
   a description, so the next field added cannot arrive mute.

## Out of Scope

- New metrics, or changing what any of them mean.
- Long-form explanation — a sentence or two, with the docs link where
  there is more (`UX-170`'s disputed region is the precedent).
- Viewer work: the popover already renders.

## Acceptance Test

Every leaf in `analyze/v1` that declares a quantity also declares a
description (asserted over the whole schema, not a list). The rendered
page shows `certified_us`'s sentence on hover, read from the schema and
not from a string in the viewer.

Mutations, each asserted red: remove `certified_us`'s description → the
completeness guard fails and names it; put a second wording of it in
`report/text.py` → the one-source guard fails.
