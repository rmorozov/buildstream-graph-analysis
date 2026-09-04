# UX-591: the architecture review log is in no index

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-241 (the review cadence), UX-583 (the round history guard) | **Serves:** the reader looking for what the last architecture review decided | **Topic:** docs

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

## Outcome

**Round 84**, 2026-09-03. The row, and the enumeration that keeps it.

### The gap, measured

```text
$ grep -c architecture-review docs/README.md
0
$ git ls-files 'docs/audits/*.md' | grep -vc 'round-[0-9]'
4
```

Four tracked audit documents are not rounds. `UX-583`'s guard
enumerates `round-\d+` only, so the other four were outside every
clause it holds — and `architecture-review.md`, 45,132 B and thirteen
reviews long, was in no index at all.

`spec-compliance-review.md` was reachable, but only as the last entry
of the `·`-separated round run under `## Audits` — a run whose every
other entry is a round number. Being in the run is not being indexed;
it is being mis-shelved.

### The close, measured

```text
$ git ls-files 'docs/audits/*.md' | grep -vc 'round-[0-9]'
4
$ python3 -m pytest tests/unit/test_the_round_history_names_every_audit.py -q
8 passed
```

`## Audits` now opens with a two-row table — the review log, said to
be append-only and why, and the original spec-compliance review — and
the round run below it is rounds only.

### Mutations

| mutation | result |
|---|---|
| the review log's row deleted | 1 red, naming `docs/audits/architecture-review.md` |
| a new `docs/audits/*.md` tracked with no row | 1 red, naming `planted-standing-record.md` |
| the review log moved from its row into the round run | 2 red — the missing row *and* the stray in the run |

Three applied, three red. The third is the pair the second clause
exists for: a document can be linked and still be in the wrong index,
which is the defect this item was filed over.

### Deviation from the Required Fix

**One.** The Required Fix says the audits *table* carries every
non-round document. There are two tables under `docs/audits/`'s
headings — case studies (§Case studies) and the round run's new
standing-records table — and the four documents do not share a shape:
two are session records, two are standing reviews. So the guard reads
"a table row anywhere in `docs/README.md`" and does not dictate which
table, with the converse clause (not in the round run) carrying the
part that actually failed. `NAMED_FLOOR = 4` keeps the scan
non-vacuous.

### Tier and suite

`test_the_round_history_names_every_audit.py` unlisted, so small;
8 tests in 0.07s.
