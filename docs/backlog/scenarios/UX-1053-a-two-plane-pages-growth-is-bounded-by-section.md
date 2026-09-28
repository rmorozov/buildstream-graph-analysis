# UX-1053: a two-plane page's growth with the run is bounded by the section that grows

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** UX-1050's architect (2026-09-27), styleguide §3e, §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

**Guard:** test_a_findings_element_list_is_bounded.py · inferred r149

## Motivation

From UX-1050's table, on `bga gen-synthetic <d> --store --seed 1` with
`capture report --json` beside the run, 1440x900, the volume guard's
`_LOOK`: from 74 to 1,202 elements with both planes, landed height grew
7,521 → 8,504 px (+983) and controls 711 → 1,053 (+342). Words grew
only 12,424 → 12,974. A population that grows with the run is §3k's
case, and no section cap caught it; moving the size-class bound would
hide it.

## Decomposition

Input classes: both planes at 74, 1,202 and 4,002 elements, with a
store; the journey extended is UX-1050's volume walk over `scale_both`
and `xl_both`.

## Required Fix

A per-section census of landed height and controls on the 74-, 1,202-
and 4,002-element two-plane pages, splitting the store and history
from Plane 2's sections (`binary_cost`, `plane2_coverage`,
`element_join`, native findings). The section(s) that grow get a §3k
cap (a row cap or a fold), so the 1,202 and 4,002 pages land under
`LANDED_HEIGHT_PX` and the controls bound without moving either.

## Out of Scope

The pages and labels themselves (UX-1050); Plane 2's analysis.

## Acceptance Test

The census table pasted in the Outcome; the capped section's guard
green on the two-plane scale page; mutation: lift the cap and the
volume guard's landed or controls clause reds on `scale_both`.

## Outcome

**Gap measured.** Three pages built by `pages.two_plane_run` (`gen-synthetic
--seed 1 --store --runs 2`, `capture report --json` of the newest
snapshot's `plane2.log.gz` as `plane2.json`, exported), the volume guard's
landed state (`FULL_LAYOUT_JS`, `scrollHeight`, `button, input, select, a`)
per `section[data-section]` at 1440x900, base `5f967f09`. Landed px /
controls; every section not listed is 0 px and flat in controls:

```text
                               74 elts    1,202 elts   4,002 elts
decide  findings              4,370/59     5,397/220    7,722/620
decide  (five other sections) 1,884/27     1,884/27     1,884/27
change  (store, history)         93/40        93/39        93/39
time    horizon                   0/22         0/92         0/74
time    critical_path(+drawn)     0/21         0/52         0/52
time    binary_cost (Plane 2)      0/6          0/8          0/8
elements parallelism              0/24         0/47         0/47
elements element-* sections      0/146        0/193        0/194
believe plane2_coverage, element_join_coverage, cpu_time, peak_memory: 0/3 each, all three
outside chapters                389/103      443/114      443/114
TOTAL                          7,209/695  8,290/1,038 10,615/1,425   bounds 7,600/900
```

Store/history and Plane 2's sections are flat. The landed growth (+1,027,
+3,352 px) is all in `findings`, and inside it one card:
`shared-source-blast` 339 -> 1,269 -> 3,594 px, 14 -> 175 -> 575
controls, because `renderFindings` drew `finding.elements` as one link
per element (11, 172, 572). The card count is 14 on all three (`boundCards`
held). Controls also grow in `horizon`/`critical_path`/`parallelism`
(+~120), already bounded (§3k) and under 900 once the card is.

**Close measured.** `renderFindings` hands an `elements` list past
`TABLE_OPENS_BOUNDED_ABOVE` to `renderStructured` - §3k's element-list row,
the `bounded` `app.js` already applies (`UX-1037`); 40 or fewer stay links.
Same census on fresh stores after:

```text
decide  findings              4,370/59     4,411/50     4,411/50
TOTAL                          7,209/695    7,303/868    7,303/854   bounds 7,600/900
```

```text
$ pytest -q -n 2 <16 files naming sections.js/renderFindings> \
    tests/unit/test_every_step_past_a_bound_is_bounded.py
278 passed, 6 skipped in 502.41s
$ pytest -q tests/unit/test_a_findings_element_list_is_bounded.py
3 passed in 0.40s   (controls 11/40/2/2/2 links 11/40/0/0/0 at 11/40/41/572/4,002)
```

**Mutation table** (each restored from a scratch copy of `sections.js`):

| mutation | reddened | count |
|---|---|---|
| cap lifted (`> Infinity`) | `test_the_card_does_not_grow_with_the_run`, `test_past_the_bound_no_name_is_dropped` | 2 of 3 |
| cap at 0 (never links) | `test_under_the_bound_every_element_is_a_link` | 1 of 3 |
| cap lifted, volume guard on `scale_both`/`xl_both` | UX-1050's mutation table, row (d) | - |

Review (#297): the reveal first drew its names as text, so a 572-name
finding linked to no element section. `boundedList` now takes an `item`
renderer (`foldedList` in `structured.js`); the card passes the same link
as the list under the bound, so the head, the tail and each revealed page
are `data-element` links. `test_a_findings_element_list_is_bounded.py`: 5 passed.

| mutation (review) | reddens | count |
|---|---|---|
| card passes no `item` | head/tail links, middle page links | 2 of 5 |
| a revealed page drawn as text | `test_a_revealed_middle_page_is_links` | 1 of 5 |
| `href` the raw uid, not `cssId` | head/tail links, middle page links | 2 of 5 |

Deviation: names still folded in the middle are not links until revealed,
so the cross-reference sees a finding through its shown names. Undeclared surface: §3k's element-list cell in the styleguide now
names the card. The tables above were read from snapshot copies, which
drop the store chapter; exported in place (as `UX-1050`'s `booted` now
does, under a pinned root) the totals read 7,490/712, 8,570/1,053,
10,895/1,439 before and 7,444/712, 7,584/883, 7,584/868 after.
