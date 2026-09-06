# UX-732: the verification log's anchor cannot survive a merge

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-652 (which made the anchor a commit), UX-604, UX-247 | **Serves:** every round that runs a track touching the architecture document | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

`test_nothing_landed_after_the_commit_the_entry_credits` anchors on
`closing_commit(item)`, which is deliberately the **oldest** subject
naming the id:

```python
    The **oldest** match, not the newest: a later commit naming the id
    again would walk the anchor forward and switch the clause that uses
    it off without failing anything.
```

That is right for a linear round and unsatisfiable for a track. The
track writes the entry as its last commit and is green on its own
branch; the session then merges, and the merge commit touches the
document:

```text
FAILED …::test_nothing_landed_after_the_commit_the_entry_credits
E    +  where True = stale(['2a0bf0f…'])
$ git log --oneline -1 2a0bf0f
2a0bf0f UX-713/714/715: merge the three documentation figures
```

The merge is correctly **not** a closing commit — `closing_commit`'s
own docstring excludes a subject where two items met — so the anchor
stays at the track's commit and the merge is forever "landed after".
No commit ordering fixes it: the entry cannot credit an item whose
oldest commit is younger than the merge that brought it in.

Round 98 hit this on its first track merge and resolved the tree by
filing this row and re-grounding the log in **this** commit, whose id
has exactly one commit and that commit is the newest touch. That is a
workaround, not a rule: it costs a backlog id per merge.

## Required Fix

The anchor's definition widens, or the range does. Two candidates:

- **A merge is not a landing.** `_landed_after` skips a commit with
  more than one parent whose `DOC` content is reachable from its
  parents — the merge introduces no claim of its own. A conflict
  resolution that *does* change the document is a real landing and
  must still count, so the test is on the blob, not on the parent
  count.
- **The anchor is the item's newest commit, with the walk-forward
  hazard closed another way** — for instance by requiring the entry's
  date to match the anchor's, so an unrelated later commit naming the
  id cannot silently move it.

The first keeps `closing_commit` pure and touches only the range. Say
which, and why, in the Outcome.

## Out of Scope

- `closing_commit`'s oldest-match rule itself, if the first route is
  taken. It is correct for what it does and `UX-652` argued it.
- The merge strategy. Squashing tracks would hide the trap rather than
  fix it, and `UX-510` settled that a track's commits are its record.

## Acceptance Test

A track commit that writes the entry, merged with `--no-ff`, leaves
the guard green; a merge that resolves a conflict *inside* the log
leaves it red. Mutation: make the skip unconditional on parent count —
the conflict case goes green and the guard reds.
