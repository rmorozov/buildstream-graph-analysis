# UX-604: the verification-log clause reads the entry below it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-233 (the log), UX-582 (the same shape, found twice) | **Serves:** the round whose log entry says nothing and passes | **Topic:** guards

## Motivation

`test_the_verification_log_is_true.py::test_the_entry_says_what_it_was_grounded_in`
takes a **fixed 1200-character window** from the newest entry's date
and searches the whole window. Measured by architecture review 14:

```text
window chars                                    1200
're-grounded in' offsets inside the window   [237, 1169]
entry length (to the next 'Updated ')        1045
```

Offset 1169 is the *previous* entry's sentence. Any newest entry
shorter than ~1186 characters is checked against its predecessor, so
the clause passes for an entry that says nothing. At the base tree the
same measurement is `[124, 837]` against an 800-character entry — the
defect predates this round and has never discriminated.

Removing the phrase from a new entry left the file **green (6 passed)**,
which is how it was found.

## Required Fix

The window is the entry, bounded by the next `Updated ` heading rather
than by a character count — the population is a section, not a slice.

## Out of Scope

- What the sentence has to say — declined: `UX-233` argued that and
  it holds; this item is only about which text is searched for it.

## Acceptance Test

Mutation: remove the phrase from the newest entry — red. Today that
mutation passes, which is this item's whole subject.

## Outcome (round 84, 2026-09-03) — 🟢 Done

**The gap, reproduced.** The Acceptance Test said the mutation *passes*
today, and it did. Removing the phrase from the newest entry only,
with the edit confirmed to have landed:

```text
$ sed -n '1037,1041p' docs/design/architecture.md
Updated 2026-09-03 (after `UX-569`), covering round 83's three changes
...
names in the reading order — checked against the two contract tables
$ grep -n "re-grounded in" docs/design/architecture.md | head -1
1056:re-grounded in the two contract tables above against `bga.contracts` — **23
$ pytest tests/unit/test_the_verification_log_is_true.py -q
6 passed in 0.05s
```

Line 1056 is inside the *next* entry (`Updated 2026-09-03 (after
`UX-549`)`, line 1054). The window ran 1200 characters from line 1037
and swallowed it.

**The close.** `_claimed()` bounds the entry at the next `Updated
YYYY-MM-DD (after `UX-N`)` heading rather than at a character count.
The same mutation now reds:

```text
FAILED ...::test_the_entry_says_what_it_was_grounded_in
1 failed, 5 passed
```

**Mutations verified red and reverted (2):**

| mutation | reddened | run |
|---|---|---|
| the phrase removed from the newest entry only | `test_the_entry_says_what_it_was_grounded_in` | 1 failed, 5 passed |
| `ends` back to `found.start() + 1200` | `test_the_window_is_the_entry_and_not_the_one_below` | 1 failed, 6 passed |

The second clause is new and exists because the first mutation is
about the *document*, not the guard: a later widening of the window
would restore the defect while every document-side mutation still
passed. It asserts the window holds exactly one entry heading.

**A guard of mine that did not discriminate:** none — but the one this
item fixes is worth naming as the reason the clause exists at all. It
had never discriminated, at any point in its life: measured at round
83's base the same window was 1200 characters against an 800-character
entry, so it read its predecessor there too.

**Deviation from the Required Fix:** none.

**Tier:** unchanged; the file runs 0.06s.

**Suite:** the batch gate runs at the end of the round.
