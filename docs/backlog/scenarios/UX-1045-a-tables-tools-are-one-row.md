# UX-1045: §3's tool row names the column thresholds §3d attaches to their headers

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §3, §3d | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

## Motivation

§3 says "one tool row per table: filter, presets, top-N, copy"; §3d
puts a threshold filter under each quantity column, in that column's
`th`. The two coexist - a threshold belongs to its column, not to a
second toolbar - but §3's sentence lists "filter" without saying which,
and the audit read it as a contradiction. Measured on `main` at
`814a2db8`, the element table on `macro_micro` at 1440x900: the tool
row holds `input.table-filter`, `select.top-n` and `button.copy-rows`
at page y 8,632; the thresholds sit in the header at 8,740.

## Decomposition

Input classes: a table under the row cap (no thresholds, §3d), over it,
in table focus (§3a).

## Required Fix

§3's sentence names the text filter as the tool row's and the
thresholds as §3d's, attached to their own `th` cells. No control
moves: a placement change needs its own measured reader benefit, which
this row does not have.

## Out of Scope

Moving Copy or the thresholds; the filter's parsing
(`parseThreshold`).

## Acceptance Test

§3 and §3d read as one rule; `test_the_tools_scale_with_the_table.py`
stays green. Mutation: none - a wording row with no page change has no
new guard, and says so here.

## Outcome

Gap: §3 listed "filter" in the tool row without saying which, so §3d's
per-column thresholds read as a second row. Close: §3 names the text
filter as the row's and the thresholds as §3d's, in their `th`
(`docs/design/styleguide.md` §3). No control moved.

```text
$ PYTHONPATH=$PWD python3 -m pytest -q tests/unit/test_the_tools_scale_with_the_table.py tests/unit/test_the_styleguide_names_its_guards.py
28 passed in 8.07s
```

Mutation: none - a wording row with no page change adds no guard, as
the Acceptance Test says.
