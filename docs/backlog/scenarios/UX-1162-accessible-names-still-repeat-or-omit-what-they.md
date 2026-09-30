# UX-1162: accessible names still repeat or omit what they name

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_every_control_and_drawing_names_what_it_shows.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

AX tree, every fold open: 11 of 17 `aria-details` are still the range sentence and plotted values are absent; shared names remain: 87 "⌕", 33 " as Markdown", 18 "Copy query", 15 "Rows shown", 8 "Copy 14 rows", 6 "As table" (`a.inspect` 77/1, `copy-sql` 14/1, `twin-toggle` 6/1, `copy-markdown` 17/1, `copy-rows` 17/8, `top-n` 4/1, `table-filter` 3/1 nodes/names); the `#utilisation` strip is missing from the AX tree; distribution strips' names do not lead with what they show.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each control's name says what it acts on, each drawing's details carry its plotted values, and the `#utilisation` strip is in the AX tree.

## Decision

- **Controls**, after `UX-1155`'s shape (visible label first, then the thing): a table's tools name the table by its `data-table` key's titled parts (`named`, `structured.js` `interrogable`) - "Copy 5 rows: <table>", "as Markdown: <table>", "Rows shown: <table>", "Filter rows: <table>"; `a.inspect` "Find <uid>"; `copyButton` takes what it copies ("Copy query: <question>", "Copy finding: <title>", `questions.js`, `sections.js`); a twin toggle is labelled by itself and its drawing (`nameDrawing`, `drawings.js`), so "As table"/"As drawing" still reads. A copy control's acknowledgement keeps the name's tail (one `say` helper, `controls.js`).
- **Drawings**: `columnStrip`'s route is `valueRoute` over its sorted row values - no new helper; `strip` takes `name` from both callers (`sections.js`, `structured.js`), so a published strip's name leads with what it shows.
- **`#utilisation`**: its strip sits in the closed `Buckets` fold (`details.map`), out of the tree exactly as it is out of sight; opening the fold puts it in (measured). The walk's "every fold open" opened chapters only. No code change; the guard opens the fold and holds it there.
- **Guard** `tests/unit/test_every_control_and_drawing_names_what_it_shows.py`, `Browser.ax`: the two-plane page at 1440 and 390, `golden` and `macro_micro` at 1440 - the seven kinds share a name only when they act alike; no `aria-details` target reads a bare range, and a column strip's lists its `data-n` values; every density strip's name leads with a word; `#utilisation`'s strip is an `image` once its fold is open.
- **Mutation**: each site undone alone.

## Out of Scope

The visible labels; the names `UX-1155` fixed.

## Acceptance Test

On the two-plane page no two controls of one kind share a name, no `aria-details` is a bare range, and `#utilisation` appears in `Accessibility.getFullAXTree`. Mutation: restore one defect, and the guard reds.

## Outcome

**The gap, measured.** Chromium's tree (`Browser.ax`), 1440x900, every chapter open plus `#utilisation`'s fold and the first question fold (the guard's state); `nodes/names`, HEAD `3e6feb45` (a `git archive` copy) against this commit; `gap.py` over the guard's own `_TAG`.

```text
                 two-plane         golden            macro_micro
                 before  after     before  after     before  after
a.inspect        77/1    77/34     15/1    15/4      62/1    62/11   one name per href
copy-sql         20/2    20/20     18/2    18/18     23/2    23/23
twin-toggle       6/1     6/6       4/1     4/4       7/1     7/7
copy-markdown    18/1    18/18     10/1    10/10     20/1    20/20
copy-rows        18/9    18/18     10/5    10/10     20/11   20/20
top-n             5/2     5/5       1/1     1/1       6/2     6/6    one is the "I am" select
table-filter      4/2     4/4       1/1     1/1       2/2     2/2    one is "Ask about element"
details bare     11/17    0/17      7/11    0/11     16/23    0/23
strips unled      3/14    0/14      0/7     0/7       3/19    0/19
```

`#utilisation`: its strip is in the closed `Buckets` fold (`details.map`, `open=false` after the chapters open); with the fold open, before any change, the tree holds `image "Buckets: 0 ms → 8.1 min across 6 rows."`. The walk's instrument opened chapters only.

**The close, measured.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_every_control_and_drawing_names_what_it_shows.py -q`: `16 passed, 2 skipped in 8.75s`. Golden page with its data removed (`TestTheSizeDiscipline`'s instrument): 149,744 B -> 150,060 B, **+316 B** - over the 150,000 B `PAGE_BUDGET_B` until `UX-1167` raises it to 160,000.

**The mutation table.** `mutate.py`, each site undone alone, then the copy restored:

| mutation | reddened | run |
|---|---|---|
| M1 `a.inspect` unnamed (`structured.js`) | `share` x3 | 3 failed, 13 passed |
| M2 Copy finding without its title (`sections.js`) | `share` x3 | 3 failed, 13 passed |
| M3 Copy query without its question (`questions.js`) | `share` x3 | 3 failed, 13 passed |
| M4 twin toggle unlabelled (`drawings.js` `nameDrawing`) | `share` x3 | 3 failed, 13 passed |
| M5 `copy-markdown` unnamed (`structured.js`) | `share` x3 | 3 failed, 13 passed |
| M6 `copy-rows` without its table | `share` x3 | 3 failed, 13 passed |
| M7 `top-n` "Rows shown" | `share[two_plane, macro_micro]` | 2 failed, 14 passed |
| M8 `table-filter` "filter rows" | `share[two_plane]` | 1 failed, 15 passed |
| M9 `columnStrip` routed to its sentence | `bare` x3, `every_row` x3 | 6 failed, 10 passed |
| M10 `columnStrip` route cut to 3 values | `every_row` x3 | 3 failed, 13 passed |
| M11 published strip unnamed (`sections.js`) | `leads[two_plane, macro_micro]`, `share[macro_micro]` | 3 failed, 13 passed |
| M12 the guard leaves `#utilisation`'s fold closed | `util[two_plane]` | 1 failed, 15 passed |
| restored | - | 16 passed, 2 skipped |

M7/M8 cannot red on `golden`: one table offers each. M11's `share` is the twin toggle, labelled by the drawing. M12 mutates the instrument, not the page: the defect was the instrument's state. All question folds open at once overruns `cdp.mjs --ax` on the review page (`unsettled top-level await`), so the guard opens the first.
