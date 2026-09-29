# UX-1129: a union merge reopens swept bookkeeping lines

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-998 | **Found by:** round 149's bookkeeping ledger, promoted at round 152's sweep | **Serves:** every round's sweep | **Topic:** guards | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`.gitattributes` gives `docs/backlog/bookkeeping.md` `merge=union`, so
two branches that mark one line differently keep both copies after a
merge: the `open` copy and the `swept` copy. Round 149 reopened 12
lines across two merges that way:

```text
git log --merges -p -- docs/backlog/bookkeeping.md | grep -c '^+- r'
```

## Required Fix

`tools/dev_bookkeeping.py` reads a finding present both open and
resolved (same derived key) as resolved, and `--sweep` collapses the
pair to the resolved copy, so a union merge cannot reopen a line.

## Out of Scope

Dropping `merge=union`, which is what lets parallel filers append
without colliding.

## Acceptance Test

A ledger holding one key twice, `open` and `swept r152 ...`, lists
nothing under `--sweep`, and `--sweep --write` (or the tool's collapse
verb) leaves one line. Mutation: prefer the open copy; the test reddens.

## Outcome
