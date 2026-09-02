# UX-549: five counted figures, read as current, wrong

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** a reader deciding whether to trust the document around the number | **Topic:** docs

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
