# UX-1149: backticks and ASCII arrows show as raw characters

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M6 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_reader_text_has_no_backtick_or_ascii_arrow.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M6).

Literal backticks in titles, details and every `?` description ("`bga sweep`", "`cc`"); "-> a resource ... saturated" as a detail prefix and "125.5s -> 54.5s" while `#culprits` uses "→"; " - " as a dash in 96 visible nodes against "—" elsewhere.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Inline code renders as `<code>`, arrows as →, and a detail line drops its leading arrow.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible text node holds a backtick or `->`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

One typesetter, `typeset` in `bga/viewer/format.js`, run once over
`document.body` at boot and on every later insertion (a
`MutationObserver`, so hydrated cards and folds get it too): a
paired backtick span becomes `<code>`, `->` becomes `→`. It skips
`code, pre, kbd, samp, script, style, svg, textarea, select, option,
td` - a table cell is data. `renderFindings` drops a detail line's
leading `->`. The Python text report is unchanged. Guard:
`tests/unit/test_reader_text_has_no_backtick_or_ascii_arrow.py`, booted
on `golden`, `macro_micro` and the two-plane synthetic page. Mutation:
the observer's install removed from `boot`.

## Outcome

### The gap, measured

```text
two-plane page (gen-synthetic --seed 1 --store --layers 8 --width 14,
capture report --json, bga view --export), Chromium, text nodes outside
code/pre/script/style/svg/td:
            backtick         "->"
  1440      67 (43 visible)  3 (3 visible)
  390       67 (43 visible)  3 (3 visible)
first: p.detail "-> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated
- try --capacity N with a higher N, or `bga sweep`..."
```

### After

```text
same page, same scan:  1440  backtick 0, "->" 0   390  backtick 0, "->" 0
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_reader_text_has_no_backtick_or_ascii_arrow.py -q
9 passed
$ PYTEST_XDIST= python3 -m pytest <55 files naming format.js/sections.js/app.js> -q
2 files red, re-based below; then 12 + 239 passed on the re-run
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| A1 | `typesetAlways(document.body)` removed from `boot` | `test_no_text_node_holds_a_backtick_or_ascii_arrow[golden]`, `[macro_micro]`, `[two_plane]`, 3 failed |
| A2 | the `MutationObserver` never installed (one pass at boot only) | the same 3 - hydrated findings are inserted after boot |
| A3 | `renderFindings` keeps the detail line's leading `->` | `test_a_detail_line_does_not_lead_with_an_arrow`, 3 failed |

Deviation: `test_the_merge_carries_every_field.py` and
`test_the_provenance_names_its_rule.py` compared published sentences
with backticks and `->` verbatim against page text; both now compare
the typeset spelling on both sides (`_typeset`). The " - " dash (96
nodes) is not changed: the Required Fix names arrows and code only.
The styleguide is not amended - §4g is also edited by `UX-1141`/`1142`.
- Merged-tree fix: `test_one_bucket_one_row` compares the advice to the hint with its backticks removed, as the typesetter renders `<code>` (stale guard).
