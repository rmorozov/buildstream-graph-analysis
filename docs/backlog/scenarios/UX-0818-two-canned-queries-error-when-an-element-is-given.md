# UX-818: two canned queries error when an element is given

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-432 (the library runs) | **Found by:** round 114, walk seed 3 | **Serves:** R1 at the Perfetto handoff | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

On seed 3's cold trace (examples/08, 2011 slices, 2002 flows), the
question library answers 16 of 18 with `--element storm.bst`; two
error in the reader's SQL parser:

```text
$ python3 tools/dev_perfetto_queries.py cold.pftrace --element storm.bst --fetch --format json
"errors": ["concurrency-curve: syntax error near '{'", "were-the-cores-busy: syntax error near '{'"]
```

`UX-432` ran the library and found it answered; a brace reaching the
SQL means the `{element}` fill is applied to two queries whose text
carries a brace of its own, or is not applied to two that need it.

## Required Fix

Every canned question parses with and without `--element`; the guard
runs the library's SQL through the reader on the smallest committed
trace (or a synthetic one) and asserts no `syntax error` for any
question, both ways. Mutation: put a stray `{` in one question — red.

## Out of Scope

- New questions — declined here: a question is its own row, and the library's population is `UX-432`'s.

## Acceptance Test

18 of 18 answered or legitimately empty on seed 3's trace with
`--element storm.bst`; the guard green; the mutation red.

## Outcome

**Gap measured.** Old `{element}`-only fill against all 18 questions,
`storm.bst`, bare-sqlite `EXPLAIN` (same probe the guard uses):
`concurrency-curve -> unrecognized token: "{"`, `were-the-cores-busy
-> unrecognized token: "{"`; the other 16 read `no such table: slice`
(or `flow`/`counter`). Both reads `{window}` and neither was filled.

**Close measured.** `tools/dev_perfetto_queries.rendered_sql` now fills
`{window}` the way `renderedSql` in `questions.js` does (same clause
for a given element/bounds, same empty fill for none). Run on round
114's own seed-3 capture (`cold.pftrace`, 74,802 B,
`.bga/runs/20260912T114117Z`) with `--element storm.bst`:

```text
empty:  2/18  ['failed-processes', 'waited-on-flow']
errors: 0/18  []
```

18/18 answered or legitimately empty (16 rows, 2 legitimately-empty
fixture facts unrelated to this fix, per `UX-432`'s own reading of
this project). `concurrency-curve` now returns 25 rows,
`were-the-cores-busy` 4.

**Mutations verified red and reverted (1):** a stray `{` inserted into
`element-time`'s SQL in `questions.js` (`limit 25;` -> `limit 25{;`)
reddened exactly `test_question_parses[no-element-element-time]` and
`test_question_parses[with-element-and-bounds-element-time]` with
`unrecognized token: "{"`, all 34 other cases stayed green; reverted
from the scratchpad copy, 36/36 green again.

**Trace-processor-only syntax:** none. All 18 questions, both fills,
parsed against a bare `:memory:` connection with no error worse than
`no such table`/`no such function` - `stalls`'s window function and
the two counter-table questions included. No question is skipped.

**Deviation from the Required Fix:** none.

Deviation: the track's `rendered_sql` emptied a missing element and an
empty `bounds` where the page keeps both tokens, and the guard proved
syntax only - a swapped window passed. Closed at merge: the fill
matches `renderedSql` byte for byte and a parity case per question
runs through node (54 passed; swap 2 red, emptied element 4 red).
