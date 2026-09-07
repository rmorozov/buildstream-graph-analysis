# UX-674: eighteen font sizes, an h3 larger than its h2, and 130-character lines

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-305 (the conformance checklist), UX-316 | **Serves:** every reader of prose on the page | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
distinct computed font sizes     18   (body/td 15 · section p 16.32 · section h2 16.8 · h3 17.55 · chapter h2 20.8 · h1 22.4 · …)
h3 vs its h2                     17.55 px > 16.8 px
prose line length                ≈ 122 chars (verdict, 993 px) · 133 (finding title) · 127 (next-step reason)
contrast                         fg 17.4:1 · muted 5.74 · accent 7.21 · warn 5.0 (4.47 on --muted-bg)
```

Three sentences a reader has to re-read: the verdict ("chain-bound"
three times, two percentages before the verb, 122-char lines); the
core.bst card's 257-character sentence with five numbers and a
slash-alternative; a provenance sentence with nested dashes, a raw
`>=` and a payload key, and one that ends a 399-character sentence
with "(UX-116)". The styleguide has color and emphasis budgets and
no type budget.

## Required Fix

Styleguide **§4f, "The type scale"**: a four-step scale (body 15 /
small 13 / h2 17 / h1 21; h3 = body at weight 600 and always smaller
than its h2); `p, li > p, dd {max-width: 72ch}`; task ids and payload
keys never inside prose (§4b extended to sentences). The three
sentences above rewritten as the worked examples.

## Out of Scope

- Contrast — every measured pair passes; the one 4.47 (warn on
  muted-bg) is at the boundary and noted, not filed.

## Acceptance Test

Guard: distinct computed sizes ≤ 4 on the golden page; every h3
smaller than its h2; no `p` wider than 72ch. Mutation: add a fifth
size — red.

## Outcome

**Gap measured** (booted golden export, 1440x900,
`tests/unit/test_the_type_scale_is_four_steps.py`'s scan, reproduced
before the fix): 18 distinct `getComputedStyle` font sizes, `h3` at
17.55px (unstyled UA `1.17em` default) above `h2` at 16.8px. The three
named sentences, re-measured fresh rather than re-quoted: the
diagnosis rule (`bga/provenance.py`, 265 chars, raw `>=` + bare
`chain_bound`), the capacity note (`bga/analyzer.py`, 157 chars,
`(UX-116)` unbacktricked), the max-jobs advisor (`bga/findings.py`,
240 chars, `` `notparallel` / raise `` slash + bare `--builders` +
`(UX-83)`). Exact character counts differ from the filing's (399/257),
since the code has moved since; the defects named (raw operator, bare
payload key, bare task id, slash-as-"or", unbounded line) all
reproduced.

**Close measured**: same scan, after the fix — 4 distinct sizes
(`21px/17px/15px/13px`) on both golden and `macro_micro`; `h3` 15px <
`h2` 17px on both; no prose box exceeds 72 widths of its own font's
`0` glyph (canvas-measured, not a re-read of the declared
`max-width`). All three sentences rewritten in place (fixtures
regenerated via `python3 tools/dev_refresh_analysis.py --write`; diff
is the one sentence each).

**Mutation table**:

| mutation | reddened | count |
|---|---|---|
| `.badge` font-size back to raw `.75rem` | `test_distinct_computed_sizes_at_most_four` | 5 distinct sizes (was 4) |
| `h3` font-size back to `1.3rem` | `test_every_h3_is_smaller_than_every_h2` | h3 20.8px >= h2 17px |
| `p, li > p, dd` max-width widened to `130ch` | `test_no_prose_box_exceeds_its_own_72ch` + `test_the_72ch_rule_is_declared` | canvas budget 687px vs box 845px |

Each mutation applied from a pristine `style.css` copy in the
scratchpad, confirmed red, reverted from that copy, confirmed green.

**Side effects of reaching four sizes, both measured and fixed**:
`--draw-tick` moving 11.52px -> 13px reddened two pre-existing guards.
`test_the_page_has_a_volume_budget.py`: `macro_micro`'s opened height
35,813px (was ~34,678), over its 35,000px class budget - moved to
35,900 (styleguide table too), words/controls/nodes unmoved.
`test_the_shape_channel_is_built.py`: a width-series axis's centred
middle tick (11.11%) now overlaps its edge tick's wider label (16.03%
needed) - fixed in `drawings.js`/`style.css` by laying out the
first/middle/last case in normal flow (`margin-left`, which a CSS row
never lets overlap) instead of by absolute percentage, only when
exactly one tick sits between two edge ticks; `decomposition`'s
multi-tick axes are unchanged.
