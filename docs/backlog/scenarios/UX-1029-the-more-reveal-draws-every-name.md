# UX-1029: the "+N more" reveal draws every name in one run of text

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R4 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed.

```text
reveal at rest     6 + 3 names (PATH_HEAD + PATH_TAIL)
after "+N more"    3,625 names, one 72,703-character run
```

The populations are `resource_blast.rows[].blast_elements` (3,634) and `direct_elements` (572), and `parallelism.levels[].elements` (208).

## Decomposition

Input classes: chain and element lists at 0, 9, 208 and 3,634 names. The journey extends reading a list's head into walking the rest a page at a time.

## Required Fix

The reveal in `bga/viewer/views.js` replaces the shown names with the next bound of them, the position shown, or opens the names as a table under table focus. It never appends.

## Out of Scope

The at-rest head and tail.

## Acceptance Test

The §3k census (UX-1032): each reveal pressed 10 times mounts at most the bound of names besides the head and tail. Mutations: reveal the whole list, or append each step, and the census reds.

## Outcome

**Gap measured.** The reveal this row is about is `boundedList` in
`bga/viewer/structured.js` (not `views.js` - `views.js` only exports
the `PATH_HEAD`/`PATH_TAIL` constants `boundedList` reads). Before the
fix, one press of `+N more` set `first.textContent = items.join(", ")`,
every middle name in one span. `REVEAL_STEP = 60` added; the button
now pages `middle.slice(offset, offset + REVEAL_STEP)` into a
`.list-middle` span, **replacing** it each press, and hides once
exhausted.

**Close measured.**
`pytest tests/unit/test_every_step_past_a_bound_is_bounded.py -q` (this
row's clauses): `10 passed`.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `chunk = middle` (whole list, one press) instead of `middle.slice(offset, offset + REVEAL_STEP)` | `TestEveryRevealStaysBounded::test_no_reveal_ever_mounts_past_the_bound` | 1 of 10 |
| `shownMiddle.textContent += …` (append) instead of `=` (replace) | same clause, mounted count grows 60 -> 120 -> 180 -> 198 over presses | 1 of 10 |
