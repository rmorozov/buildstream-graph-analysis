# UX-1136: a finding card prints the word "null" between its parts

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-921 | **Found by:** Ruslan's own `bga snapshot` -> `bga view` (2026-09-29), reproduced on a two-plane synthetic store | **Serves:** R1, R2, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_finding_card_prints_no_null.py`

## Motivation

`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114
elements, both planes), exported with `python3 -m tools.bga_view`,
booted in Chromium 1440x900: `article#finding-wait-category` reads

```text
<p class="detail muted">...</p>null<dl class="pairs evidence">...</dl>null<div class="investigate">
```

Every finding card on every page carries two or three: 34 on `golden`,
48 on `macro_micro`. `renderFindings`' `_hydrate` (`sections.js`)
passes its optional children to the native `Element.append`, which
stringifies `null`; `el()` skips it.

## Decomposition

Input classes: a finding with and without elements, provenance, an investigate query and copy text; both fixtures and a two-plane store. The journey extends reading a finding card.

## Required Fix

`_hydrate` hands `append` only the children that exist.

## Out of Scope

The findings' own wording and evidence layout (UX-1137 and the view UI review's rows).

## Acceptance Test

`tests/unit/test_a_finding_card_prints_no_null.py`, booted on `golden`
and `macro_micro`: no text node outside `script`/`code`/`pre` reads
`null`, `undefined`, `NaN` or `[object Object]`. Mutation: drop the
filter, and it reds on both.

## Outcome

## Outcome (round 153, 2026-09-29) — 🟢 Done

**Premise:** held — every finding card carried the text "null", on every page.

### The gap, measured

```text
$ python3 -m tools.bga_view <store>/.bga/runs/20260303T091500Z/run --export page.html   # 114 elements, both planes
booted at 1440x900, text nodes reading exactly "null" outside script/code/pre:
  two-plane store   article.finding x 2-3 each
  golden            34
  macro_micro       48
```

`_hydrate` passed `null` for an absent element list, provenance,
investigate button or copy button to the native `append`, which
stringifies it; `el()` had always skipped them.

### After

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_finding_card_prints_no_null.py -q
4 passed
```

The same probe on the two-plane page reads 0.

### Mutations verified red and reverted (1)

| # | mutation | reddened |
|---|---|---|
| A1 | drop `.filter(...)` from `_hydrate`'s `append` | `test_no_text_node_reads_null[golden]`, `[macro_micro]`, 2 failed |

Deviation: none.
