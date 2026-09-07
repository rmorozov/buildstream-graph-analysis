# UX-762: the gate binds to a branch, not to the commit that is pushed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the loop), UX-522 (the selector hook) | **Serves:** the session whose gate passed on a commit it did not push | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md` calls `make test` **the gate** and *"required before
marking anything done"*. It does not say *on which commit*, and
nothing checks.

Round 104 broke it twice, in one round:

- the gate ran at `67cc0d1`; the round-document commit `4879bcc`
  followed, and CI reddened on two guards that read every round
  document — a `directions.md` history row and a `docs/README.md`
  link. The round-document commit is by construction the one most
  likely to trip document guards and the one that always follows the
  gate.
- earlier, `ff41d19` was pushed with no batch gate at all;
  `docs/audits/round-104.md:79-82` records it.

The hook that exists is deliberately narrower. `.claude/hooks/
selector_before_commit.py:13-16` says so itself — it runs the
*selector* on the staged tree, *"not `make test`"*. So the repository
has commit-time enforcement for the cheap gate and none for the real
one, and the gap is invisible until CI.

## Required Fix

State the binding: the gate covers **the commit you push**, not the
branch you ran it on. Then make it checkable — record which commit a
suite run covered (the junit already carries a run; the reference
already records shas) and red on a push whose head was never covered.
A `pre-push` hook is the obvious home; the repository has none today.

The cheap alternative, if the hook is too heavy: name the commits that
always follow a gate — the round document, the ledger, the closes —
and require the gate after them rather than before.

## Out of Scope

- Replacing the batch gate with a per-item one. `UX-500` measured
  that and the answer was no.
- The selector hook (`UX-522`) — its own docstring disclaims replacing
  `make test`, so it is not the gate this row is about and widening it
  to run the suite at every commit is a different, dearer change.

## Acceptance Test

A push whose head commit no suite run covered is refused, or the guide
states the ordering and a guard reads it. Mutation: commit a document
change after a green suite and confirm the check reds where round 104
was silent.

## Outcome

_Not started._
