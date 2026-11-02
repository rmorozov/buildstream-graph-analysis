# UX-1367: an analysis written by an older bga is not served as the current one

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the walk of the freedesktop-sdk field-test branch (2026-10-30) | **Serves:** R1 | **Topic:** analysis | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`bga view /home/claude/fdsdk-cap/run` on the published capture serves the
capture's own `analyze.json`, written by bga 0.5.0 in the capture job, so
none of UX-1357..1366 appear and the status line still says "Plane 2 not
captured". Only `--reanalyse` shows the current tool's answer. A reader
of a published capture meets the old tool and cannot tell.

## Decomposition

Input classes: a run dir whose `analyze.json` carries an older `bga`
version; the same version; none.

## Required Fix

`bga view` (tools/bga_view.py) re-analyses, or says on the page which
bga wrote the analysis and offers `--reanalyse`, when the stored
analysis's version differs from the running one.

## Out of Scope

Migrating stored analyses.

## Acceptance Test

On a fixture whose `analyze.json` names an older version, the page
carries the current analysis or the version notice. Mutation: drop the
version check; the guard reds.
