# UX-1297: the pilot's workflow keeps no pull request's verdict, and its overhead control is in no file

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** review 36, checklist item 1 (2026-10-02) | **Serves:** R4 | **Topic:** docs | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome
