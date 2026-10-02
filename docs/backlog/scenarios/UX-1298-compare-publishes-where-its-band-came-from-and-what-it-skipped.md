# UX-1298: `compare/v2` publishes where its band was read from and how many members it skipped for host

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 36, checklist item 2 (2026-10-02) | **Serves:** R4 | **Topic:** contracts | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1285` and `UX-1286` added two answers to a band comparison: how
many class members were skipped as measured on another host, and that
the band was read from a `--bundles` tree. Both reach stderr and the CI
comment (`bga/report/ci_comment.py:_band_selection`) and no contract:

```text
$ grep -rn "band_skipped_for_host" bga --include=*.py | cut -d: -f1 | sort -u
bga/cli.py
bga/report/ci_comment.py
$ bga compare BASE CAND --format json --band-from-class 10 --bundles kept/review/default
  (pilot fixture, four kept runs)  schema compare/v2, 34 keys;
  baseline_band_sources lists 3 stamps; "skipped" in the document: False; the tree's path: False
```

`continuous-build-improvement.md` §5 fixes the order for every new
answer: a key in a published contract, then the report line. This one
went report-first, so a JSON consumer of the gate cannot tell a band of
three from a band that dropped seven for host.

## Required Fix

`compare/v2` gains the skipped count (and which host fields differed)
and the band's source (store or tree) as added keys, no version bump;
the CI comment reads them from the comparison rather than from `args`;
`cli.md`'s compare key list and `architecture.md`'s `compare/v2` entry
name them.

## Out of Scope

A fuzzy host class (`UX-1285`'s own Out of Scope).

## Acceptance Test

A band comparison with one member on another host publishes the count
and the source in `--format json`; the comment's sentence is rendered
from those keys; removing either key reddens the guard.

## Outcome
