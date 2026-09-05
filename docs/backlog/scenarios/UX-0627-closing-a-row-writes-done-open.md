# UX-627: closing a row writes `🟢 Done Open`

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-454 (the defect this reproduces), UX-336 (the helper) | **Found by:** architecture review 15 | **Serves:** anyone reading a task file's status | **Topic:** guards | **Area:** tools

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

## Outcome (round 85, 2026-09-04) — 🔴 Open

**Premise:** held, and **wider than filed**. Re-measured on `695455d`.

### The gap, measured

`close_status_line` over the tree's forms, before:

```text
'🔴 Open | ...'          -> '🟢 Done Open | ...'          words=['Done']
'⚪ Blocked / Deferred'  -> '🟢 Done Blocked / Deferred'  words=['Done']
'🟢 Done Open | ...'     -> '🟢 Done Open | ...'          (not repaired)
```

Not only `Open`: **any** word outside `STATUS_WORDS` survives, and
`⚪ Blocked / Deferred` mangles the same way. `--check` stayed clean —
`status_words()` parses with the vocabulary under test, so the word it
cannot name is the word it cannot see.

Two corrections to the filing's census, which counted every
`**Status:**` string rather than header lines:

```text
filed  17 🟢 Done Open, 2 🟢 Done Done, 6 🔴 Open   (19 to repair)
header 17 🟢 Done Open, 0 🟢 Done Done, 12 🔴 Open  (17 to repair)
```

The two `Done Done` are `UX-454`'s quoted evidence (lines 109, 143) and
the nine `Done.` are trailing markers deep in eight 2026-06 files.
**17** files repaired, not 19.

### After

```text
distinct forms in the tree: 6
  '⚪ Blocked'            -> '🟢 Done'   idempotent=True
  '⚪ Blocked / Deferred' -> '🟢 Done'   idempotent=True
  '🔴 Not Started'        -> '🟢 Done'   idempotent=True
  '🔴 Open'               -> '🟢 Done'   idempotent=True
  '🟢 Done'               -> '🟢 Done'   idempotent=True
  '🟢 Fixed & Verified'   -> '🟢 Done'   idempotent=True
$ python tools/dev_close_task.py --check
0 problem(s) over 5 propert(y/ies), 630 backlog row(s)   exit=0
```

Second half, a form the helper does not name (`🔴 Reopened`, planted
then removed): both guards red, `2 failed, 6 passed`.

The word list is the tree's whole vocabulary, the alternation is built
longest-first, and the guard derives its cases from `file_statuses()`.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| N1 | `STATUS_WORDS` back to the original four | tree guard + 3 closing cases, 4 failed 6 passed |
| N2 | only `"Open"` dropped (the filed defect) | closing `('🔴','Open')` → `'Done Open'` + tree guard, 2 failed 8 passed |
| N3 | alternation sorted shortest-first | closing `('⚪','Blocked / Deferred')` → `'Done / Deferred'`, 2 failed 8 passed |
| N4 | one repaired file put back to `🟢 Done Open` | **tree guard alone**, 1 failed 10 passed |
| N5 | population narrowed to `🟢` forms | **non-vacuity alone**, 1 failed 5 passed |

Why a sixth literal would not have worked: under `N2` the old clause's
two assertions both **pass** for `🔴 Open` — closing it is already
idempotent and `status_words('🟢 Done Open')` is already `['Done']`.
Only reading the closed *text* discriminates, which is the proxy shape
(§5) and why this is the second occurrence.

`test_no_task_file_repeats_its_status_word` co-reddens under `N1`–`N3`:
vocabulary-covers-tree and tree-is-clean are one condition while the
tree is clean. `N4` is what it discriminates on.

### Deviation from the Required Fix

None. The vocabulary question stayed out of scope; no row moved and no
other status flipped — the sweep is 17 lines, one per file.

```text
$ make lint            All checks passed!
$ make test-touching   35 file(s) selected · 1146 passed, 3 skipped
```
