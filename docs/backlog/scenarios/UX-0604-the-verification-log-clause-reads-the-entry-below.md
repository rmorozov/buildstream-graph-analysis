# UX-604: the verification-log clause reads the entry below it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-233 (the log), UX-582 (the same shape, found twice) | **Serves:** the round whose log entry says nothing and passes | **Topic:** guards

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
