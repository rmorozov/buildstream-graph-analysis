# UX-1188: the compare chapter states how many elements moved and offers them as a bounded, filterable table

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_every_step_past_a_bound_is_bounded.py::TestTheCompareChapterCountsWhatMoved`

## Motivation

Finding: 6 of the review.

`element_deltas.rows` publishes 1,202 rows and `counts` gives 623 grew and 573 shrank; the changed-elements section (`culprits`) draws 4 + 4 of 1,196 changed, says nothing of the rest, and no route looks up one element's delta. Breaks §3k ("its label states what lies beyond it") and §1b; the rule already binds, and this is a missed instance.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

A table over `element_deltas.rows` with the §3 tools, and the "623 grew, 573 shrank" line above the culprits.

## Decision

Class: product.

Architect, round 158 (group C):

```text
Route:     the culprits section states `element_deltas.counts` ("623 grew, 573 shrank of 1,196 changed" - read from the payload, never typed) and its lists become one bounded element table over `element_deltas.rows` built by `buildTable`, in the payload's ranking, with presets "Cost time", "Saved time", "Only in one run" standing in for the three lists.
Rejected:  keep the three lists and add the table beneath - the volume guard opens every fold, so a second, 1,202-row view costs ~+400 px and ~+15 controls on xl_both for the same rows; re-rank in the page - UX-214's second comparison (the comment at element.js:752 holds this).
Files:     bga/viewer/element.js (`renderCulprits`, `culpritRow` retired or kept for the absent group only); bga/viewer/app.js (the `renderCulprits(comparison)` call ~762 only if its signature changes); bga/schemas.py (preset list for the deltas table, beside `element_deltas` ~5605, if presets are declared rather than inline); tests/unit/test_every_step_past_a_bound_is_bounded.py (census gains the two-plane store page, whose second run compares against the first, and `element_deltas.rows`); tests/unit/test_which_elements_caused_the_regression.py (the culprit-list assertions move to the table); tests/tiers.py.
Guard:     test_every_step_past_a_bound_is_bounded.py - on `pages.two_plane_run` (1,202 elements, `--runs 2`: the export auto-compares), the compare chapter's sentence carries `counts.grew` and `counts.shrank` as the payload states them, and the filter set to one uid leaves exactly that row.
Mutation:  hide the count sentence; the guard reds (second: cap the table at CULPRITS_SHOWN rows with no bound sentence).
Class:     product
Question:  lists kept beside the table (+~400 px, +~15 controls), or the table carries them?
```

Owner question open; **default taken, awaiting Ruslan**: the table replaces
the culprit lists, the culprits become its opening sort (the payload's
ranking, `absolute-duration-delta`), and the count line sits above it - no
second population view.

Implementer's deviation from the route: **no presets.** `applyPreset`'s
`where` is equality only, and "Cost time" is `delta_us > 0` - a new
predicate in `tables.js` (another track's file) or a `verdict_kind ==
regressed` proxy that is empty whenever the run's verdict declines
(`_element_deltas` gives every row the run's kind then). The table's own
sort on Change reaches both directions, and "Only in one run" is the
Presence column's filter; the owner's default names the opening sort, not
presets. `buildTable` is called, not edited; the schema's declared
`element_deltas.rows` columns are the table's.

Second deviation: the table does not open in the payload's `|delta|`
ranking. `openingBound` (UX-1185's, not this row's) opens any table over
40 rows on "Top 25 by" its first quantity column, which was `baseline_us`:
the 25 slowest baselines, not the culprits. `delta_us` moves first in
the declared columns, so it opens on "Top 25 by Change": the old "Cost
time" list, which the payload's ranking filtered to `delta_us > 0` already
was, 25 deep. Unsorted, the rows keep the payload's order.

## Out of Scope

How a delta is computed; the culprit ranking.

## Acceptance Test

The §3k census, `tests/unit/test_every_step_past_a_bound_is_bounded.py`, gains a compare page and `element_deltas.rows`: the compare chapter states 623 grew and 573 shrank and the table filters to one element. Mutation: hide the count; the guard reds.

## Outcome

**Gap measured** at `8a531cbb`: `pages.two_plane_run(--layers 20 --width 60)`
exported, the `culprits` section read in Chromium 1440x900; `element_deltas`
from `compare_runs` on the same two snapshots.

```text
payload counts   {'grew': 623, 'shrank': 573, 'unchanged': 6, 'appeared': 0, 'disappeared': 0}  rows 1202
page             delta-counts: null   li: 8   table: null   controls: 9 (8 A.element + collapse)
```

**Close measured**, same page, after:

```text
delta-counts     "623 grew, 573 shrank, 6 unchanged of 1,202 elements."
table            data-rows 1202, mounted 25, "Top 25 by Change"; columns Element, Change, Before, After, Verdict
first rows       layer08/mod018.bst 8.9 s · layer03/mod046.bst 8.3 s · layer17/mod057.bst 8.2 s
filter           last-ranked uid typed -> exactly that one row mounted
```

xl_both (`two_plane_run --layers 20 --width 200`), the volume guard's `_LOOK`,
opened, HEAD's three files against the tree's:

```text
          page_bytes  height  words  controls  nodes
before    144,202     42,037  12,320   886     6,847
after     144,230     42,855  12,387   913     7,035
```

`test_the_page_has_a_volume_budget.py::…[xl_both]` reds: `913 controls, over
the 900 budget` - 25 Inspect links (the opening bound's rows) + 3 thresholds,
filter, Top-N, prev/next, 2 copy, against 8 list links. Bound left for the
integrator, per the brief.

`PYTEST_XDIST= pytest` over the 24 files naming `element.js`, `renderCulprits`,
`element_deltas` or the viewer's budgets: `1 failed, 1720 passed, 3 skipped`
(the xl_both control budget above). `test_which_elements_caused_the_regression.py`
re-based: its shim tests read the table's rows and cells, not `li`s.

**Mutation table** (`TestTheCompareChapterCountsWhatMoved`, 3 tests; and the
re-based shim class, 27 tests in its file):

| mutation (element.js) | reddened | run printed |
|---|---|---|
| count sentence not appended | `test_the_sentence_states_the_payloads_counts` | 1 failed, 2 passed |
| `buildTable(…, rows.slice(0, 4), …)` | `…holds_every_row_and_opens_bounded`, `…filter_reaches_one_element_past_the_bound` | 2 failed, 1 passed |
| "grew" reads `counts.unchanged` | `test_the_sentence_states_the_payloads_counts` | 1 failed, 2 passed |
| rows reversed into the table | `test_the_rendered_order_is_the_payloads_order` | 1 failed, 26 passed |
| sentence drops `appeared` | `test_the_counts_are_the_payloads_own` | 1 failed, 26 passed |
| reverted | - | 3 passed; 27 passed |

The census fixture costs 12.6 s (one 1,202-element two-plane build, export,
two visits).
