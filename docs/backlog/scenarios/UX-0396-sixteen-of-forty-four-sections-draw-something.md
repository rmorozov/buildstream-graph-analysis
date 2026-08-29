# UX-396: sixteen of forty-four sections draw something

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-303 (the shape before the rows), UX-361 (two new shapes), UX-350 (the shape channel), UX-306 (the visual contract) | **Serves:** anyone scanning the report for where the time went | **Topic:** viewer

## Motivation

The user asked whether every piece of data that could carry a visual
has one. Counted on the round 63 export:

```text
sections                                      44
  with a drawing                              16
  with rows or numbers and no drawing         10
  neither (prose, identity, apparatus)        18
```

Ten sections hold quantities and draw nothing:

```text
findings                     22 numeric spans, no shape
batch_opportunities          10 rows
next_steps                   14 rows
serialization_point_risks
```

`findings` is the one that matters most: it is the section the report
is *for*, it carries twenty-two numbers, and it is a wall of text. The
page already owns the instruments — `UX-303`'s sparklines and density
strips, `UX-361`'s floors waterfall and interval bar — and `UX-350`'s
shape channel exists to say which instrument a value gets. What is
missing is the sweep that applies the channel to the sections written
before it.

This is not "every section gets a chart". Eighteen of forty-four are
prose, identity, or apparatus and correctly draw nothing. The claim is
narrower and it is measured: ten sections carry ranked or bounded
quantities that one of the four existing instruments already fits.

## Required Fix

- **Walk the ten**, and for each either attach the instrument
  `UX-350`'s channel selects or record why the quantity has no shape —
  the two-state answer, so a later reader knows the omission was
  decided.
- **`findings` first.** A finding carries a magnitude and a share; the
  density strip already draws exactly that, and twenty-two of them in
  a column is the report's own ranking made visible.
- **The instruments are the four that exist.** Nothing new is drawn
  here, which is what keeps this inside `UX-360`'s volume budget and
  `UX-305`'s emphasis budget — a drawing per section is emphasis
  spent, and spending it thirty times would be its own defect.

## Falsification

A guard that walks the rendered sections, and for each section
carrying a ranked or bounded numeric population asserts either a
drawing or an entry in a declared no-shape list with a reason. Today
ten sections satisfy neither.

The other direction, which is the real risk: the export's page bytes
and the emphasis count must both stay inside their existing bounds.
Both are already guarded, and this item is done when the ten are
answered *without* moving either.

## Out of Scope

- New instruments. If one of the ten needs a fifth shape, that is its
  own filing with its own justification.
- The eighteen prose and apparatus sections. They draw nothing on
  purpose, and a shape attached to any of them would spend
  `UX-305`'s emphasis budget on a section with nothing to rank.
