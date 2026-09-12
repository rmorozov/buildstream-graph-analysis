# UX-818: two canned queries error when an element is given

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-432 (the library runs) | **Found by:** round 114, walk seed 3 | **Serves:** R1 at the Perfetto handoff | **Topic:** guards | **Area:** tools | **Shape:** judgement

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
