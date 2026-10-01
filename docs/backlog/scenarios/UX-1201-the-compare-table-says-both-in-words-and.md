# UX-1201: the compare table says 'both' in words and scales negative durations

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_value_is_what_it_names.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

culprits: the sentence "Every row: Presence both." names the field presence; negative changes print "-50 ms", "-5050 ms", and the strip "-8450 ms to 8.9 s", unscaled beside "8.9 s" (walk N13).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The constant-column sentence uses reader words for presence; a negative duration scales as a positive one does.

## Decision

Route: `duration()` formats the magnitude and prefixes the sign (one function, every caller). `READER_LABELS` gains `both: "both runs"`, `appeared: "the candidate only"`, `disappeared: "the baseline only"` and the five verdict kinds (so `Verdict no_significant_change` reads "No significant change"). The compare rows' `presence` column title becomes "In", so the sentence reads "Every row: In both runs." Rejected: a presence special-case in `statedOnce`, since the cells show the raw word too; the one map fixes both.
Files: `bga/viewer/format.js`, `bga/schemas.py` (one title), `tests/unit/test_a_value_is_what_it_names.py`.
Class: product.

## Out of Scope

The compare table's columns (`UX-1188`).

## Acceptance Test

No reader text holds "Presence both" and -5050 ms prints as -5.1 s; a guard in `test_a_value_is_what_it_names.py`. Mutation: restore the defect, and the guard reds.

## Outcome

Gap measured (round-158 walk, scale_both): "Every row: Presence both."; strips "-8450 ms to 8.9 s". `duration()` tested `s < 1` on the signed value, so every negative printed as ms.

Close measured (`PYTHONPATH=. PYTEST_XDIST= python3 -m pytest tests/unit/test_a_value_is_what_it_names.py -q`): 6 passed. `duration(-5_060_000)` is "-5.1 s", `-50_000` "-50 ms"; the two-plane page's uniform-columns sentence reads "In both runs" and no text matches /-\d{4,} ms/. Page half: +9 lines of JS, 0 words on golden and macro_micro (no compare table).

| Mutation | Reddened | Count |
|---|---|---|
| delete the `microseconds < 0` branch of `duration()` | `test_a_negative_duration_scales_as_a_positive_one_does` | 1 failed, 5 passed |
| delete `READER_LABELS.both` | `test_the_constant_column_sentence_says_both_runs_not_presence_both` | 1 failed, 5 passed |

Deviation: the task's "-5050 ms prints as -5.1 s" is 5.05 s, which `toFixed(1)` rounds to 5.0 (binary float); the guard uses 5,060,000 us. The guard's page is `two_plane_run` (SHAPE 8x14), whose compare table carries the sentence; xl_both was not built.

**Deviation (round 159 verification).** `duration(-400)` and `duration(-499)` printed "-0 ms": the sign was prefixed to a magnitude that rounds to 0; such a negative now prints "0 ms".
Node, `[-400, -499, -500].map(duration)`: `["-0 ms", "-0 ms", "-1 ms"]` -> `["0 ms", "0 ms", "-1 ms"]`.
Mutation: the zero test removed gives `test_a_negative_duration_scales_as_a_positive_one_does` 1 failed, 5 passed.
