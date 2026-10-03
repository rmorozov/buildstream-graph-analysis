# UX-1296: `pilot.md` states a band threshold and an exit-6 behaviour the kit does not have

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 36, checklist item 1 (2026-10-02) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_pilot_kit_runs_report_only.py::TestTheBandThreshold`

## Motivation

`docs/guides/pilot.md` is R4's first page, and two of its sentences
disagree with `examples/ci/bga-pilot.sh` run on the guard's own fixture
(`tests/unit/test_a_pilot_kit_runs_report_only.py`'s `pilot`):

- `:63-65` and the exit table at `:133` say the band refuses *below
  three kept runs of the class*. `_resolve_band_from_class` excludes
  both principals, and the kit's baseline is the newest kept bundle, so
  the band needs four kept runs before the candidate:

  ```text
  prior kept  kept with candidate  verdicts.tsv
  2           3                    rule  4
  3           4                    rule  4
  4           5                    band  4
  ```

- `:132` says exit 6 *logs the refusal, no comment*. With four runs kept
  on a 4-core host and a candidate from an 8-core one, the band skips
  all three for host (exit 8), the rule fallback's cross-host gate
  exits 6, and the kit prints a 2,263-character comment that starts
  with `<!-- bga-ci-comment -->` — the marker the workflow posts on.
  `verdicts.tsv`: `rule 6`.

No guard reads either sentence: the pilot guard checks switches, flags
and three verdict paths (rule 4, enforce 4, band 4).

## Required Fix

`pilot.md`'s threshold says four kept runs of the class before the
candidate (three for the band, one for the baseline), derived from
`MIN_BASELINE_RUNS` plus the baseline; the exit-6 row says what the kit
does (comments, with the refusal on stderr). `cli.md`'s exit `8` entry
says *three runs besides the two principals*.

## Out of Scope

Whether exit 6 should post a comment (a kit-behaviour row, if the owner
wants one); the workflow's kept verdicts (`UX-1297`).

## Acceptance Test

The pilot guard gains two cases: three prior kept runs judge against
the rule and four against the band, and a cross-host candidate writes a
comment and records `rule 6`; the guide's threshold is read from
`MIN_BASELINE_RUNS` by the same guard. Each reddens on its mutation.

## Outcome (round 167, 2026-10-03) — 🟢 Done

**Premise:** held — the kit judges 3 prior kept runs against the rule
and 4 against the band, and a cross-host refusal prints a 2,263-character
comment and records `rule 6`.

### The gap, measured

```text
$ git show 5e1b9fa76:docs/guides/pilot.md > docs/guides/pilot.md
$ pytest -q -p no:xdist tests/unit/test_a_pilot_kit_runs_report_only.py -k TestTheBandThreshold
FAILED ...::TestTheBandThreshold::test_the_guide_reads_the_threshold_off_min_baseline_runs
FAILED ...::TestTheBandThreshold::test_a_cross_host_refusal_still_comments
2 failed, 2 passed, 15 deselected in 5.44s
```

The kit's behaviour already matched the row's table (both parametrized
cases green on the base guide); the guide's "three" and "no comment"
were the defect.

### After

```text
$ pytest -q -p no:xdist tests/unit/test_a_pilot_kit_runs_report_only.py
19 passed in 14.50s
cross-host probe: report exit 0, stdout 2263 chars, stderr "Cross-host gate FAILED: ...",
verdicts.tsv "20261003T001517Z  review  default  rule  6"
```

`pilot.md` says *below 4 kept runs of the class before this build*
(the band's 3 besides both principals, plus the baseline) in prose and
the exit-8 row, both read off `MIN_BASELINE_RUNS + 1`; the exit-6 row
says *comments; the refusal is on stderr*. `cli.md`'s exit `8` says
*three runs ... besides the two principals*.

The guard's `bga.compare` import adds one file to `compare`'s
selection, the p90 module: `test_the_loop_stays_fast.py`'s measured
shape went 67 → 68 (median 41, max 196 over 814), and its `CEILING`
moves with it, as each earlier guard's did.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A1 | `MIN_BASELINE_RUNS = 2` (`bga/compare.py`) | `[3-rule]`, threshold-read: 2 failed |
| A2 | `MIN_BASELINE_RUNS = 4` | `[4-band]`, threshold-read: 2 failed |
| A3 | guide prose `Below 4` → `Below 3` | threshold-read: 1 failed |
| A4 | guide exit-6 row back to `logs the refusal, no comment` | cross-host: 1 failed |
| A5 | kit prints no comment on `rc` 6 | cross-host: 1 failed |

Every guard discriminated; green after each revert (19 passed).

### Deviation from the Required Fix

None.

```text
$ make lint
1002 files already formatted
tools: pyright 1.1.414, ruff 0.16.9
```
