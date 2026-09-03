# UX-591: the architecture review log is in no index

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-241 (the review cadence), UX-583 (the round history guard) | **Serves:** the reader looking for what the last architecture review decided | **Topic:** docs

## Motivation

`docs/audits/architecture-review.md` is 45,132 B and thirteen reviews
long. `docs/README.md` has two tables that should carry it and does
not:

```text
docs/README.md:161-163   the audits table   case-study-06, optimization-walkthrough-04, planted-defect-walk-round-72
docs/README.md:201+      the round list     round-2 … round-83
git grep -l architecture-review -- docs/   scenarios/README.md, six task files, two round documents; docs/README.md: 0
```

`UX-583`'s guard reads the round history and the audits list against
`docs/audits/`, and passes: it enumerates round documents, and this
is not one. So the file every review appends to is reachable only
from the backlog index and from task files that happen to cite it.

## Required Fix

`docs/README.md`'s audits table carries every tracked
`docs/audits/*.md` that is not a round document, derived — `UX-583`'s
enumeration extended from "every round document has a row" to "every
audit document has a row, in the table its shape belongs to". The
row for the review log says what it records and that it is
append-only.

## Out of Scope

- The review cadence itself (`UX-241`) and its guard — this is the index.

## Acceptance Test

Mutation: remove the review log's row — red naming the file; add a
`docs/audits/` document with no row — red.
