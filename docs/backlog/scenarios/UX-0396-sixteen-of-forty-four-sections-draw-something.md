# UX-396: sixteen of forty-four sections draw something

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-303 (the shape before the rows), UX-361 (two new shapes), UX-350 (the shape channel), UX-306 (the visual contract) | **Serves:** anyone scanning the report for where the time went | **Topic:** viewer | **Area:** bga

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

## Outcome (round 64, 2026-08-29) — 🟢 Done

### "Carries numbers" is not "has a shape"

The filing named ten sections that "hold quantities and draw nothing".
Measured against the *schema* rather than the DOM — the declaration is
where the unit lives — a section is shapeable when it publishes a
population of numbers that are all **one declared quantity**:

```console
$ # every analyze/v4 key whose numbers share one bga:quantity, n >= 5
attribution                  8 values, all duration_us
blast_radius_distribution    5 values, all count
by_binary                   11 values, all count
wall_clock_share_us         11 values, all duration_us
```

Four, not ten. A section holding eleven numbers in six different units
has nothing to rank, and drawing one anyway is the fiction `UX-407`
removed from `projection` two items earlier in this round, where a
strip read `19050000 → 43200000 across 3 rows` over three numbers that
are not a distribution.

### `attribution` draws where the wall clock went

The one this item gives a shape, and the one that earns it: it is the
section that *asks* the question, its eight buckets are published parts
of a published total, and they sum to it exactly.

```text
Where did the wall-clock go?   attribution
  ▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▇▏▏
  46.1 s in total: 43.2 s work on the chain, 0 ms waiting upstream,
  0 ms capacity full, 0 ms nothing dispatched, 0 ms nothing ready,
  0 ms retries, 2.7 s before the first task, 216 ms after the last
```

No new instrument: `UX-361`'s `bga:decomposition`, declared, and the
page lays out numbers it was handed rather than working out a
remainder.

### The two-state answer

`SHAPES` in the guard is the census the Required Fix asks for: every
shapeable section either names the instrument it draws or says why it
has none, read off the payload rather than off a list, so the next
section that arrives with a population and no shape fails.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| F1 | drop `bga:decomposition` from `attribution` | 2 of 8, incl. `test_the_wall_clock_question_draws_its_answer` |
| F2 | remove `by_binary` from the census (a shapeable section unanswered) | 1 of 8: `test_every_shapeable_section_is_answered` |
| F3 | shorten `wall_clock_share_us`'s reason to four words | 1 of 8: `test_a_section_with_no_shape_says_why` |

### Deviation from the Required Fix

- **"`findings` first" cannot be done as written, and this is the sixth
  false premise of the round.** The bullet says "a finding carries a
  magnitude and a share; the density strip already draws exactly that".
  Measured on this run, one finding of eleven carries `share`, and each
  finding's evidence is in its own units — `path_us` against
  `zero_slack_share` against `envelope_bytes` against a list of steps.
  There is no per-finding magnitude to rank, and deriving one would be
  the page doing analysis (`UX-193`'s rule that the page chooses
  nothing). `TestFindingsCannotTakeTheShapeTheFilingNames` records it,
  and asks to re-open this item if most findings ever start carrying a
  share.
- **Two of the four shapeable sections still draw nothing**, recorded
  with what they would need. `by_binary` and `wall_clock_share_us` are
  *ranked maps* — one measure over many data keys — and none of the
  four instruments draws one. Improvising a fifth here would be a
  shape arriving without a §2 row in the style guide, which the Out of
  Scope forbids and `UX-302` made a design task rather than an `if`.
  **Filed as `UX-411`** before this commit landed, per fixing guide
  §3.11.
- **The census counts four, not ten**, because the filing counted
  "sections with numeric spans" and this counts "sections publishing
  one quantity over a population". Both numbers are real; they measure
  different things, and the second is the one the Required Fix's
  instrument list can act on.
