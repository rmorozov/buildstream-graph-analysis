# UX-419: a map population is bounded by nothing, and the sweep cannot see it

**Priority:** High | **Status:** 🔴 Not Started | **Found by:** UX-411's measurement | **Serves:** anyone whose run has many binaries or many tasks | **Topic:** viewer

## Motivation

`UX-413` made a long table open bounded whether or not it has a column
worth ranking by. It bounds **tables**. A section whose payload is a
*map* — one measure per key — is drawn by `renderPairs`, which has no
bound at all:

```js
for (const [name, value] of Object.entries(object)) {
```

Measured by rendering each of `UX-396`'s two ranked maps at 120 keys
in the shim, exactly as `UX-400`'s sweep does for record populations:

```text
by_binary            entries 120   drawn 120   shown 120   tables 0
wall_clock_share_us  entries 120   drawn 120   shown 120   tables 0
```

Every pair drawn, nothing hidden, no table and therefore no badge, no
filter, no preset and no `N of M`. `UX-360`'s volume budget is measured
on three fixtures, and the largest of them has eleven of these keys.

The sizes are not hypothetical. `wall_clock_share_us` is one duration
**per task uid**, so it is the element population by another name —
1,202 keys on the `gen-synthetic` scale run. `by_binary` is one count
per binary name across the whole build; the round-60 capture published
`cmake 248, sh 150, make 99, c++ 88, cc1plus 51, …`.

**And no instrument would have found it.** `UX-400`'s sweep discovers
its populations as *arrays of objects*:

```js
.filter(([, v]) => Array.isArray(v) && v.length
                   && v.every((r) => r && typeof r === "object" ...))
```

A map of numbers is not one, so the whole zero/one/many sweep — the
file written precisely to stop the next population shipping the same
three bugs — steps over every section of this shape.

## Required Fix

- Bound a long pair list the way `UX-413` bounds a long table: past
  `TABLE_OPENS_BOUNDED_ABOVE` entries, show the first
  `TABLE_OPENS_BOUNDED_ABOVE` in the payload's order, say `40 of 120`,
  and give one control that shows the rest. `boundCards` is the same
  shape for a different element and is the obvious thing to generalise.
- **Extend `UX-400`'s sweep to map populations**, at zero, one and
  many. The bound is worth less than the instrument: this defect
  existed because the sweep's discovery rule has a shape-shaped hole,
  and the next map section will fall in it too.

## Out of Scope

- Turning a ranked map into a table. That is a bigger change with its
  own reader-facing consequences, and `UX-411` decided the *drawing*
  question separately; this is about volume.
- Choosing an order for the entries. As in `UX-413`, publication order
  is the emitter's decision.

## Acceptance Test

- A map section rendered at 120 keys shows `TABLE_OPENS_BOUNDED_ABOVE`
  entries and a badge naming the total.
- `UX-400`'s sweep discovers `by_binary` and `wall_clock_share_us` and
  asserts all three legs over them, with the ledger for each leg
  empty or filed.
