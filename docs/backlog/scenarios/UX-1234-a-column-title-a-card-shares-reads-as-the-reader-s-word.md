# UX-1234: a column title the card shares reads as the reader's word

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-1226 | **Found by:** the round-161 verification of UX-1226 (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

UX-1226 derives each element card label from its column's title. On the 1,202-element page (`layer10/mod010.bst`) the card now reads "Probability 0.0%" where it read "On the path 0.0%", and "Element durations 3.5 s" (plural, one value) where it read "Duration". The verifier judged both worse for a reader; "Unweighted depth" and "Weighted duration" read as jargon beside "Depth" and "Blast radius". Owner, round 161: "Fix the poor titles" (decision card, 2026-10-01).

## Decomposition

Input classes: the 1,202-element two-plane page, its `--workload binaries` variant and macro_micro, at 1440 and 390.

## Required Fix

The columns the card shares that read worst take the reader's word, on table and card alike: the critical-path probability column reads "On the path", Element durations reads "Duration". The old titles stay accepted as filter words.

## Out of Scope

Columns no card shows; "Unweighted depth" and "Weighted duration" unless a one-word reader title is already in the repository's terms; the card fields with no column.

## Acceptance Test

`tests/unit/test_a_card_label_is_its_column_title.py` still holds; a guard reads that the card and the column say "On the path" and "Duration", and that `probability` and `durations` still filter. Mutation: restore the old title, and the guard reds.

## Decision

Session, round 161 (2026-10-01), on the owner's "Fix the poor titles":

```text
Route:     The two titles come from one place (format.js TERMS or the declared schema title that `title()` reads); set "On the path" and "Duration" there, so the column and the card move together, and keep "probability" and "durations" as filter words beside tables.js:71's aliases.
Rejected:  card-only overrides (UX-1226's one name per field breaks again); renaming every derived title (out of scope).
Files:     bga/viewer/format.js, bga/viewer/tables.js, tests/unit/test_a_shared_title_is_the_reader_s_word.py, and any test that pins the two old titles
Guard:     test_a_shared_title_is_the_reader_s_word.py: on the 1,202 page, the card and the column read "On the path" and "Duration"; `probability > 0` and `durations > 1` still filter.
Mutation:  Restore the old title for the probability column: red.
Class:     product
```
