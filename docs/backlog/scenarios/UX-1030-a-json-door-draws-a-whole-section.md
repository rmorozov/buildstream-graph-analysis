# UX-1030: a "view as JSON" door draws a whole section as one node

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §3k | **Serves:** R1, R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on the 4,002-element run (`bga gen-synthetic --seed 1 --layers 20 --width 200 --store --runs 30`), exported, 1440x900, every chapter open, then every step control pressed.

```text
largest JSON door opened   3,592,666 characters (elements); 21,967 on macro_micro (findings)
```

## Decomposition

Input classes: JSON doors on sections of 1 KB, 22 KB and 3.6 MB. The journey extends opening a section's JSON into copying the whole of it.

## Required Fix

The labeled fold in `bga/viewer/structured.js` draws at most a stated number of characters and offers the whole value as a copy, not as a node.

## Out of Scope

The copy itself, which may be any size.

## Acceptance Test

The §3k census (UX-1032): no opened JSON door holds more than the stated cap. Mutation: draw the whole value, and the census reds.

## Outcome

**Gap measured.** The "view as JSON" door is `bga/viewer/rawjson.js`
(`jsonToggles`), not `structured.js` - the file named there holds the
per-cell labeled fold (`CELL_TEXT_CAP`), a different escape §1 already
bounds. `JSON_DOOR_CHAR_CAP = 20_000` added; past it the `<pre>` holds
a prefix and a `<button class="copy-json-whole">` copies the whole
published value, never a second node.

**Close measured.**
`pytest tests/unit/test_every_step_past_a_bound_is_bounded.py -q` (this
row's clauses): `10 passed`. The largest door on the 4,002-element run
(`elements`) reads exactly `20,000` characters after the cap, against
`3,591,520` before it.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `if (json.length > JSON_DOOR_CHAR_CAP)` -> `if (false)` (draw the whole value) | `TestTheCensusReadsSomething::test_at_least_one_door_reaches_the_cap`, `TestEveryJsonDoorStaysBounded::test_no_door_ever_draws_past_the_cap` | 2 of 10 |

`test_the_mapping_is_law.py`'s round-trip clause read the whole
`data-raw-json` box's `textContent`, which now includes the caption and
copy button past the cap - fixed to read the `<pre>` alone and to judge
a capped prefix against the published value rather than `JSON.parse`.
