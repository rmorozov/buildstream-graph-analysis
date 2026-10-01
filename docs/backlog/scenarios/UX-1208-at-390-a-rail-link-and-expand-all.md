# UX-1208: at 390 a rail link and Expand all keep the reader's place for Back

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_narrow_page_keeps_its_place.py` (`test_back_after_a_rail_link_or_expand_all_lands_where_the_reader_read`)

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Residue track H (`840758fb`, `f5122e71`, `7363a773`) left two at 390x844: a rail link pressed from the opened rail lands Back at the page top, because opening the rail moved scrollY to 0 before the entry was saved (walk N3: scrollY 9,082 -> 0, #elements 9,215 px below); Expand all at 390 leaves scrollY at 24,872.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

At 390, Back after a rail link pressed from the opened rail and after Expand all lands where the reader was before the rail opened.

## Out of Scope

1440, where Expand/Collapse all restore (round 159, H).

## Acceptance Test

At 390, the reader's scrollY before opening the rail is restored within one row after Back, for a rail link and for Expand all; a guard in `test_the_narrow_page_keeps_its_place.py`. Mutation: restore the defect, and the guard reds.

## Decision

The round-160 architect (`arch160/B.md`), as shaped:

```text
Route:     the page remembers the reader's last place below the rail (a closure lastPlace = {scrollY, anchor top}, written on scrollend only when the rail's bottom is above the viewport - no history writes), and keepPlace(railed) writes that place into the entry instead of window.scrollY (0 after the reader climbed to the static folded rail); Expand all from the opened rail takes the same path.
Rejected:  land the anchor at its scroll margin - measured on the 1,202 page at 390, #elements lands 80 px under the top while the walk's reader stood 133 px above it: 53 px, outside the one-row (24 px) bound; replaceState on every scroll - history writes per gesture against Chrome's navigation throttle (bookkeeping r152); a sticky folded rail - reverses UX-1145 (168 of 844 px stuck).
Files:     bga/viewer/app.js boot(): keepPlace (:1152-1158), the capture click listener (:1163-1186), one new scrollend listener beside them; tests/unit/test_the_narrow_page_keeps_its_place.py new _RAILED expression + test_back_after_a_rail_link_or_expand_all_lands_where_the_reader_read (1,202 page via pages.two_plane_run(..., ("--layers","20","--width","60"))).
Guard:     test_the_narrow_page_keeps_its_place.py - at 390, reader scrolls to Y (>2 screens), climbs to 0, opens the rail, presses a rail link (and, second param, Expand all), Back: |scrollY - Y| <= LINE_PX (24).
Mutation:  keepPlace(railed) back to window.scrollY -> Back lands 0, red. Keep test_back_after_the_narrow_rail_s_expand_all_lands_the_reader_s_anchor green.
Class:     product.
Split:     one judgement track on opus (UX-1039: architect-shaped judgement); after UX-1215/1217. Probe (scratch/arch160/p1208.py): a programmatic title press at scrollY 9,530 does NOT move scrollY to 0 (sticky, 10,204); 0 is the reader climbing to the static rail - the track replays that path, not a programmatic press. Expand all's 24,872 was not reproduced here; the track measures it first.
Question:  none. Budget: no controls, nodes, words or height; app.js bytes not prototyped - must fit 3,292 B page-half headroom shared with UX-1209 (~190 B) and UX-1212.
```

The track took that route with three changes. `railed` is any press inside the opened narrow rail, not only Expand all: a rail link reached `keepPlace(false)` and wrote the anchor's top from the page top (Back 0). The place carries the hash it was read under, and is used only while the hash is unchanged, so a traversal that did not scroll cannot hand one anchor's top to another. With no such place the old path stands (`at: null`, the anchor at its margin), so `test_back_after_the_narrow_rail_s_expand_all_lands_the_reader_s_anchor` keeps its claim. Not closed: a reader who stopped below the rail and then read at the top before opening it gets the lower place; a browser without `scrollend` keeps the old behaviour. Expand all's 24,872 did not reproduce: after the press scrollY read 144 (1,202 page) and 95 (golden, macro_micro).

Follow-up (the verifier's wheel climb): a wheel climbs in notches and each lull is a `scrollend` with the rail still above, so the climb overwrote the place. A stop above the previous stop under the same hash is now a climb and keeps the place; a dwell was rejected because its threshold is a guess between a notch's lull and a reader's pause (the verifier's reader dwelt 600 ms). A reader who scrolled up to reread and then climbed gets the lower place.

## Outcome

**The gap measured** (guard against `24b64b40`'s `app.js`; 390x844, Chromium; Y = min(9000, the page's last scroll)):

```text
big link         {'y': 9000, 'after': 10709, 'back': 0}
big all          {'y': 9000, 'after': 144, 'back': 0}
golden link      {'y': 7224, 'after': 8732, 'back': 0}
golden all       {'y': 7224, 'after': 95, 'back': 0}
macro_micro link {'y': 9000, 'after': 11395, 'back': 0}
macro_micro all  {'y': 9000, 'after': 95, 'back': 0}
6 failed, 14 deselected in 30.96s
```

**The close measured** (same, after; plus `heavy_binary_run`, the `--workload binaries` variant):

```text
big / heavy / golden / macro_micro, link and all   back == y, off 0 (8 of 8)
narrow-page + rail-tools + population key + rail click + reveal re-folds + filter-back + volume budget
                                                   123 passed, 3 skipped in 287.07s
page half (golden, macro_micro)                    156,767 -> 156,875 B (+108) of 160,000
eslint bga/viewer                                  0 problems
```

**Mutation table** (each written from a saved copy of `app.js`, restored after; `-k rail_link`, 6 cases):

| Mutation | Reddened | Count |
|---|---|---|
| `24b64b40`'s `app.js` (the defect) | all six, back 0 | 6 failed |
| `keepPlace(railed)` writes `window.scrollY`, `at: null` | all six, back 0 | 6 failed |
| `scrollend` records nothing | all six, back 0 | 6 failed |
| `railed` only for Expand all (`all?.closest`) | the three `link` cases | 3 failed, 3 passed |

The hash key on the place is not discriminated by this guard (no traversal without a scroll in its path).

**Deviation (follow-up).** The verifier's wheel climb (`page.mouse.wheel`, 100 px notches) landed Back 300 px, 5,700-8,600 px from the read place. The guard gains `climb="steps"` (400 px `scrollBy` per `scrollend`): on `e7a26758` 6 failed (back 166-497); after, the guard 12 passed (83 with the related files and the page-half budget), and the verifier's script reads delta 0 in 4 of 4.
Mutations: `climbing = false` 6 failed; the hash clause dropped survives (12 passed: no hash change in the path). Page half 156,875 -> 156,923 B (+48).

**Deviation (second follow-up, walk N2 and N8).** The guard gains `climb="reread"` (up to y/2, 2 s dwell, stepped climb) and `press="chapter"` (the last chapter row), and asserts the rail is folded after Back as before the press: 27 cases. On `a69d1d88` 15 failed (every reread, every chapter); after, 27 passed; the walk's script on the 1,202 page reads delta 0 for link, chapter and Expand all at 6000 and 3500.
N2: a climbing stop the reader dwelt on over 1 s before scrolling on is the place read. Height cannot tell a reread from a notch (a wheel stops at every height), time can: notches lull 100-600 ms (guard, verifier), the walk's reread 2 s. The Decision's "gets the lower place" is closed; a reader who pauses over 1 s mid-climb gets that pause.
N8: the chapter row keeps the rail open (`UX-1171`), and the open rail sat 623-772 px tall above the restored scrollY (5,851). A saved place now carries the rail's fold, and popstate folds it back before the scroll.
Mutations (from a saved copy; 27 cases): dwell never met 9 failed (reread); every climbing stop taken 18 failed (steps, reread); popstate rail fold dropped 9 failed (chapter); `here()` without `rail` 9 failed. Page half 158,192 -> 158,332 B (+140); related Back/rail files and the volume budget 203 passed, 3 skipped.
