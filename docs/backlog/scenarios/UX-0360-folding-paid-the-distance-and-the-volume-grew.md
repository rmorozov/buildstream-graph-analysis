# UX-360: folding paid the distance, and the volume grew by a third

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-347 (the distance budget), UX-346 (the schema's sentence on the door) | **Serves:** anyone who opens more than the first chapter | **Topic:** viewer

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
