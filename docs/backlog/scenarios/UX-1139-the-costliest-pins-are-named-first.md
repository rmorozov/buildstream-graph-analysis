# UX-1139: the capacity finding names whichever pinned elements sort first by name

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-116 | **Found by:** Ruslan's own `bga view` (2026-09-29), with UX-1138 | **Serves:** R2, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_costliest_pins_are_named_first.py`

## Motivation

`summarize_plane2_capacity` (`bga/correlate.py`) sorts
`pinned_elements` by name, and the capacity finding's sentence names
`pinned[:3]` with no count of the rest: "Free capacity you already
have: a.bst, b.bst, c.bst asked its native build for -j1". With many
pins the three named are alphabetical, not the ones worth fixing, and
the reader cannot tell three from thirty.

## Decomposition

Input classes: one pin, three, more than three. The journey extends reading the capacity recommendation.

## Required Fix

Pinned elements are ordered by `work_span_s`, longest first; past three
the sentence adds "and N more elements", in the finding and the text
report.

## Out of Scope

Which elements are pinned (UX-1138).

## Acceptance Test

`tests/unit/test_the_costliest_pins_are_named_first.py`: five pins with
spans 1/50/5/300/20 s order 300, 50, 20, 5, 1, and the sentence reads
"d.bst, b.bst, e.bst and 2 more elements asked", in the finding and the text report.

## Outcome

## Outcome (round 153, 2026-09-29) — 🟢 Done

**Premise:** held.

### After

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_costliest_pins_are_named_first.py -q
3 passed
$ python3 tools/dev_refresh_analysis.py
0 of 2 committed analysis document(s) disagree with the analyzer
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| B1 | sort pins by name again | both clauses, 2 failed |
| B2 | drop "and N more" from the finding | the sentence clause, 1 failed |
| B3 | drop "and N more" from the text report | the text-report clause, 1 failed (added at verification) |

Deviation: the size ledger moves `bga/correlate.py` 2943 -> 2947 and `bga/report/text.py` 1967 -> 1968 lines (`dev_sizes.py --adopt --force`).
