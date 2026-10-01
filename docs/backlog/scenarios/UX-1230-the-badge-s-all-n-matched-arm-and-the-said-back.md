# UX-1230: the badge's all-N-matched arm and the said-back clause's owned-words rule have a mutation that reddens them

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-160 residue pass, track R (2026-10-01) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_value_is_what_it_names.py::test_a_filter_that_keeps_every_row_says_all_n_matched`, `tests/unit/test_a_key_column_matches_exactly.py::test_a_word_another_column_also_names_is_not_taken_as_the_column_s_own`

## Motivation

Track R's pass left two arms unguarded: the badge's `all N matched` (`UX-1213`'s follow-up 2, `badgeText` unbounded and narrowed) and the owned-words rule of the said-back clause (`UX-1206`'s follow-up: a word no other column owns).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

One guard each, in the files that hold their claims, each reddened by deleting its arm.

## Out of Scope

The arms' behaviour.

## Acceptance Test

Guards in `test_a_value_is_what_it_names.py` and `test_a_key_column_matches_exactly.py`; deleting the `all N matched` arm, or taking a word another column also names as the column's, reds one. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     Two node unit tests, no browser: badgeText(n, n, n, {narrowed: true}) gives "all n matched", and parseQuery with element and element_kind specs leaves "element <word> kind:x" applied (the shared word "element" is not counted as kind's own word).
Rejected:  browser walks (the arms are pure functions in tables.js); adding to existing assertions (neither arm is reached by one today).
Files:     tests/unit/test_a_value_is_what_it_names.py, tests/unit/test_a_key_column_matches_exactly.py
Guard:     test_a_value_is_what_it_names.py: a filter that keeps every row says "all N matched"; test_a_key_column_matches_exactly.py: a word another column also names is not taken as the column's own.
Mutation:  tables.js:441 `(matched < total ? of : `all ${of}`)` -> `of`; tables.js:114 drop `&& (names.get(word) ?? spec) === spec`. Each reddens exactly one guard.
Class:     product (guards shipped arms)
Split:     tests only; parallel with everything.
Question:  none
```

## Outcome

**Gap measured.** Before: `grep -rl "all [0-9a-zN]* matched" tests/unit` found only this commit's new test; the shared-word rule had no test naming it (Decision: neither arm is reached today).

**Close measured.** Two node unit tests, no browser: `badgeText(5, 5, 5, { narrowed: true })` is `all 5 matched` (and `badgeText(5, 5)` stays `5 rows`); `parseQuery("element foo kind:x", [element, element_kind])` leaves `element foo` as text, `unread` empty, one exact clause on `element_kind`. Both files: 31 passed in 44.76s (`-n 2`). No viewer change committed; `tables.js` restored from a copy.

**Mutation table.**

| Mutation | Red | Count |
|---|---|---|
| `tables.js:441` `(matched < total ? of : `all ${of}`)` -> `of` | `test_a_filter_that_keeps_every_row_says_all_n_matched` only | 1 failed, 1 passed |
| `tables.js:115` drop `&& (names.get(word) ?? spec) === spec` | `test_a_word_another_column_also_names_is_not_taken_as_the_column_s_own` only | 1 failed, 1 passed |

**Deviation.** The Decision cites the second arm at line 114; the filter is on line 115 (114 is the `const own` opener).

