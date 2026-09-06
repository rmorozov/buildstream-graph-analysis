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

**The decision, taken here: the first route.** `_landed_after` skips
a commit whose `DOC` blob equals one of its parents' — not "skip
merges", which would hide a conflict resolution that really did change
the document. The test is on the blob, so a merge that introduces no
claim of its own is not a landing and a merge that edits the log still
is. `closing_commit` keeps its oldest-match rule untouched, which
`UX-652` argued for and this row does not reopen; only the range
moves. The second route (anchor on the newest commit, close the
walk-forward hazard with a date check) is the fallback if the blob
comparison cannot be expressed against this history — say so in the
Outcome if you get there.

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

## Outcome

**Deviation.** The "decision, taken here" chose the blob comparison.
This pass measured it wrong against the merge the row exists for:
`2a0bf0f^1:DOC` = `b354827…`, `^2:DOC` = `1340b1b…`, `2a0bf0f:DOC` =
`dc38a08…` — the merge's blob equals **neither** parent, so `blob in
parent_blobs` calls it a landing, the exact commit this row exists to
stop calling one. It is not rare: master rewrites the derived-count
line on nearly every commit, so "master moved the count, track added
the entry" is a clean 3-way whose blob is in neither parent every
time. The combined diff replaces it: `git diff-tree --cc <sha> --
DOC`, empty when every line already matches a parent —
`git diff-tree --cc 2a0bf0f -- docs/design/architecture.md | wc -c` →
`41` (the sha line, no hunk). `_landed_after` keeps the default range;
`--full-history` is dropped — `2a0bf0f` reaches
`<anchor>..HEAD -- DOC` today (its blob is TREESAME to neither
parent), confirmed against this repository's own history with
`409fe54..2a0bf0f -- DOC` (`UX-713`'s own closing commit as anchor),
which lists `2a0bf0f`. `closing_commit` stays untouched.

**Gap, measured.** The blob-route code (this branch's prior commit)
against the new fixture (`2a0bf0f`'s shape: a real same-line conflict
resolved by keeping master's newer count *and* track's entry, so the
blob matches neither parent but every line matches one side):
`assert not stale(_landed_after(anchor))` →
`AssertionError: assert not True … stale(['a896570…'])`.

**Close, measured.** With the combined-diff check: `pytest
tests/unit/test_the_verification_log_is_true.py -q` → `30 passed`.
Three directions: no other side at all → `not stale([])`; the clean
recombination above (`--cc` empty) → `not stale([])`; the same
conflict resolved by writing a count in *neither* parent (`--cc` has a
hunk) → `stale(['<merge sha>'])`.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `merge_has_no_claim`: unconditional on parent count (drop the diff test) — the Acceptance Test's own mutation | `test_a_conflict_resolved_with_new_content_is_a_landing` | 1 failed, 29 passed |
| `_merge_has_no_claim`: reintroduce the blob comparison | `test_a_clean_recombination_is_not_a_landing` (`2a0bf0f`'s shape) | 1 failed, 29 passed |
