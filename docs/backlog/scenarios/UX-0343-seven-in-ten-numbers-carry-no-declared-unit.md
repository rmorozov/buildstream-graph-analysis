# UX-343: seven in ten numbers carry no declared unit

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-201 (the rule this is the gap in), UX-341 (which reduces the vocabulary those declarations use) | **Serves:** every payload consumer, and the viewer's own fallback | **Topic:** contracts

## Motivation

`UX-201`'s rule is *declared beats guessed*, and `quantityFor` still
guesses whenever the schema says nothing — name-sniffing `guessQuantity(key)`
and, under `BGA_STRICT_HINTS`, complaining to the console. Counted on
the two committed fixtures, over every numeric leaf of the real
`analyze/v2` document, reading both declaration channels:

```text
golden        208 numeric leaves, 147 with no declared quantity   (71%)
macro_micro   618 numeric leaves, 423 with no declared quantity   (68%)
```

The gaps are not scattered. They are three shapes:

**1. Bare number arrays, and arrays of tuples.**

```text
10x  structural.parallelism.levels.[]
10x  structural.parallelism.width_at_level.[]
10x  structural.sensitivity.top_opportunities.[].[]
```

`top_opportunities` is a list of *lists* — positional pairs with no
field names at all, which is the one shape a schema-driven renderer
cannot say anything about and a consumer has to read the source to
decode.

**2. Fields nobody declared.**

```text
11x  element_join.[].redundancy_count
 9x  element_join.[].dominant_binary.count
 9x  element_join.[].dominant_binary.cpu_share
 9x  structural.bottleneck.choke_points.[].downstream_count
```

Each has an obvious quantity — `count`, `count`, `share`, `count` — and
each currently renders because `guessQuantity` recognises the suffix.
That is the schema gap `UX-201` says the guess exists to *reveal*.

**3. A genuinely polymorphic value.**

```text
24x  findings.[].provenance.evidence.[].value
```

`UX-229`'s provenance rows carry *whatever field the rule read*, so one
static declaration cannot be right. The value's unit is knowable —
`path` names the field it came from — but it has to travel with the row
rather than with the schema node.

**The second declaration channel is part of why this went unnoticed.**
A quantity is declared either as `bga:quantity` on a schema node **or**
as `quantity` inside a `bga:columns` v2 entry — 165 and 36 of the 201
declarations respectively, under two different key names. The first cut
of the census above read only `bga:quantity` and reported 81%; the
correction is in the numbers above, and a reviewer eyeballing
`schemas.py` for coverage has the same trap in front of them.

## Required Fix

Every numeric leaf a published document can emit carries a declared
quantity, by one of three routes: on the node, in the column spec, or —
for `provenance.evidence[].value` — as a `quantity` field on the row
itself, resolved from the `path` it names.

`structural.sensitivity.top_opportunities` becomes a list of objects
with named fields, like every other table in the document.

A guard walks the committed fixtures' real payloads (not the schema
alone, which cannot see which keys a run actually emits) and fails on
any numeric leaf with no declaration, with a declared allowlist for the
handful that are genuinely dimensionless.

## Out of Scope

- Removing `guessQuantity`. It is the fallback that makes an
  undeclared field render *something*, and `UX-201` argues for keeping
  it as a complaint rather than a crutch. This item empties its input;
  it does not delete it.
- The two-channel declaration itself. Columns declaring their own
  quantity is `UX-201`'s v2 column spec working as designed; what this
  item asks for is that a census can read both, which the guard does by
  construction.

## Acceptance Test

On both committed fixtures, every numeric leaf of the emitted
`analyze/v2` document resolves to a declared quantity through either
channel, or appears in an allowlist whose every entry carries a reason.
`top_opportunities` rows are objects with named keys, and the viewer
renders the same section list as before. Running with
`BGA_STRICT_HINTS` set produces **no** `has no bga:quantity` console
warning on either fixture — asserted through the console reader
`UX-334` built, not by eye.
