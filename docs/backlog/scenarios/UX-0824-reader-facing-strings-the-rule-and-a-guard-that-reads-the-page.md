# UX-824: reader-facing strings: the rule, and a guard that reads the page

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-669 (a task id is never bare in prose), UX-665 (the census) | **Found by:** round 115, the design review | **Serves:** every reader of the page | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

§4b's sentence rule exists and no guard reads the rendered page for
it. Measured this round on `document.body.innerText`:

```text
scale export (1,202 elements)   bare task ids: UX-478, UX-478, UX-345, UX-477
walk capture                    UX-14 in findings ("does not model contention (UX-14)")
span.section-key visible        37 of 47 (scale) · 47 (walk, every open section)
duration_resolution "Tasks?"    all.bst|FETCH|FETCH|0   — a pipe-delimited task key
```

The guide has the rule in three places (§4a, §4b, §4f); §4g gathers
them into one list a contributor can read before writing a sentence,
and one guard holds it.

## Required Fix

§4g in the styleguide (landed this round) is the list: no task id, no
payload key outside the JSON door, no internal task key, no "payload",
"contract" or "Part N", every quantity with its unit and every instant
with its origin. `tests/unit/test_a_reader_never_sees_the_register.py`
boots the golden export and the scale export and asserts each line of
the list on `innerText`; it cites §4g.

## Out of Scope

- Fixing the five citations and the section keys — `UX-825`, `UX-826`.
- The text renderer's own strings — a second guard on `bga analyze` output, filed when §4g holds on the page.

## Acceptance Test

The guard is red on `main` today (five ids, 37 keys) and green once
`UX-825` and `UX-826` land; mutation: reintroduce one bare id in a
finding sentence — red.
