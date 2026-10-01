# UX-1214: a card's +N more Blocks reach every element it counts

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-159 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_an_element_view_answers_whole.py` (`test_a_card_s_more_blocks_reach_every_element_it_counts`)

## Motivation

Page: the round-159 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `31b5971b`, Chromium 1440x900 and 390x844.

Walk P8 (pre-existing): the toolchain card's "Blocks:" lists 40 links then "+1,160 more" as a plain span; the rest is unreachable from the card.

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

## Outcome

The gap measured, at `7d0c5ddd` (UX-1206 landed), the 1,202-element two-plane page (`pages.two_plane_run
--layers 20 --width 60`), Chromium 1440x900: toolchain.bst's card ends its 40 Blocks links in
`span[data-more]` ", +1,160 more" (no link; `p[data-list] > span[data-more]` = 1 on the page), and the box
has no way to ask for the rest:

```text
depends_on:toolchain.bst @elements  25 of 1,202 | "depends_on:toolchain.bst": no column here is called "depends_on" ...
```

The close measured, same page: the rest is `a[data-more]` "+1,160 more" to `#elements` with `f.elements =
depends_on:toolchain.bst`; pressed from the Leaves view it selects All elements and filters; the href alone on a
fresh load lands the same:

```text
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

Re-based: `test_an_element_view_answers_whole.py`'s `_line` and the past-the-cap clause read "+N more" for
dependents (the link's text; the ", " is the list's separator now), ", +N more" still for direct.
