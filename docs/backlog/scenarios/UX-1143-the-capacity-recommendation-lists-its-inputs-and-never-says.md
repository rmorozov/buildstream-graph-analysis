# UX-1143: the capacity recommendation lists its inputs and never says what to set

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings H4 | **Serves:** R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_capacity_section_opens_with_its_answer.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §H4).

`#capacity_recommendation` shows four inputs, a two-row constraints table and "Binding constraint CPU / Recommended builders 4 / Builders change 0", and no sentence saying keep 4 builders. "CPU binds" sits beside "0.51 of 4 cores busy", which reads as a contradiction; the clamp from 31 is explained only in the finding title. The finding repeats the section's nine facts.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

The section opens with the verdict in reader terms (what to set, and why the binding constraint binds, including the clamp); the table is the evidence under it; the finding links to the section rather than repeating its evidence.

## Decision

- `compute_capacity_recommendation` publishes `verdict`, one sentence: what to set (keep/raise/lower to N), which constraint binds and why - the clamp named as a cap on builders, not load - and the other ceilings. Additive under `analyze/v6`, declared in `bga/schemas.py`.
- A new hint `bga:lead` on the section names that member; `renderPairs` draws it first as `p.section-lead` and not as a pair (schema_hints.py, format.js, styleguide §1a row).
- The finding's title is `Capacity: <verdict>`, so the text report and the page say one thing; the finding publishes `section: "capacity_recommendation"` (additive, declared on `findings.items`), and a card with `section` draws a link to it in place of its detail and evidence. The JSON evidence stays: it is the carrier `copy_text` and the provenance guard read.
- Guard: `tests/unit/test_the_capacity_section_opens_with_its_answer.py`, Chromium on the two-plane page at 1440 and 390, plus the unit sentence cases. Mutations: drop `section` from the finding (the card repeats the evidence, red); stop drawing the lead (red).

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: the section's first block is a sentence naming the recommended builder count, and the finding's evidence holds no key the section already draws, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

**Gap measured.** The two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`, `capture report --json`, `bga_view --export`), Chromium, the guard's read:

```text
width  first block after the heading  card dt repeating a section term  card detail lines  link
1440   DL.pairs                        7                                 3                  none
390    DL.pairs                        7                                 3                  none
```

**Close measured.** Same page and read after the fix:

```text
1440   P.section-lead                  0                                 0                  #capacity_recommendation
390    P.section-lead                  0                                 0                  #capacity_recommendation
```

Lead: "Keep 4 builders: each building element drew 0.13 cores, so the CPU alone could feed 31, but builders are capped at the host's 4 cores - that cap, not load, binds; the graph allows 8." `macro_micro` reads "Lower builders from 4 to 2: the graph binds - the sweep's knee is at 2 builders; the CPU allows 4, the memory allows 9." The text report prints the same sentence as the finding's first detail line; the finding's JSON evidence is unchanged (the carrier `copy_text` and the provenance guard read).

**Mutation table.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_the_capacity_section_opens_with_its_answer.py`, 14 tests (two-plane and `macro_micro` at 1440 and 390, every fixture's section links, three sentence cases):

| mutation | reddened | count |
|---|---|---|
| finding publishes no `section` (the old card) | `test_the_finding_links_instead_of_repeating` x4 ("repeats the section's ['Binding constraint', 'Builders', ... 'Recommended builders']"), `test_the_text_report_leads_with_the_same_sentence` | 5 failed, 9 passed |
| `renderPairs` does not draw the lead | `test_the_section_opens_with_a_sentence_naming_the_count` x4 | 4 failed, 10 passed |
| clamp not told (`clamped_from = None` in the sentence) | `test_the_clamp_is_told_in_the_sentence` | 1 failed |
| reverted from the copies | - | 14 passed |

Merged-tree fix: styleguide 1a hint count 21 -> 22 for the new `bga:lead` row (`test_the_hint_count_is_the_documented_table`).
