# UX-1150: booleans and dashes stand in for a verdict

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M7 | **Serves:** R5 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_boolean_is_a_verdict.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M7).

`#capacity_verdict` answers "Was the capacity right?" with "Oversubscribed false / Undersubscribed false / Checks ran true"; elsewhere "Records embedded false", "Run identity available true"; absence reads "—" in some places and "none" in others.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

A boolean group renders as one verdict sentence; absence has one word.

## Decision

- `_build_capacity_verdict` publishes `verdict`, one sentence over the group ("Capacity matched demand: neither over- nor undersubscribed, and both checks ran."; oversubscribed/undersubscribed/checks-skipped each say so), declared additive in `bga/schemas.py` with `bga:lead` (UX-1143's hint): a section with a lead draws its boolean members only through that sentence; the JSON view keeps them.
- Every other boolean the page draws in a `dd` or a cell reads `yes`/`no`; every null reads `none`, the word empty collections already use (`ABSENT` in `primitives.js`). `quantity`'s own null dash in `format.js` is number formatting (UX-1140) and stays.
- Guard: `tests/unit/test_a_boolean_is_a_verdict.py`, Chromium on the two-plane page, `golden` and `macro_micro`: no `dd`/`td` value reads `true`, `false` or `—`, and `#capacity_verdict` opens with its sentence. Mutations: booleans back to `String(value)` (red); null back to `—` (red); the lead rule off (red).

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no visible `dd` reads `true` or `false`, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Outcome

**Gap measured.** The two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`, `capture report --json`, `bga_view --export`), Chromium, every `dd`/`td` with finding cards hydrated, its `?` door and description removed:

```text
width  cells  "true"  "false"  "—"  "none"  "yes"  "no"  #capacity_verdict first block
1440   1822   23      66       9    17      0      0     DL.pairs
390    1822   23      66       9    17      0      0     DL.pairs
```

**Close measured.** Same page and read:

```text
1440   1810   0       0        0    24      22     64    P.section-lead
390    1810   0       0        0    24      22     64    P.section-lead
```

`#capacity_verdict` reads "Capacity matched demand: neither over- nor undersubscribed, and both checks ran."; `macro_micro` reads "The capacity checks did not run - native_max_jobs missing - so neither over- nor undersubscription was tested." The cell count is not held equal: the three answered booleans leave `#capacity_verdict`, and UX-1143 (the commit before) moved the capacity finding's evidence out of its card.

**Mutation table.** `PYTEST_XDIST= python3 -m pytest tests/unit/test_a_boolean_is_a_verdict.py`, 9 tests (two-plane at 1440 and 390, `golden` and `macro_micro` at 1440, one sentence case):

| mutation | reddened | count |
|---|---|---|
| `plainValue` prints a boolean as `String(value)` | `test_no_value_cell_reads_a_boolean_or_a_dash` x4 (two-plane "86 cells, 13 distinct") | 4 failed, 5 passed |
| `ABSENT` is `—` again | `test_no_value_cell_reads_a_boolean_or_a_dash` x4 (two-plane "7 cells, 5 distinct") | 4 failed, 5 passed |
| a lead no longer answers its booleans (`renderPairs` draws them) | `test_the_capacity_verdict_is_a_sentence` x4 ("drawn again: Checks ran, Oversubscribed, Undersubscribed") | 4 failed, 5 passed |
| `_build_capacity_verdict` publishes no sentence | `test_the_capacity_verdict_is_a_sentence` x4, `test_each_state_has_its_own_sentence` | 5 failed, 4 passed |
| reverted from the copies | - | 9 passed |

Merged-tree fix: `test_no_field_is_withheld[golden]` skips `rule.comparison` "present" with no observed path (UX-1141 dropped the only text carrying it; the block reads "No named threshold").
