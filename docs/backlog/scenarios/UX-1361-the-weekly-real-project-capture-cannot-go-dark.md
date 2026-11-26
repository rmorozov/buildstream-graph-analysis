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
artifacts. Policy stays `pinned` (UX-514); re-pin to `dd4b4ece` (superseded by rework 3: advanced)
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

**Rework 3** (2026-11-24, owner's batch: "fix the weekly capture's cut step"). The re-pin went dark too: scheduled runs 42468092048, 43702204195 and 45012490234 (11-08, 11-15, 11-22) red at the cut, the last reading `79 element(s) ... 126 elements, 104 not cached`. Dispatched warm pulls, all `components/libxml2.bst`, verify step's own line:

| ref | committed | not cached of 126 | beyond the cut |
|---|---|---|---|
| `db97cce3` 26.08.0 | 09-01 | 124 | 99 |
| `114ae909` 26.08.4 | 10-26 | 36 | 11 |
| `dd4b4ece` (the pin) | 10-27 | 104 (11-22) | 79 |
| `783dba2b` release/26.08 head | 11-23 | 26 | 1 (`bootstrap/build/rsync.bst`) |
| `20b2828f` master head | 11-23 | 26 | 1 (same) |

The cache holds no commit for more than weeks, release tags included, so no pin survives: `capture-ref-policy: advanced`. The clone step resolves the newest `release/26.08` commit at least `FDSDK_LAG_DAYS` 2 old when no commit is dispatched; the verify step builds up to `BEYOND_CUT_MAX` 2 stragglers and writes them to `capture/beyond-cut.txt`, red above. The trend glob stays per commit: `bga baseline` refuses a set across `fdsdk_ref` (`HOMOGENEOUS_FIELDS`), so a cross-commit trend is `UX-92`'s, not this row's. `python3 -m pytest -q -p no:xdist tests/unit/test_the_weekly_capture_takes_a_commit_the_cache_holds.py` -> 6 passed (both step bodies, a dated `file://` remote, fixture state):

| mutation | count |
|---|---|
| R1 `--before` lag dropped | 1 failed, 5 passed |
| R2 a dispatched commit re-resolved | 1 failed, 5 passed |
| R3 `BEYOND_CUT_MAX = 0` | 1 failed, 5 passed |
| R4 `BEYOND_CUT_MAX = 9` | 1 failed, 5 passed |
| R5 `beyond-cut.txt` not written | 2 failed, 4 passed |
| reverted | 6 passed |

Owner review of #352: the lag now walks `--first-parent`, so a merged topic's older date never resolves; the fetch is `--depth` 200 then 2000, so a branch quiet past any `--shallow-since` window resolves to its tip; and a new step fetches `beyond-cut.txt`'s sources `--deps none` between the verify step and the capture, so a straggler's download is not inside the timed build. Same file -> 10 passed:

| mutation | count |
|---|---|
| R6 `--first-parent` dropped | 1 failed, 9 passed |
| R7 `--shallow-since="30 days ago"` restored | 1 failed, 9 passed |
| R8 `xargs` without `-r` | 1 failed, 9 passed |
| R9 the pre-fetch reads `rebuild-set.txt` | 2 failed, 8 passed |
| R10 the pre-fetch moved after the capture | 1 failed, 9 passed |
| reverted | 10 passed |

`test_the_pinned_ref_is_a_decision.py`: the pin-copy check skips under `advanced`; its mechanism check passes. Open until three consecutive green scheduled runs.
