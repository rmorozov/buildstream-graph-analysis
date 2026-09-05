# UX-673: sixteen tables offer a Top 10 they cannot fill

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-194 (the Top-N control), UX-349 (the tools scale with the table) | **Serves:** anyone reading a three-row table with a five-option menu | **Topic:** viewer

## Motivation

```text
Top-N selects        20 · 16 offer "Top 10 / Top 25" on tables with ≤ 10 rows (top_actions 3 rows, latent_heavies 1)
```

§3d says the tools scale with the table; a menu whose options
cannot change the rows is apparatus without effect — the §2b
question "is every control's label its effect?" answered no,
sixteen times.

## Required Fix

Presets render only where `rows > n`; a table under the smallest
preset renders no Top-N control at all (the badge still says the
count). Guard: no `select.top-n` option names an `n` ≥ the table's
row count.

## Out of Scope

- The presets' values — `UX-194`'s.

## Acceptance Test

Mutation: render the menu on a three-row table — red.
