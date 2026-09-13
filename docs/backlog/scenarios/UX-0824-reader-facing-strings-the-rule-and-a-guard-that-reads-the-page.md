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

## Outcome

**Gap measured.** `git show 3afade2e:bga/correlate.py | grep -c "(UX-14)"`
→ 1 (pre-`UX-826`). Round 115: scale export bare ids `UX-478, UX-478,
UX-345, UX-477`; `span.section-key` 37 of 47.

**Close measured.** On `HEAD` (866eecde), `pytest -v
tests/unit/test_a_reader_never_sees_the_register.py`: 10 tests (2
exports × 5) → 10 passed, 3.45-3.65s across runs. Boots
`tests.pages.export_uri` on `FIXTURES["golden"]` and `scale_run`
(1,202 elements), every `.description[hidden]`, `data-collapsed`
section and `data-open` chapter forced open, `content-visibility`
lifted (`UX-826`'s scratchpad expression, reused). Items 1-3 zero hits
both exports; item 4 one hit both times, narrowed below; items 5
(`UX-823`) and 6 (§1c/§4c) skipped per brief.

**Item 4 narrowing.** One hit, both exports: `<dt data-key="schema"
title="The shape of this document.">Schema<button>?</button></dt>` -
the document's own `bga:version` field naming itself, not producer
jargon in a sentence. Excludes `tag == DT and data-key == schema`
rather than dropping the word; no other hit either export.

**Item 3 widened** (verifier finding): a `td`-only scan passed with
`duration_resolution.tasks` (`KEYED_BY_TASK_UID`) intact, because that
field renders `<dd><span>all.bst|BUILD|BUILD|0, …</span></dd>` - a
description list, never a table. Now scans item 4's cell set (`p, li,
td, dt, dd, h2`).

**Mutation table.**

| mutation | file | targets | measured |
|---|---|---|---|
| `(UX-14)` in `compute_capacity_recommendation`'s caveat | `bga/correlate.py:1181` | item 1 | stayed **green** both exports - `capacity_recommendation` is `null` on golden and scale even with `-d`: every constraint needs host-CPU-sample data neither fixture publishes; round 115 placed `UX-14` on the walk capture, not the synthetic export. |
| `(UX-478)` in `dependency_stages`'s hint (round 115's own reading) | `bga/schemas.py:1837` | item 1 (substitute) | **red** - `['UX-478']`, 8 passed/2 failed |
| restore `span.section-key` append | `bga/viewer/format.js:369` | item 2 | **red** - 32 (golden)/36 (scale) spans, 8/2 |
| drop `KEYED_BY: KEYED_BY_TASK_UID` from `duration_resolution.tasks` | `bga/schemas.py:3320` | item 3 | **red**, scale only - `all.bst\|BUILD\|BUILD\|0, toolchain.bst\|BUILD\|BUILD\|0` in a `dd`, 9 passed/1 failed |

All four restored from `git show HEAD:<path>` copies; reconfirmed
green, 10 passed, 3.54s.

`make test-touching` at this base: 3 pre-existing reds, none this
track's - `fixing-guide.md`'s touching-map figure (532 vs a measured
533 with no files of mine on the tree), `macro_micro`'s volume budget
(36,846px vs 36,300px), and `test_a_budgeted_outcome_fits[UX-0826]`
(83 lines) - the last already fixed upstream to 80 lines on the round
branch (`65efded3`), not yet merged into this base. Committed with
`BGA_SKIP_SELECTOR=1`.
