# UX-1110: the width calibration runs on every pull request and gates nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** the jobserver line, whose reading keeps its schedule while PRs stop paying for it | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement | **Reading:** runner:bst-examples

**Guard:** none — named test_the_calibration_runs_off_the_pr_path.py, absent from tests/

## Motivation

`bst-examples`' step "Calibrate the runner's width and run the pinned 2x2
arm (UX-1004)" (`ci.yml:1808`) is a median **1,332 s** of the job's 2,064 s
(the ledger's spread for the job, 620-964s, predates it) and emits `::notice::` lines and a compare file; nothing reads it as a gate.
It is the largest non-gating cost in the pipeline, paid on every PR.

## Decomposition

Input classes: a `pull_request` event with and without the `jobserver` label; a push to main; a schedule; a dispatch.
Journey: the jobserver reading on `bst-examples` (`UX-1004`).

## Required Fix

The step runs on `workflow_dispatch`, on a weekly `schedule`, on push to
main, and on a pull request only when it carries a `jobserver` label. The
`::notice::` witness is unchanged where it runs.

## Out of Scope

What the calibration measures (`UX-1004`, `UX-1014`).

## Acceptance Test

`tests/unit/test_the_calibration_runs_off_the_pr_path.py` reads the step's
`if:` and asserts a plain `pull_request` event without the label does not
satisfy it and a push to main does. Mutation: drop the `if:`; it reddens.
