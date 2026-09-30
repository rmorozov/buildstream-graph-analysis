# UX-1140: a quantity in the decision panel and provenance prints as a raw float or byte count

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H1, M5 | **Serves:** R1, R2 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_quantity_is_formatted_where_it_is_shown.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H1, M5).

Why #1-#3 in `#decision` read "Cores busy 0.12022221619070929" and "Peak RSS 234506240" where the element card formats the same fields as "0.07×" and "144.8 MiB"; `#provenance` shows "0.9998986759763121" three times; 11 such nodes visible. Producer prose mixes "14.3s" and "14.3 s" (23 nodes), and one card reads "78.35s" in its title and "78.3 s" in its evidence.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Every quantity the page draws, in pairs, provenance and producer prose, goes through the one formatter the element card uses.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node outside `code`/`pre` matches `\d+\.\d{5,}` or a digit run glued to `s`/`ms`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

The Why pairs (`factText`) and every provenance evidence value go
through `format.js`'s `quantity` - the formatter the element card
already calls - with the kind the report schema declares at the
evidence path (`quantityAt`, falling back to `guessQuantity` on the
leaf, then to `quantity`'s own 3-place rounding). `data-raw` keeps the
published number. Producer prose has no shared Python helper to
route through, so the unit's space is added in `UX-1149`'s one
typesetter on the page: a number glued to `s`/`ms` gets a space; no
sentence is reworded and the text report is unchanged. Guard:
`tests/unit/test_a_quantity_is_formatted_where_it_is_shown.py` on the
two-plane page, `golden` and `macro_micro`. Mutations: `factText` back
to `String(row.value)`; the typesetter's unit rule removed. The unit
rule spaces only before a space, punctuation or the end, so a name
like `sdk-1s.bst` is untouched.

## Outcome

### The gap, measured

```text
two-plane page (gen-synthetic --seed 1 --store --layers 8 --width 14),
Chromium, as booted, text nodes outside code/pre/script/style/svg/td:
            \d+\.\d{5,}      digit glued to s/ms
  1440      11 (11 visible)   23 (23 visible)
  390       11 (11 visible)   23 (23 visible)
#decision Why: "Cores busy 0.12022221619070929", "Peak RSS 234506240"
#provenance: "0.9998986759763121", "54450000", "121787500"
the guard, every finding hydrated and every fold open, at 1440:
  raw float   golden 0   macro_micro 7    two_plane 11
  glued       golden 28  macro_micro 42   two_plane 21
```

### After

```text
same page, same scan:  1440 and 390: float 0, glued 0
#decision Why: Cores busy 0.12×, Peak RSS 223.6 MiB, CPU burned 471 ms
#provenance: headline.chain_share 42.4%, floors.lb 2.0 min,
  confidence.primary 100.0%, capacity_recommendation.cores_busy 0.51×
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_quantity_is_formatted_where_it_is_shown.py -q
9 passed
$ PYTEST_XDIST= python3 -m pytest <77 files naming format.js/sections.js/app.js/decision.js, or reading published sentences> -q
1211 passed, 36 skipped
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| B1 | `factText` returns `String(row.value)` | `test_no_text_node_prints_a_raw_float[golden]`, `[macro_micro]`, `[two_plane]`, 3 failed |
| B2 | a provenance value back to `String(ref.value)` | `test_no_text_node_prints_a_raw_float[macro_micro]`, `[two_plane]`, 2 failed (golden's records hold no float) |
| B3 | the typesetter's `.replace(GLUED_UNIT, "$1 $2")` removed | `test_no_number_is_glued_to_its_unit`, 3 failed |

Deviation: `test_why_bga_believes_what_it_believes.py` admitted only a
record's own spellings; it now also admits `quantity`'s spelling of
each evidence number. `_typeset` in `test_the_merge_carries_every_field.py`
and `test_the_provenance_names_its_rule.py` also folds the unit's space.
`CPU burned` reads `471 ms` where the Why pair read `0.5 s`: the
card's `duration`, not `primitives.seconds`. A finding's own provenance
fold has no schema in reach (`renderFindings`), so its values use the
leaf's guess and 3-place rounding. Producer prose is not reworded:
"78.35s" beside "78.3 s" (two precisions) and "1 process(es)" stay -
no shared Python helper renders them; the text report is unchanged.

- Merged-tree fix: `quantityAt` reads a table column's unit from the row's `bga:columns`, so provenance paths like `optimization_horizon[0].makespan_after_us` no longer guess (`test_no_number_renders_from_a_guess`).

- Residue fix: `bga/shown.py` (`duration`/`seconds`/`share`, the viewer's rounding) now builds the duration and percent in `findings.py`, `correlate.py`, `provenance.py`, `sources.py`, `report/text.py` prose ("78.35s" -> "78.3 s", "6m" -> "6.0 min", "1.00" -> "100.0%", "process(es)" pluralised, "50000 us" -> "50 ms"); `test_a_title_quantity_reads_as_its_pair` compares a finding title's quantity with the same value in its pairs (mutations: `Confidence: {primary:.2f}` reddens 3, `{path_us / 1e6:.2f}s` 2).
