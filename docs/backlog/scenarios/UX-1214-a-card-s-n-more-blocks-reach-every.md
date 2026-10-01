# UX-1214: a card's +N more Blocks reach every element it counts

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_element_view_answers_whole.py` (`test_a_card_s_more_blocks_reach_every_element_it_counts`); the follow-up's `tests/unit/test_a_card_s_more_reaches_every_dependency_both_ways.py`

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P8 (pre-existing): the toolchain card's "Blocks:" lists 40 links then "+1,160 more" as a plain span; the rest is unreachable from the card.

Follow-up 2, the round-160 walk's N3-N5 at `a69d1d88`: the link drops the reader's View and Forward does not
return the link's; focus stays on the off-screen card link; `depends_on` is named nowhere on the page. The guard's
reads on `wide_run`, Chromium 1440x900 (`gap.py`: View Leaves, the card's "+10 more" by a real Enter, Tab, Back,
Forward):

```text
name "+10 more" (no aria-label); after Enter focus not in the box, Tab scrolls back to y 21,646
Enter All elements 50 matched; Back Leaves; Forward Leaves, matched -1 (the filter dropped)
lead "... joined from 7 signals. Each element's direct dependencies are listed on its own card, not here."
title "a word matches any cell; ... a threshold"; sentence "(Element, ..., Observed critical)": no key
```

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The +N more is a link to the rest, as a binaries +N more lands on binary_cost filtered (`UX-1183`).

## Out of Scope

The Blocks list's bound (`UX-1200`, closed).

## Acceptance Test

toolchain's +1,160 more is a link whose target shows 1,160 more elements; a guard beside `UX-1200`'s Blocks guard. Mutation: restore the defect, and the guard reds.

## Decision

Round 160's architect (group A, track T-A), pasted; the session took the filter-link route (the owner's card on
publishing every dependent stays open). As built: `buildTable` splits the `drawn: false` specs off before any
head, cell, sort or Copy sees them, writes each as `data-list-<key>` on the row, and hands them to
`interrogable` as a fifth argument only the query's column list reads - so Copy's columns are the drawn ones
with no change to `rowsMarkdown`/`rowJson`. A press selects the first view (All elements) before filtering; the
href alone lands there on a fresh load, the first view being the default. The Acceptance's "shows 1,160 more" is
asserted as the architect proposes: the filter holds all `dependent_count` (1,200), the 40 listed and the 1,160.
Two side effects: the card's Blocks rest is `a[data-more]` after ", ", so `_line` in the UX-1200 guard reads
"+N more" for dependents; and a not-applied sentence's list of columns now names "Depends on", which the box reads.

```text
Route:     "+N more" becomes a link to the elements table filtered `depends:<uid>`: each row carries its published `fan_in[uid].direct` as `data-list-depends_on` through a declared undrawn spec (`drawn: false` - no cell, no head, no Copy column), matchesKey answers a clause on it by membership, and the link lands as UX-1183's binaries one does (joinHash + filterSection, the All elements view selected).
Rejected:  publishing every dependent (`fan_in[*].dependents` uncapped: +5,008 B gzip+base64 on the walk payload, +14,744 B on xl_both, and it reverses UX-1187's 40 cap); landing on `#blast` (the closure, 1,201 for toolchain, not its 1,200 dependents, and only a command on an export).
Files:     bga/viewer/element.js elementSection (the record.lists loop ~741, span -> a); bga/viewer/tables.js matchesKey (list membership); bga/viewer/structured.js buildTable (skip `drawn: false` specs, write the row attribute), interrogable (Copy's rowsMarkdown/rowJson over drawn specs only); bga/viewer/pairs.js renderPairs/elementSignalTable hint (the undrawn depends_on spec); tests/unit/test_an_element_view_answers_whole.py (beside UX-1200's Blocks guard).
Guard:     on the big page: toolchain's `[data-more]` is an `a`; following it, the elements filter matches fan_in["toolchain.bst"].dependent_count (1,200 - the 40 listed and the 1,160 more; the Acceptance's "1,160" counts only the unlisted), via Browser.measure(fresh_history=True) (UX-1215).
Mutation:  the span back -> no link, red; drop the row attribute -> matched 0, red.
Class:     product
Split:     T-A second commit, after UX-1206 (both write interrogable; 1214's matchesKey sits beside 1206's parseQuery).
Question:  the link reaches every dependent only while no dependent's own list hits the 40 cap - exact on all four built pages (`dep.py`: reversing the published direct lists gives 1,200 = 1,200 and 4,000 = 4,000) - so on a real monorepo it can fall short. Accept that, or publish the reverse relation uncapped (+5.0 KB / +14.7 KB data)? Default: the filter route.
```

Budget (`measureA.py`): `p[data-list] > span[data-more]` at rest - macro_micro 0, walk 1, xl_both 1 (toolchain, "+3,960 more"). So controls +0 macro_micro (866/868 kept), +1 xl_both (1,161/1,192); words, nodes, height unmoved (a span becomes an a). Code half +164 B link + 404 B list clause.

Follow-up, on the owner's call (Ruslan, 2026-10-01 12:31: "frankly speaking i like publish all option but maybe
there compromise like maybe we already all have all this data like in blast radius table and we can point user there
to traverse full list of dependencies as well as full list of dependents?"). The page held only counts and the
40-capped lists, so the route publishes the cheaper direction whole: `fan_in[uid].direct` loses its cap (the 40
earliest in graph order first, as before, then the rest, sorted; `GROWS: "elements"`; the card slices 40), not a new
field, which would repeat up to 40 names per element. The page inverts it into each row's undrawn `blocks` list, so
`depends_on:<uid>` (what <uid> blocks) and its mirror `blocks:<uid>` (what <uid> depends on) are exact, and both
cards' "+N more" link there. The not-applied sentence names drawn and stated columns only. The transitive clause
(`downstream:<uid>`, a closure over `blocks`) is dropped: its matcher alone measured +236 B page half.

## Outcome

The gap -> the close, at `7d0c5ddd` (UX-1206 landed), the 1,202-element page (`pages.two_plane_run --layers 20
--width 60`), Chromium 1440x900: toolchain.bst's 40 Blocks links ended in `span[data-more]` ", +1,160 more" (no
link), now `a[data-more]` "+1,160 more" to `#elements`, `f.elements = depends_on:toolchain.bst`; pressed from
Leaves it selects All elements; the href alone on a fresh load lands the same:

```text
depends_on:toolchain.bst @elements  25 of 1,202 | "depends_on:toolchain.bst": no column here is called "depends_on" ...
depends_on:toolchain.bst @elements        25 of 1,200 matched | Copy first 200 of 1,200 matched rows
depends_on:toolchain.bst @Leaves          25 of 149 matched
guard, big:  followed {tag: A, view: All elements, matched: 1200}; landed {matched: 1200, view: All elements}
guard, golden / macro_micro: the most-blocking uid's rows carrying it = dependent_count; 0 drawn depends_on cells
```

1,200 = `fan_in["toolchain.bst"].dependent_count`: the 40 listed and the 1,160 more. Volume at rest, the
architect's `measureA.py` on 7d0c5ddd -> this: macro_micro unmoved (height 39,141, words 13,068, controls 866,
nodes 6,858); walk controls 1,197 -> 1,198 (+1, the span became a link), height, words, nodes unmoved. Page half
on the walk run 157,181 -> 157,669 B (+488; with UX-1206, +900 over `ec816233`). The 32 test files naming
the four modules: 511 passed, 5 skipped, `test_the_page_has_a_volume_budget.py` among them.

| mutation | reddened | run printed |
|---|---|---|
| the span back (`element.js`, `true ?`) | `..._reach_every_element_it_counts[big]`, `..._blocks[big]`, `..._past_the_cap` | 3 failed, 7 passed |
| no `data-list-<key>` row attribute (`structured.js`) | `..._reach_every_element_it_counts[golden,macro_micro,big]` | 3 failed, 7 passed |
| no membership match in `matchesKey` (`tables.js`) | `..._reach_every_element_it_counts[big]` | 1 failed, 9 passed |
| a press keeps the reader's view (`element.js`) | `..._reach_every_element_it_counts[big]` | 1 failed, 9 passed |
| reverted | | 10 passed |

Follow-up gap -> close, `ffa8bcb1` -> the change, the guard's `wide_run` (layer01 elements name 51 each), 1440x900:

```text
published: layer00/mod049.bst dependent_count 50 | layer01/mod000.bst direct_count 51 len(direct) 40 -> 51
depends_on:layer00/mod049.bst    matched 0 -> 50; 'nosuch:x' sentence names Depends on/Blocks: True -> False
blocks:layer01/mod000.bst        matched -1 (no such column) -> 51; the sentence names Depends on/Blocks: False
layer00/mod049.bst dependents: {'text': '+10 more', 'view': 'All elements', 'matched': 0 -> 50}
layer01/mod000.bst direct: {'text': ', +11 more' -> '+11 more', 'href': None, 'view': 'Leaves' -> 'All elements', 'matched': -1 -> 51}
```

Cost, `view.export` page/data bytes ffa8bcb1 -> this: page half 157,667 -> 157,739 B (+72) on golden and
macro_micro, 157,669 -> 157,741 B on the 1,202 two-plane page and xl_both; data half +9 B golden, +9 macro_micro,
+89 the 1,202 page (20 names past 40, on one element), +717 xl_both (160). At rest unmoved: no card's Depends on passes
40 at rest on any page; macro_micro 38,965 px / 13,068 words / 866 controls / 6,858 nodes. 57 test files naming
the touched modules, the volume and data-half guards among them: 1059 passed, 3 skipped.

| mutation | reddened | run printed |
|---|---|---|
| `direct` capped at 40 again (`fan_in.py`) | `[wide]` | 1 failed, 2 passed |
| no inversion, `blocks: []` (`pairs.js`) | `[golden]`, `[macro_micro]`, `[wide]` | 3 failed |
| Depends on's rest filters `depends_on:` (`element.js`) | `[wide]` | 1 failed, 2 passed |
| the sentence lists undrawn columns (`structured.js`) | `[wide]` | 1 failed, 2 passed |
| the card shows the whole list (`element.js`) | `[wide]` | 1 failed, 2 passed |
| reverted | | 3 passed |

Deviation (follow-up, owner's call, 2026-10-01 12:31): the route and the dropped `downstream:<uid>` (+236 B) are
the Decision's last paragraph. Re-based: `test_what_an_element_pulls_in.py`'s cap class; the UX-1200 guard's `_line`
and past-the-cap clause read "+N more" for dependents (the link's text, ", " the list's separator), ", +N more" for direct.

Follow-up 2 close (walk N3-N5), the same reads as the Motivation's gap on this tree:

```text
name "+10 more: all 50 layer00/mod049.bst blocks, in Elements"; after Enter focus in the box
"depends_on:layer00/mod049.bst", Tab to the table's own tools (y 4,963); Back Leaves; Forward All elements, 50 matched
lead and title end "; depends_on:X lists every element X blocks, blocks:X every one X depends on"; the sentence "(..., depends_on:…, blocks:…)"
```

Page half +288 B (158,192 -> 158,480) on all three pages; at rest unmoved; 50 files naming the modules: 795 passed.

| mutation | reddened | run printed |
|---|---|---|
| popstate keeps a View the entry does not name (`app.js`) | `[wide]` | 1 failed, 2 passed |
| no focus after the filter (`element.js`) | `[wide]` | 1 failed, 2 passed |
| no `aria-label`; no key in the title; none in the sentence | `[wide]`, each run alone | 1 failed, 2 passed, each |
| the old lead (`pairs.js`) | `[golden]`, `[macro_micro]`, `[wide]` | 3 failed |
| reverted | | 3 passed |

Deviation (follow-up 2): N3 - Back restored a View the hash named (the walk's script fired a non-bubbling `change`,
so its hash had none); Forward did not. Popstate sets a View the entry does not name to the opening one, as it clears
a filter (a bare-hash navigation too); a `history.state` record goes stale. N4 - `filterSection` returns the box, the
link focuses it. N5 - the sentence names the keys, not the titles the follow-up kept out; lead and title share a string.
