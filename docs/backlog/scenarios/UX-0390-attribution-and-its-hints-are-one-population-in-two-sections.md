# UX-390: attribution and its hints are one population in two sections

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-288 (a population is published once), UX-351 (the label prints the unit the value carries), UX-286 (the report has chapters) | **Serves:** anyone reading where a build's time went | **Topic:** viewer

## Motivation

The user asked whether `attribution` and `attribution_hints` could be
one section. Measured on the round 63 capture, they are one
population already — the key sets are identical:

```text
attribution        execution_on_chain_us dependency_wait_us resource_wait_us
                   scheduler_wait_us idle_us retry_wait_us
                   untracked_head_us untracked_tail_us
attribution_hints  (the same eight)
SAME KEY SET       True
```

Eight buckets, two `<h2>` sections, each carrying a different sentence
about the same field. The reader meets a number in one chapter and its
explanation in another, and nothing in either says they are the same
eight things — which is `UX-288`'s one-population rule at section
level rather than at payload level.

The hints half also renders its keys raw, unit suffix and all:

```text
Execution on chain us
Dependency wait us
Untracked head us
```

`UX-351` established that a label does not print the unit the value
already carries, and `UX-374` that the page does not show the reader a
key it invented. The hints section predates both and was never swept.

## Required Fix

One section. The bucket is the row; its measured value and its
sentence are two columns of that row, not two chapters.

- **Merge into a single attribution section**, keyed by bucket, so the
  number and the sentence that explains it arrive together.
- **The hint is a property of the bucket**, published once —
  whichever payload key survives, the other is not a second population
  of the same eight names.
- **Labels go through the page's own label rule**, so
  `execution_on_chain_us` reads "Execution on chain" with the unit on
  the value, not "Execution on chain us".

## Falsification

A guard that asserts no two rendered sections draw the same key set
from the payload, and that no rendered label ends in a unit suffix the
value already carries (`_us`, `_bytes`, `_s`). Today the first fails
on this pair and the second fails on eight labels.

The other direction: merging must not lose a sentence. Every hint
present before the merge is reachable after it — the count of
explained buckets does not drop, which is the property that would make
"merge" mean "delete the hints".

## Out of Scope

- The wording of the eight sentences. `UX-220` set the rule that a
  number needing a sentence has one; this item moves them, it does not
  rewrite them.
- Whether the eight buckets are the right decomposition. That is an
  analysis question and untouched here.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

Driven in Chrome on the exported `macro_micro` page, before:

```text
attribution        8 <dt>   Execution on chain?  43.2 s  ...
attribution_hints  8 <dt>   Execution on chain us   real work on the
                            critical path - the only way to reduce this
                            is to reduce the work itself
```

Two `<h2>` sections over the same eight bucket names, and eight labels
printing the unit their value already carries.

### After

```text
attribution        8 <dt>   Execution on chain?  43.2 s
                            Time the chain's own elements spent
                            executing - the part of the makespan that
                            is work rather than waiting.
                            real work on the critical path - the only
                            way to reduce this is to reduce the work
                            itself
attribution_hints  no section
```

One section, both sentences on the bucket's own row, and no label ends
in a unit suffix.

### Two sentences, and only one of them is a contract

The schema's `description` says what a bucket **is** and travels with
the contract. The hint says what to do about it **on this run** —
`resource_wait_us`'s names whether *this run's* capacity checks could
run at all, which no contract sentence could say. So the hint cannot
become a description, and `bga:explained_by` is what lets the page draw
both on one row without sniffing for a key named `<something>_hints`
(`UX-201`).

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| C1 | drop `bga:explained_by` from the `attribution` node | 3 of 7, incl. `test_the_contract_says_where_the_advice_lives` and `test_no_hint_was_lost_in_the_merge` |
| C2 | remove `attribution_hints` from `DRAWN_ELSEWHERE` (two sections again) | 1 of 7: `test_the_hints_have_no_section_of_their_own` |
| C3 | render the advice as one block at the foot of the section rather than per row | 2 of 7, incl. `test_the_advice_is_on_the_row_of_its_bucket` |

### A guard of my own that did not discriminate

`test_the_advice_is_on_the_row_of_its_bucket` first compared two
*counts* - eight labels against eight `p.run-advice` paragraphs - and
C3 left it green: eight sentences collected at the foot of the section
give the same two counts, and that is the two-section defect at half
the distance. The probe now walks `<dt>`/`<dd>` pairs and matches each
bucket's sentence to the hint the payload publishes for it, and C3
reddens two clauses.

### Deviation from the Required Fix

- **Both payload keys stay published.** The Required Fix says "whichever
  payload key survives, the other is not a second population of the same
  eight names". Removing `attribution_hints` from `analyze/v4` is a key
  *removal*, which bumps the contract version under `UX-190` — a version
  bump for a rendering merge is out of proportion, and the filing does
  not ask for one. What the contract gains instead is the statement that
  one explains the other, so they are no longer two unrelated
  populations: `bga:explained_by` is a declaration a consumer can read,
  and the page draws one section.
- **The label fix came for free** rather than being a second change.
  Once the row's label comes from the map whose members declare
  `duration_us`, `UX-351`'s rule applies to it; the hints map's keys are
  never rendered as labels again.
- **Three existing numbers moved, each with its measurement.**
  `test_the_label_is_for_the_reader.py`'s floor of labelled terms goes
  200 → 190, because eight labels left the page by merging (the guard is
  there to catch the trim rule *silently dropping* terms, and 190 still
  catches that). `PAGE_BUDGET_B` goes 274,000 → 276,000, +954 B all
  source — the first rise since `UX-360` that buys a page which is
  *smaller* to read. And the data-dwarfs-the-page ratio goes 2.5 → 2.4,
  which is the procedure its own comment sets out: the largest round
  number the claim carries against the permitted page, measured at
  686,497 B against 2.4 × 276,000 with 24,097 B to spare. `UX-367`'s
  clause holds the two from becoming two ceilings again, so its copy of
  the constant moved with it.
