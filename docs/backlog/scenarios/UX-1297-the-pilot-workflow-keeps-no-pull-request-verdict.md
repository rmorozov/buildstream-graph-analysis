# UX-1297: the pilot's workflow keeps no pull request's verdict, and its overhead control is in no file

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** review 36, checklist item 1 (2026-10-02) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_pilot_kit_runs_report_only.py::TestEveryReadingIsKept`

## Motivation

`docs/guides/pilot.md:135-143` names what two weeks measure: the
band's false alarms from `verdicts.tsv`, *one line per report*, and the
overhead against plain `review` builds the sample rate supplies. The
shipped `examples/ci/bga-pilot.yml` keeps neither for a pull request:

```text
$ grep -n "if:\|cache/save\|upload-artifact" examples/ci/bga-pilot.yml
65:        if: always()
69:        if: always() && github.event_name == 'pull_request' && hashFiles('bga-comment.md') != ''
91:        if: always() && github.event_name != 'pull_request'
92:        uses: actions/cache/save@v4
```

`verdicts.tsv` lives under `PILOT_KEEP_DIR`, which is saved only off
pull requests, so every review-gate verdict line is discarded with the
runner. The plain builds are pull requests only (a push sets
`PILOT_REVIEW_SAMPLE=100`), and `bga-pilot.sh` writes nothing for a
plain build: the control is the CI job's own duration, which the guide
does not say.

## Required Fix

Decide whether the pull request's verdict line and the plain build's
wall are kept (an uploaded artifact per run, or a line the report step
prints for the CI log) or the guide says the false-alarm count comes
from main and nightly builds and the overhead from job durations. The
guide and the workflow then say the same thing.

## Out of Scope

The band threshold and exit-6 wording (`UX-1296`); a non-GitHub wrapper.

## Acceptance Test

The pilot guard reads the workflow: either every report's line reaches
a step that keeps it, or the guide's two readings name where each is
taken; mutating the workflow's keep step reddens it.

## Outcome (round 167, 2026-10-03) — 🟢 Done

**Premise:** held — no step kept a pull request's `verdicts.tsv`, and
the kit wrote nothing for a plain build.

**Decision:** the kit and workflow do what the guide promised. The kit
appends one `builds.tsv` line per build (`captured`, `plain`,
`unready`; wall seconds; exit), and an `always()` step uploads both
`.tsv` files as the `bga-pilot-lines` artifact, pull requests included.
The cache stays off pull requests: a pull request's cache is scoped to
it and cannot feed main's band. Cheaper than rewording the guide to say
"read job durations off the CI log", which no file would hold.

### The gap, measured

```text
$ git show aa3435581:{examples/ci/bga-pilot.yml,examples/ci/bga-pilot.sh,docs/guides/pilot.md}  # base, restored after
$ pytest -q -p no:xdist tests/unit/test_a_pilot_kit_runs_report_only.py -k TestEveryReadingIsKept
FAILED ...::test_the_workflow_keeps_the_ledger_after_the_report_on_every_event[verdicts.tsv]
FAILED ...::test_the_workflow_keeps_the_ledger_after_the_report_on_every_event[builds.tsv]
FAILED ...::test_the_guide_names_where_the_readings_land
FAILED ...::test_every_build_writes_its_wall[captured|plain|unready]   (3)
6 failed
```

### After

```text
$ pytest -q -p no:xdist tests/unit/test_a_pilot_kit_runs_report_only.py
25 passed in 13.93s
builds.tsv after three captures (probe on the guard's `pilot`):
20261003T002757Z  review  default  captured  0  0
20261003T002757Z  review  default  plain     0  0
20261003T002757Z  review  default  unready   0  0
kept by: Keep this run's lines | always() | actions/upload-artifact@v4 | bga-pilot-lines
```

The guide's "What two weeks measure" names both files, their columns,
the artifact, and that each artifact repeats the cached lines
(`sort -u`). Wall is bash `SECONDS`, whole seconds.

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| B1 | upload step `if:` gains `&& github.event_name != 'pull_request'` | both ledgers, guide: 3 failed |
| B2 | `builds.tsv` dropped from the artifact `path` | `[builds.tsv]`: 1 failed |
| B3 | `upload-artifact` → `cache/save` | both ledgers, guide: 3 failed |
| B4 | plain branch's `ledger_build` call commented out | `[plain]`, `[unready]`: 2 failed |
| B5 | guide drops `` `bga-pilot-lines` `` | guide: 1 failed |

Green after each revert (25 passed). Under B1 and B3 the guide test
fails by finding no keeping step, so it adds no discrimination there.

### Deviation from the Required Fix

None.

```text
$ make lint
tools: pyright 1.1.414, ruff 0.16.9
```
