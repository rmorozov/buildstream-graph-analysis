# UX-764: two Register caps are guarded and two are honour-system

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-497 (the Outcome cap), UX-749 (which broke one) | **Serves:** the reader who trusts a cap because the guard reported green | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md`'s Register states four caps. `rules.md` says it is "every
rule on a page, with its guard". Two of the four have no guard, and
`tests/unit/test_the_register_is_terse.py` reports green either way —
which is the `UX-573` shape, in the file that polices the shape.

| cap | enforcement |
|---|---|
| module docstring ≤ 25 lines | guarded, but only for `tools/dev_*.py` and `.claude/hooks/*.py` (`test_the_register_is_terse.py:39-40,52-82`) |
| Outcome ≤ 80 lines | guarded — **length only** (`TestOutcomes::test_a_budgeted_outcome_fits`) |
| commit body ≤ 8 lines | guarded, and CI-enforced (`ci.yml:642`) |
| **code comment: one line of why** | **unguarded** — nothing reads code comments |

It has already been broken with the guard green. `UX-0749`'s own
Outcome records it: the verifier found a new constant's comment
running **six lines** against the one-line cap; it was *"trimmed to
two"* — still over — and the file reports
`test_the_register_is_terse.py` green, because that guard never reads
that surface.

The Outcome cap has the matching hole on the other axis: its
*content* is unguarded. `CLAUDE.md` says an Outcome carries "the gap
measured, the close measured, the mutation table, the deviation", and
only the line count is checked. `docs/audits/round-94.md:20` measured
the consequence — **55 of 60** closed tasks carried a mutation table,
so five closed without one and nothing reddened.

## Required Fix

1. Decide the code-comment cap honestly: guard it, or state the rule
   as the convention it actually is. A cap that reports green while
   being broken is worse than a cap stated as guidance — this
   repository files rows about exactly that.
2. Guard the Outcome's **content**, not just its length: a closed row
   whose Outcome names no mutation table is the defect
   `round-94.md` counted.
3. `rules.md` claims to carry every rule with its guard. Where the
   guard is a convention, say so in the row rather than leaving the
   column to imply one exists.

## Out of Scope

- The caps' values. `UX-497` set the Outcome budget and `UX-652` the
  commit body; this row is about which are enforced, not how big.
- Widening the docstring guard beyond `tools/` and the hooks. Its
  narrowness is deliberate — "older ones only shrink".

## Acceptance Test

Every Register row states its enforcement truthfully, and a closed
Outcome with no mutation table reds. Mutation: strip the mutation
table from a round-104 Outcome and confirm the new clause names it,
where today the suite is green.

## Outcome

_Not started._
