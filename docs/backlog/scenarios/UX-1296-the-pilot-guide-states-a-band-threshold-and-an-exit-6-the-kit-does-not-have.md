# UX-1296: `pilot.md` states a band threshold and an exit-6 behaviour the kit does not have

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 36, checklist item 1 (2026-10-02) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
