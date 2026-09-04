# UX-627: closing a row writes `🟢 Done Open`

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-454 (the defect this reproduces), UX-336 (the helper) | **Found by:** architecture review 15 | **Serves:** anyone reading a task file's status | **Topic:** guards

## Motivation

`STATUS_WORDS` names four words. The tree uses five: `🔴 Open` entered
it on 2026-09-03 and is what every row filed since is written with.
`close_status_line` matches the glyph plus *known* words, so against
`🔴 Open` it consumes the glyph alone and leaves the word standing:

```text
in : **Status:** 🔴 Open | **Priority:** Low
out: **Status:** 🟢 Done Open | **Priority:** Low
status_words(out): ['Done']
STATUS_WORDS: ('Not Started', 'In Progress', 'Fixed & Verified', 'Done')
```

The census of the tree:

```text
556  **Status:** 🟢 Done
 55  **Status:** 🟢 Fixed & Verified
 17  **Status:** 🟢 Done Open      ← 16 of them closed this window
  6  **Status:** 🔴 Open           ← every one mangles on close
  2  **Status:** 🟢 Done Done      ← UX-454's original, still present
```

`dev_close_task.py --check` reports `0 problem(s) over 5 propert(y/ies),
624 backlog row(s)` throughout, because `status_words()` returns
`['Done']` — it reads the words it knows, and `Open` is not one, so
the guard cannot see the text it is looking at.

This is `UX-454`'s "Done Done" defect **reproduced by the fix for it**.
That fix's own docstring says the pattern it replaced "named only the
two *open* words, so against an already-closed line it matched the
glyph alone and left the old word standing - twenty-five files". The
replacement names only the words that existed in 2026-08; a fifth
arrived and the same sentence is true again.

The guard against it, `test_closing_a_task_twice_says_done_once`,
enumerates five literal status lines. None of them is `🔴 Open` — the
form six open rows carry right now — so it is green on a tree it does
not describe.

## Required Fix

Both halves, or the third occurrence is a matter of time.

1. The word list covers what the tree holds, and the seventeen files
   already written are repaired.
2. The guard's cases are **derived from the forms the tree actually
   carries** rather than enumerated, so the next new word reddens it
   instead of walking past. That is `UX-606`'s technique — a
   distribution over the population, not a sample — applied here.

## Out of Scope

- The status vocabulary itself: whether `Open` and `Not Started` should
  both exist is a separate question, and this fix must not decide it by
  deleting one.
- `UX-622`'s population question, in the same file this round.

## Acceptance Test

`close_status_line` over every distinct `**Status:**` form in the tree,
each closing to exactly one word, with the guard reddening when a form
is added to the tree and not to the helper.
