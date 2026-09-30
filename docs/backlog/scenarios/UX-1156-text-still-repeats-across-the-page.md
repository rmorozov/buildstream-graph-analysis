# UX-1156: text still repeats across the page

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-154 walk, items 4 and 11, and the verifier's `#capacity_verdict` read (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_each_sentence_is_drawn_once.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

The Shared-source sentence is drawn in 11 places; the element card's "Dominant binary" and "Ran one process at a time" list the same values; `#utilisation` says "6 rows" five times; `#confidence`'s gates table has a "Name" header over sentences and "Ordering violations 0" repeats its first gate; "Highest-criticality elements" and "Elements most worth optimizing first" are titles over list bodies; `plane2_coverage`'s "Process count", "Wall span" and "Peak processes" restate its lead (`test_no_key_is_terminal_only_in_silence` requires them drawn); `#capacity_verdict` reads "Skipped inputs none" under a sentence saying both checks ran.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- A finding off its own card is **named and linked** (`findingLink`, `format.js`): its title to the colon, in the element card's one `Findings:` line and the decision's Why lines. A title over a list body reads as the list's name.
- The decision's ranking rule is **linked** to its `#provenance` block, which draws it; an evidence block whose every row an earlier block says becomes a clause on that block's label (`Dominant binary, ran one process at a time`).
- A `SECTION_ANSWERS` lead declares the members it read (`data-said`, a read-tracking proxy) and those pairs leave; a producer lead drops its empty lists as it drops its booleans (`Skipped inputs none`). `test_no_key_is_terminal_only_in_silence` reads `data-said` as drawn.
- The `#blast` export drops the step's reason, the findings card a detail line `attribution` draws as advice, the Perfetto library its requirement's second statement; a strip's label names its column, not the count.
- Guard: `tests/unit/test_each_sentence_is_drawn_once.py` on `golden`, `macro_micro`, two-plane. Mutation: restore the element card's full finding title.
- Not taken: the table badge beside `Copy N rows`, `#confidence`'s gates header and `Ordering violations` (page-byte budget).

## Required Fix

Each sentence is drawn once; a pair that restates a lead leaves the page and the guard that required it is re-read.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

On the two-plane page no sentence of 8 or more words appears twice and no pair restates its section's lead. Mutation: restore the defect, and the new guard reds.

## Outcome

### Gap measured

`tests/unit/test_each_sentence_is_drawn_once.py`'s census run against the base tree (`54d61bb9`, `git archive`), every chapter and fold open:

```text
             sentences>=8w  said twice  copies  lead-restated pairs
golden             164          10         24       0
macro_micro        271          11         30       0
two_plane          242           8         23      13  (11 an answer reads: Process count, Peak processes
                                                          at once, Wall span, Opens covered processes, Joined /
                                                          Plane 1 / Plane 2 elements, Epsilon, Total CPU, Measured /
                                                          Unmeasured processes; + Skipped inputs, Pinned elements none)
two_plane    Shared source x10 (7 cards, decision, finding); decision rule = #provenance block;
             #blast reason = next step 1; wait-category detail = attribution advice; Perfetto
             requirement x3; Dominant binary = Ran one process at a time on 19 cards
```

### Close measured

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_each_sentence_is_drawn_once.py -q
18 passed
             sentences>=8w  said twice  copies  lead-restated  data-said keys
golden             148           0          0          0             0
macro_micro        253           0          0          0            11
two_plane          229           0          0          0            13
                    base      after
golden page bytes   149,151   149,547   (+396; 453 of 150,000 left)
xl_both opened      43,469 px 42,715 px (-754), words 12,844 -> 12,331, nodes 7,310 -> 7,063, controls 873 -> 886 (of 900)
golden opened       19,599 px 18,972 px, words 8,025 -> 7,667;  macro_micro 37,808 -> 36,722 px
```

The 103 test files naming the touched modules, single process: 1841 passed, 39 skipped.

Guards re-read, claims kept: `test_no_key_is_terminal_only_in_silence` counts a lead's `data-said` members as drawn - the lead states them, so `process_count`/`max_concurrency`/`wall_span_us` are drawn there, not as pairs; `test_why_is_this_ranked_first` reads the list's rule through its link to the `#provenance` block (the sentence that block draws is `test_the_provenance_names_its_rule`'s), which is the claim's own "reachable, not positioned".

### Mutations verified red and reverted (12)

| # | mutation | reddened |
|---|---|---|
| M1 | `findingLink` names the full title | link-is-a-name clause, 3 failed |
| M1b | element card prints each finding's title | sentence clause, 3 failed |
| M2 | answer reads nothing (`dropped = []`) | census-reads clause (`data-said` keys 0), 1 failed |
| M2b | `data-said` kept, pairs not removed | lead clause, 2 failed |
| M3 | empty list kept under a producer lead | lead clause, 1 failed |
| M4 | Perfetto requirement in full every time | sentence clause, 3 failed |
| M5 | no `advised` filter on the card | sentence clause, 3 failed |
| M6 | `#blast` step reason restored | sentence clause, 3 failed |
| M7 | evidence blocks never merged | evidence clause, 1 failed |
| M8 | strip label `across all N rows` | strip clause, 3 failed |
| M9 | decision draws the rule fold again | sentence clause, 3 failed |
| M10 | census ignores `data-said` | `test_every_carried_member_is_drawn_where_it_landed`, 1 failed |
