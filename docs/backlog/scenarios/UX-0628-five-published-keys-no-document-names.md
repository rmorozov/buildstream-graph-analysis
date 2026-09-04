# UX-628: five published keys no document names

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-233 (the mechanical half), UX-610, UX-612 (which added them) | **Found by:** architecture review 15 | **Serves:** anyone reading a payload against the prose that describes it | **Topic:** contracts

## Motivation

Five keys shipped in this window and no document outside
`docs/backlog/` and `docs/audits/` names any of them:

```text
verdict_provenance            compare/v2      UX-610
queue_wait_us                 store/v1        UX-594
queue_wait_absent_reason      store/v1        UX-594
requested_at_us               run-context/v9  UX-612
requested_at_source           run-context/v9  UX-612

$ git grep -l <key> -- 'docs/**/*.md' README.md ':!docs/backlog' ':!docs/audits'
(empty, for each of the five)
```

The prose that should carry them stops short. `architecture.md:946`
ends `compare/v2` at *"the candidate's diagnosis chain"*;
`architecture.md:1011` ends `run-context/v9` at *"the resolved
`native_max_jobs`"*. Both contracts gained keys after those sentences
were written.

`test_the_documents_keep_up_with_the_contracts.py` is green because it
guards **ids**. Five keys walked past it, which is `UX-233`'s
mechanical half doing exactly what it promised and no more.

## Required Fix

The prose rows for `compare/v2`, `store/v1` and `run-context/v9` name
what they now carry, and the guard's population is keys rather than
ids — or, if key-level coverage is deliberately out of scope, the
document says so where a reader will look.

## Out of Scope

- `UX-629`'s question about the required set, which is the same window
  and a different property.
- The keys themselves — they are right, and this row is about the
  prose beside them, not the payload.

## Acceptance Test

A key added to a live schema with no prose, reddening a guard that
names the key.
