# UX-673: sixteen tables offer a Top 10 they cannot fill

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-194 (the Top-N control), UX-349 (the tools scale with the table) | **Serves:** anyone reading a three-row table with a five-option menu | **Topic:** viewer | **Shape:** judgement

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

## Outcome

**Gap measured.** Booted both committed fixtures through `bga_view.export`
and walked every `table[data-rows]` for a sibling `select.top-n` offering
an `n >= rows`:

```text
golden        15 tables, 10 offer an unfillable n
macro_micro   29 tables, 17 offer an unfillable n (17 unique table keys
              across both fixtures - `producer.contracts` at rows=25
              offers `Top 25`, which the `n >= total` rule also catches)
```

**Close measured.** Same walk after the fix: `golden 0 affected`,
`macro_micro 0 affected`.

**The fix.** `structured.js:849-859`: `for (const n of [10, 25]) { if (n
>= total) continue; ... }`, and the outer gate becomes
`(presets.length && total > 10) || opening` so a table under the
smallest preset gets no `<select>` at all.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| drop `if (n >= total) continue;` and the `total > 10` gate | `TestAPresetOffersOnlyWhatItCanFill::test_no_offered_n_reaches_the_row_count`, `::test_under_the_smallest_preset_gets_no_control` | 2 failed, 29 deselected (was 31 passed) |

**Deviation.** `test_the_report_you_can_attach.py`'s export-bound
assertions were left untouched per brief; measured delta on
`mixed_task_kinds`: 428054 B before, 428104 B after (+50 B, the added
source, not fewer options - no table in that fixture is small enough
for the option removal itself to change its byte count). That test
still passes today (slack in its bound covers +50 B).
