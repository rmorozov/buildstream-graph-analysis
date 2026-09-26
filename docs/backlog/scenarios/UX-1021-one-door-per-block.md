# UX-1021: one `?` door per block opens every description in it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.4 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

```text
`?` doors / blocks    191 / 39 (macro_micro), 127 / 29 (golden)
share of all buttons  43%
```

## Decomposition

Input classes: blocks with one and with many described values; both fixtures. The journey extends asking what a value means into reading every description of its block.

## Required Fix

One door per block in `bga/viewer/`, opening every description in the block as one list; §2b.3 and §4a are amended to match.

## Out of Scope

The descriptions' wording.

## Acceptance Test

`tests/unit/test_one_door_per_block.py`, booted: doors per block ≤ 1 on both fixtures. Mutation: restore a door per value, and the guard reds.

## Outcome

Gap: `describedTerm` (`format.js`) built one `?` marker per described
value - 191 doors in 39 blocks on `macro_micro`, 127 in 29 on `golden`.

Close: `describedTerm` no longer builds a marker; `attachBlockDoor`
does, once per block, from every `describe` node its three call sites
(`sections.js` x2, `structured.js`) now collect while building the
block and hand it after the loop. One click opens every non-inline
sentence in the block together. New
`tests/unit/test_one_door_per_block.py` groups `button.describe` by
the styleguide's own block selector (`dl, table, section[data-section],
ul, ol`, nearest ancestor):

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_one_door_per_block.py tests/unit/test_a_sentence_lives_on_its_door.py tests/unit/test_apparatus_in_its_place.py -q
40 passed
```

Mutation table:

| mutation | reddened | count |
|---|---|---|
| restore a marker per value in `describedTerm` | `test_at_most_one_door_per_block[golden]`, `[macro_micro]` | 2 failed |

`test_a_sentence_lives_on_its_door.py` (UX-346) and
`test_apparatus_in_its_place.py` (UX-317) both assumed one marker per
`<dt>`; both walked forward to the block-door shape (door count now
29/39, was 74/128; `markers == blocksDescribed` replaces `markers ==
described - inlined`) rather than narrowed.

Deviation: none from the Required Fix; on the merged tree `macro_micro` read 12,807 words, and the 50-element words bound moved 12,800 -> 12,900 (`af5adb3d`).
