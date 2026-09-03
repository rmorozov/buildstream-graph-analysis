# UX-549: five counted figures, read as current, wrong

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** a reader deciding whether to trust the document around the number | **Topic:** docs

## Motivation

Architecture review 12, checklist item 3. Each is a *count* a reader
takes as the document's own arithmetic, and none is guarded:

```text
document                                claim              actual
docs/README.md:88                       "eight of those    9  (contracts.superseded();
                                         are only ever         its own parenthetical
                                         *read*"               on :90-92 lists nine)
docs/design/architecture.md:965         "The last four     6, and not last: nine
docs/spec/specification.md:1671          rows are written  read-never-written rows
                                         but not printable" follow them
CHANGELOG.md:5                          "the twelve        23 (contracts.ids(); the
                                         published              file's own state block
                                         contracts"             at :102 lists 23)
README.md:114                           "all thirteen      17 (bga/viewer/questions.js;
                                         canned questions"     what-the-viewer-answers.md
                                                               :53 says seventeen)
docs/guides/what-the-viewer-answers.md  report.json        53 top-level sections
  :19-26, "Measured on macro_micro"      "25 top-level     element_join 24 keys each
                                         sections",
                                         element_join
                                         "19 keys each"
```

The last is the worst placed: it is the evidence block for that
document's central rule ("the report has no time axis"), and it has
been wrong since `UX-344` lifted the `signals` and `structural`
namespaces to the top level — five reviews walked past it.

The `docs/README.md` one is the sibling of a figure that *is* guarded:
`test_the_unknown_to_schema_sentence_counts_correctly` holds "the last
fifteen" on the same line, and "eight" beside it holds nothing.

## Required Fix

Each figure derived rather than restated, or guarded where a derivation
is not available. `contracts.superseded()`, `contracts.ids()`,
`QUESTIONS.length` and `len(payloads(...)["report.json"])` are all
readable at test time; the pattern is the guard that already holds the
sentence next door.

## Out of Scope

- The spec's Part text: it is ground truth by the review's own rule,
  so the architecture copy is in scope and the spec line is filed
  against rather than edited here.

## Acceptance Test

Each of the five re-derived and pasted; a mutation to any one of the
underlying populations reddens a guard rather than passing.

## Outcome

**Round 81, 2026-09-03.** All five re-derived, in one guard file that
recomputes each population.

**The five, measured:**

```text
figure                              claimed  measured  from
docs/README.md:88   read-only            8         9  contracts.superseded()
docs/README.md:92   printable            8         8  contracts.printable()
architecture.md:964 written-not-print    4         6  unprintable() - superseded()
architecture.md:967 read-never-written  "last"     9  and they *are* the last 9 rows
CHANGELOG.md:5      published set       12        23  contracts.ids()
README.md:114       canned questions    13        17  questions.js QUESTIONS
guide:19-26         report sections     25        53  len(payloads(RUN)["report.json"])
guide:19-26         element_join keys   19        24  and 11 rows, which was right
```

The architecture sentence was wrong twice — the count, and *last*: nine
read-never-written rows follow the six it was about. Both halves are
now read off the table's own rows.

**Mutations verified red and reverted (15).** Five populations and
eight documents, so each figure reddens both when the thing it counts
moves and when the sentence is edited back:

| mutation | reddened |
|---|---|
| `superseded()` +1 (`sources/v0`) | the index's read-only clause, the architecture's last-nine and rows-before clauses, the CHANGELOG clause |
| `ids()` +1 (`OWNED = ("probe/v1",)`) | the architecture's written-not-printable clause, rows-before, the CHANGELOG clause |
| `printable()` +1 (a `_SCHEMAS` entry) | the index's printable clause, the CHANGELOG clause |
| `QUESTIONS` +1 | both question-count clauses |
| a question the text parse cannot see | `test_node_agrees_on_the_count` |
| `report.json` +1 top-level section | the guide's section-count clause |
| an `element_join` row +1 key | the guide's element_join clause |
| each of eight sentences edited back to its old figure | exactly the clause that names it |

**A guard of mine that did not discriminate at first.** Every clause
was written against the document's line wrap (`f"{word} of those\nare
only ever *read*"`), which made the CHANGELOG clause fail on a correct
sentence that wrapped one word earlier. Where the wrap falls is the
author's, not the claim's, so the file now flattens whitespace before
matching. The `printable()` clause and the node cross-check were both
green through the first eleven mutations and needed two more written
for them — recorded because a clause nothing has reddened is a clause
nobody has tested.

**Filed rather than fixed:** `docs/spec/specification.md:1671` carries
the same wrong sentence ("The last four are **written but not
printable**") and is ground truth by the review's own rule. It needs a
backlog row of its own; this track does not own
`docs/backlog/scenarios/README.md` (`UX-501` gives the index to the
orchestrating session), so the row goes to that session with this
text: *the spec's Part 32.5 says "the last four" of six, and nine
read-never-written rows follow them — the architecture copy was fixed
by `UX-549`.*

**Deviation from the Required Fix:** none. One figure beyond the five
was guarded — "The other eight" on the same `docs/README.md` line —
because it was restated the same way and is one edit from being wrong.

**Tier:** `make test-small` — 3,485 passed, 39 skipped, 25.63s; the 4
failures are the index-row status pair this track does not own.
`make lint` clean. New file
`tests/unit/test_a_counted_figure_is_derived.py` (11 tests, 0.54s)
needs a **small** tier row.
