# UX-411: a ranked map has no instrument

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-303 (the shape before the rows), UX-350 (the shape channel), UX-396 (the census that found this) | **Serves:** anyone scanning a per-key measure for its shape | **Topic:** viewer

## Motivation

`UX-396` swept the sections publishing a population of numbers in one
declared quantity and found four. Two draw. The two that do not are
the same shape as each other:

```text
by_binary            11 values, all count          one call count per binary
wall_clock_share_us  11 values, all duration_us    one duration per task uid
```

Both are a **ranked map**: one measure, many data keys, no order the
schema declares. The four instruments the page owns draw a *series*
(`bga:series`, an ordered array), a *distribution*
(`bga:distribution`, a published percentile record), a *total in
parts* (`bga:decomposition`) and a *value on an axis*
(`bga:interval`). None of them is a ranked map, and `columnStrip` —
the closest existing drawing — is annotation grade and lives beside a
table, while these render as pair lists.

Improvising one inside `UX-396` would have been a fifth shape arriving
without a §2 row in the style guide, which is what `UX-302` made a
design task rather than an `if`.

## Required Fix

- Decide whether a ranked map wants a drawing at all, against
  `UX-305`'s emphasis budget — two sections on the committed fixture,
  and the count grows with the payload rather than with the run.
- If it does: one declaration (`bga:ranking`, or `bga:series` widened
  to a map with a stated order), one control, one §2 row in
  `docs/design/styleguide.md`, and `UX-396`'s census updated from
  "no shape" to the instrument.
- If it does not: say so in the census's reason, and this row closes
  as a decision rather than as code.

## Falsification

Whichever way it goes, `UX-396`'s census is the record: a clause there
already asserts that a section recorded as shapeless draws nothing, so
a drawing that appears without the census moving fails.

## Out of Scope

- The other three instruments. They are declared, drawn and guarded;
  this is about the shape none of them covers.

## Outcome (round 65, 2026-08-30) — 🟢 Done, as a decision

### The decision: no fifth instrument

`UX-396`'s census was right that a **ranked map** — one measure over
many data keys, with no order the schema declares — is a real shape and
is not one of the four. The answer is that it wants no drawing of its
own, on three grounds:

1. **The page already answers "which is biggest", and not with a
   drawing.** Sort a column, choose `Top N by <column>`, type in the
   filter box, read `columnStrip` beside the header. That mechanism is
   general and every table carries it. `UX-305`'s emphasis budget
   spends emphasis once per block; a fifth instrument would be a second
   answer to an answered question, which is what the budget is for.
2. **A ranked map grows with the payload, not with the run** — one key
   per binary, per task uid. A bar per key is unbounded by
   construction, which is the volume `UX-360`'s budget exists to stop.
   `wall_clock_share_us` is the element population by another name:
   1,202 keys on the scale run.
3. **`UX-193`: the page chooses nothing.** Drawing a ranking asserts an
   order the schema does not declare — the decision `UX-413`'s Out of
   Scope deliberately left with the emitter this same round.

This is the first time §2d's rule (*the vocabulary grows only where an
existing shape cannot make the comparison*) has been applied to refuse
a shape rather than to admit one, which is why the refusal is written
down beside the rule rather than only in this file.

### Where it is written, and what guards it

- `docs/design/styleguide.md` **§2e**, beside §2d's rule.
- `test_a_shapeable_population_is_drawn.py`'s `RANKED_MAP`, which is
  what the census reads and what a later round will find first.
- The two census reasons no longer defer: they said *"needs a fifth
  shape and its own filing (UX-411)"* and now say what was decided and
  why.

Two clauses hold it. `test_the_four_instruments_are_the_four_that_exist`
is the filing's own falsification — a drawing that appeared without the
census moving fails. `test_the_ranked_maps_are_decided_rather_than_pending`
is new and asserts the second state is a *decision*: a reason that
defers again reddens.

### What the measurement turned up, filed rather than folded in

Rendering both sections at 120 keys — the size `UX-400`'s sweep uses —
in the same shim:

```text
by_binary            entries 120   drawn 120   shown 120   tables 0
wall_clock_share_us  entries 120   drawn 120   shown 120   tables 0
```

Every pair drawn, nothing hidden, no badge, no filter, no preset.
`renderPairs` has no bound, and `UX-413` bounded *tables*. Worse,
`UX-400`'s sweep discovers populations as arrays of objects, so a map
of numbers is invisible to the instrument written to stop exactly this.

Filed as **`UX-419`** (High). It is a bound, not a drawing, which is
why it is not this row — and `UX-400`'s Out of Scope says a real
failure a sweep turns up is its own filing.

### Mutations verified red and reverted (2)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| E1 | a census reason goes back to deferring ("needs a fifth shape and its own filing") | `test_the_ranked_maps_are_decided_rather_than_pending`; 1 failed, 8 passed |
| E2 | `by_binary` claims a fifth instrument, `"ranking"` | `test_the_four_instruments_are_the_four_that_exist`, `test_the_ranked_maps_are_decided_rather_than_pending`, and `test_every_declared_instrument_is_on_the_page` in the browser; 3 failed, 6 passed |

E2 is the filing's own Falsification clause, and it goes red three
ways: the vocabulary is closed, the decision is recorded, and the page
does not draw what the census claims.

### Deviation from the Required Fix

- **None.** The Required Fix offers two outcomes and this took the
  second: *"If it does not: say so in the census's reason, and this row
  closes as a decision rather than as code."* No `bga:ranking` hint, no
  control, no §2 row for a new instrument — a §2e note recording the
  refusal instead, which §2d's rule needs if it is ever to mean
  anything.
