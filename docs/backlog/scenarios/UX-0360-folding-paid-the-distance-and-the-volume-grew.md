# UX-360: folding paid the distance, and the volume grew by a third

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-347 (the distance budget), UX-346 (the schema's sentence on the door) | **Serves:** anyone who opens more than the first chapter | **Topic:** viewer

## Motivation

Round 52's complaint was distance: twenty screens, the element table
6.8 screens down, the run identity 19.6. `UX-347` answered it with
chapters that fold, and the answer worked. Round 55, measured on the
page an export actually produces:

```text
                    round 52      round 55 landed / opened
golden height      11,286 px       3,548 / 13,844
macro  height      18,148 px       5,588 / 24,689
golden sections           28            43
macro  sections           37            58
golden words           3,448         5,034
macro  words           5,026         8,174
golden buttons           195           257
macro  buttons           274           381
```

**The page a reader lands on is a third of what it was (−69%). The
page in total is a third bigger (+23% on `golden`, +36% on
`macro_micro`).** Distance was paid for with a fold, and the volume
behind the fold went unmeasured and grew — because nothing measures
it. `UX-347` bought a distance budget; there is no volume budget, and
"it is behind a chapter" is currently a complete answer to any
question about page weight.

The growth is not waste, and this item does not claim it is. Round 53
and 54 built the shape channel (`UX-350`: 0 strips → 5 and 15),
narrowed the table tools (`UX-349`: 81 inputs → 18), moved the
schema's sentences behind a door (`UX-346`), and lifted two
namespaces (`UX-344`: 28 sections → 43, because grouping was removed
on purpose). Each was right. Together they are a third more page, and
the round that adds the next thing has no number to check it against.

The reference the user keeps returning to is Apple's, and its version
of this rule is not "make it smaller" — it is that the default state
is a complete answer and everything else is opt-in. The landed page
*is* a complete answer: 3,548 px, one chapter, verdict, three ranked
elements, a runnable command. That property is what a volume budget
exists to protect: without one, the next four rounds put their weight
behind the fold and the landed page slowly stops being the whole
answer.

## Required Fix

Styleguide §3e, the sibling of §3c:

- **Two budgets, both bound, both measured on the exported page**:
  landed distance (§3c, unchanged) and total volume — words, controls
  and height with every chapter open.
- **A fold is not a licence.** A change that moves weight behind a
  chapter answers the distance budget and says nothing about the
  volume one.
- **The bound is set against a measured page and moves only with a
  filed reason.** Round 55's measurement is the baseline; the numbers
  above are what it is set from.

Set the initial bound with headroom rather than at today's value — a
budget that reddens on the commit that lands it teaches the next
person to raise it.

## Out of Scope

- Reducing the volume. This item asks for the *measurement*; the
  reductions have their own items (`UX-356` and `UX-361` both change
  it, in opposite directions).
- The landed-state distance budget, which `UX-347` set and which is
  being met.
- The `?` door count (121 of `golden`'s 257 buttons). It is §6a's
  deference question, and this item deliberately only *measures* it:
  bounding the doors is a change to `UX-346`'s mechanism and belongs
  with that argument, not inside a budget.

## Acceptance Test

A guard that boots both fixtures, opens every chapter, and asserts
words, controls and height against a stated bound — with the landed
figures asserted in the same guard, so the two budgets are visibly a
pair and a change that trades one for the other has to say so.

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured

```text
                    round 52      round 55 landed / opened
golden height      11,286 px       3,548 / 13,844
macro  height      18,148 px       5,588 / 24,689
```

The landed page was a third of what it was; the whole page was a third
bigger. Nothing measured the second half, so "it is behind a chapter"
was a complete answer to any question about page weight.

### After

Measured on the **finished** page — this item ran last, after `UX-355`,
`UX-356`, `UX-357` and `UX-361` all moved the number:

```text
                landed   opened    words   controls
golden           3,501   14,493    5,279        409
macro_micro      5,564   28,213    9,879        659
budget           7,000   34,000   12,000        800
```

The budgets are set from that with roughly a fifth of headroom on the
larger fixture, in `tests/unit/test_the_page_has_a_volume_budget.py`
and restated in §3e.

### One guard, two budgets

They are asserted in the same class on purpose. `UX-347`'s distance
budget is met and lives elsewhere; this holds it *beside* the volume it
was paid for with, so a change that folds more in order to grow more
reddens rather than passing two guards separately. That is exactly what
happened for four rounds and nobody noticed.

Two clauses keep the pair honest rather than decorative:

- **`test_the_page_still_folds`** — without it the landed clause is
  satisfied by a page that renders nothing, and the trade stops being a
  trade.
- **`test_the_budgets_are_not_slack`** — the larger fixture must sit
  within a factor of two of every bound. A bound nothing can reach is
  not a bound, and setting one is the easiest way to write a guard that
  never fires.

### Words and controls are one number, not two

The chapters hide their sections with CSS, so `textContent` reads every
word whether the fold is open or shut: 5,279 words on `golden` landed
*and* opened. That is the mechanism rather than a simplification, and
it is the sharpest statement of the finding — **the volume is in the
document from the first byte, and folding changed only how far a reader
scrolls past it.**

### What this replaces

Round 56 restated the export's size bounds three times, once per item
that added to the page:

```text
page      244,088 -> 249,694 -> 260,369 B
golden    329,444 -> 335,050 -> 346,521 B
macro     369,740 -> 375,346 -> 386,817 B
ratio       2.860x ->  2.748x (bound 2.8 -> 2.6)
```

Each restatement carried its measurement and its reason, which is the
repository's convention and is why they were legitimate. Three in one
round is also the signal that byte counts were standing in for a
budget nobody had. The note in
`test_the_report_you_can_attach.py` says so at the ratio, and points
here.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `5040c6e`.

| # | mutation | reddened |
|---|---|---|
| U1 | every chapter opens on load — the page stops folding | 4, including both `test_the_page_still_folds` |
| U2 | 900 filler controls appended at boot | 4, both budgets on both fixtures |
| U3 | §3e states a bound the guard does not | 1: `test_the_style_guide_states_both_budgets` |
| U4 | a bound raised to 120,000 px, far past anything reachable | 2: the slack clause, and the guide clause it now disagrees with |

U4 is the one that makes this a budget rather than a record. The
failure mode of a number written down after a measurement is that the
next round raises it instead of arguing with it, and the slack clause
is what stops the raise being silent.

### Deviation from the Required Fix

- The Required Fix asked for "words, controls and height with every
  chapter open". Height is measured both ways; words and controls are
  measured **once**, because the fold does not change them —
  documented above and in §3e rather than measured twice to look
  symmetrical.
- The Required Fix said "set the initial bound with headroom rather
  than at today's value". Done, with the addition it did not ask for:
  the headroom is itself bounded, by `test_the_budgets_are_not_slack`.
  A budget with unbounded headroom is a comment.
- The Out of Scope entry stands: nothing here reduces the volume. The
  measurement was the ask, and reducing it is the next round's
  argument — with, for the first time, a number to make it against.
