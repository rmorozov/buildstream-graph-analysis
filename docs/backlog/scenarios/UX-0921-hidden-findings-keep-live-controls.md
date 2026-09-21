# UX-921: hidden findings keep live controls

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-413 (card populations open bounded) | **Found by:** round 130 design review | **Serves:** R1, R4 and assistive-technology users reading a report with many findings | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

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

Not started. The measurements are in
[`round-130.md`](../../audits/round-130.md).
