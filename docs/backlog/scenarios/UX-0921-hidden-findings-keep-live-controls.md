# UX-921: hidden findings keep live controls

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-413 (card populations open bounded) | **Found by:** round 130 design review | **Serves:** R1, R4 and assistive-technology users reading a report with many findings | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

`boundCards` caps the visible finding cards at 40, but hides complete cards
rather than detaching their contents. A direct render of findings carrying one
copy action each measured 1/1, 15/15, 40/40 and 121/120 controls/findings; at
120 findings, 80 buttons remain in hidden cards. The visible population is
bounded while the interactive DOM, tab/accessibility work and page budget keep
growing with the producer's findings array.

## Required Fix

Keep an addressable shell for every finding, but do not materialise interactive
descendants beyond the opening 40. Hydrate a requested shell when its fragment
is followed and hydrate the remainder when **Show all findings** is pressed.
The card order, count badge, copy text, Perfetto handoff and fragment identity
must remain unchanged.

## Decomposition

Input classes: findings at 1, 40 and 120; visible and hidden cards; copy,
description and investigation controls; direct fragment entry and Show all.
The journey extends reading the bounded findings list into opening one hidden
finding without paying for every hidden action first.

## Out of Scope

Changing which findings the analyzer publishes, lowering the visible-card
bound, or removing deep links to findings.

## Acceptance Test

Render 1, 40 and 120 findings with copy and investigation actions. Before
expansion, the last two documents contain the same number of interactive
descendants; following finding 100's fragment materialises that card and no
unrelated one. **Show all** materialises all 120 once, in source order, and
each action keeps its label and effect. Mutation: restore complete hidden
cards; the 40/120 control-count equality reddens.

## Outcome

**Gap measured** (round 130, `round-130.md`): a direct render of findings
carrying one copy action each drew 1/1, 15/15, 40/40 and 121/120
controls/findings - 80 buttons in hidden cards at 120 findings.

**Close measured**, same instrument
(`node --input-type=module`, `sections.renderFindings` under
`tests/dom_shim.mjs`, one copy button per finding): 1/1, 15/15, 40/40,
**40**/121 (was 121/121) and **40**/120 controls/findings - the population
past the opening 40 is a shell (`id`, `data-finding-id`,
`data-severity`, the title only) with a `_hydrate` closure, run once on
that finding's fragment or on Show all, in source order. Card order,
badge text, copy text and the Perfetto handoff are unchanged (existing
suites: `test_every_population_at_zero_one_and_many.py`,
`test_findings_carry_their_evidence.py`, `test_buttons_that_know_why.py`,
`test_the_report_you_can_attach.py` - all green).

**Mutation table**

| mutation | reddened | how |
|---|---|---|
| `if (index < bound) article._hydrate();` -> `article._hydrate();` (every card hydrates on render, `UX-413`'s old shape) | yes | `test_a_fold_bounds_its_interactive_descendants.py`: all 4 clauses error/red - `_hydrate` is cleared on first call, so a fragment or Show all follow throws rather than silently double-rendering |

Deviation: none from the Required Fix. The shell carries `id` and the title only (with `data-finding-id` and `data-severity`); it hydrates on a fragment follow and on Show all.
