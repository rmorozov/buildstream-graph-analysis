# UX-1361: the weekly real-project capture cannot go dark without someone hearing

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R4 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_dark_scheduled_capture_is_reported.py`

## Motivation

`real-project-capture.yml`'s scheduled runs failed on 2026-10-04, 10-11, 10-18 and 10-25, each in about 4 minutes at "Verify the cut is exactly the rebuild set" (`cp: cannot stat 'capture/run'`); its trend step separately refuses the baseline set ("trace_spine is not in the ref name ... drop 32223468993"). The last good incremental capture is 2026-09-27. It is bga's only standing field reading, and nothing surfaced the failure.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

Fix the 2026-10 failure; a red scheduled run, or a baseline set the trend refuses, opens or updates one tracking issue (or equivalent a human reads).

## Out of Scope

Moving the capture to another target or host.

## Acceptance Test

One dispatched run publishes a capture ref; a forced failure (bad target) produces the notice. Reading: GitHub runner.

## Decision

The cause is the pin, not the tooling: the warm phase of run 40174440140
(2026-10-25) read `126 elements, 103 not cached, 25 in the rebuild set` —
`cache.freedesktop-sdk.io` no longer serves `953683fb`'s (2026-08-14)
artifacts. Policy stays `pinned` (UX-514); re-pin to `dd4b4ece`
(2026-10-27 merge), a new population. The verify step names eviction when
more than half the closure is unpullable. A last step, `failure()` or a
refused trend (review 2) on a `schedule` run, comments on the open "Real-project capture is dark" issue or
opens it (`issues: write`). Mutations: drop the schedule condition, then
the permission.

## Outcome (2026-10-30)

Gap, measured: scheduled runs 37190444368, 38128254134, 39107821899,
40174440140 all `failure` in ~4 min; job 121111972970's verify step:

```text
78 element(s) would be built beyond the intended cut - the warm phase did not pull the whole closure
126 elements, 103 not cached, 25 in the rebuild set
```

Close: guard 4/4; mutations — `if: failure()` only → 3 red; that plus no
`issues: write` → 4 red. The capture itself is re-read by a dispatched run after merge
(Reading: GitHub runner); until then the re-pin is unverified.

**Review correction 2** (owner, PR #336 head `217550fb1`): the trend step catches a failing `bga baseline`, prints and exits 0 under `continue-on-error`, so a green capture whose baseline set is refused never made `failure()` true - the half of the Required Fix the first close left silent. The trend step (`id: trend`) now writes `refused=true` to `$GITHUB_OUTPUT` on any non-zero `bga baseline` and `refused=empty` when its stderr is the tool's own "no capture refs matched" (a first capture's normal state); the report step runs on `(failure() || steps.trend.outputs.refused == 'true') && schedule`, and its issue body names which happened (`JOB_STATUS`, `TREND_REFUSED`). Gap: the step's refusal branch wrote no output and the condition read `failure()` alone. Close: the guard runs the trend step's own shell body against a stub `bga` (exit 6 refusal, exit 1 ls-remote failure, exit 1 with the real tool's empty-glob stderr) and the report body against a stub `gh`; `python3 -m pytest -q -p no:xdist tests/unit/test_a_dark_scheduled_capture_is_reported.py` -> 9 passed.

| mutation | reddened | count |
|---|---|---|
| C1 the condition back to `failure()` alone | both refusals (and empty, which reads its key there) | 3 failed, 6 passed |
| C2 the refusal branch writes another key | both refusals | 2 failed, 7 passed |
| C3 an empty history writes `refused=true` | empty | 1 failed, 8 passed |
| C4 the empty-history grep misses the tool's words | empty | 1 failed, 8 passed |
| C5 the trend step's `id` renamed | both refusals | 2 failed, 7 passed |
| C6 the body ignores `TREND_REFUSED` | refused-on-green | 1 failed, 8 passed |
| C7 the body always says the job failed | refused-on-green | 1 failed, 8 passed |
| C8 `bst_baseline_set`'s empty-glob wording changed | empty | 1 failed, 8 passed |
| reverted | — | 9 passed |

A `bga cache-trend` failure after an accepted set is still `continue-on-error` and unreported; the runner reading (a dispatched schedule) stays the Acceptance Test's.
