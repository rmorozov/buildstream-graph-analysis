# UX-1121: timing gates red pull requests for the runner's speed

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29); Ruslan took it on the audit thread (2026-09-29 06:09) | **Serves:** the implementing session, whose PR reds for a file it never touched | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** runner:test

**Guard:** none — named test_a_timing_gate_reports_on_a_pr.py, absent from tests/

## Motivation

Two steps of `test (3.12)` judge seconds, not behaviour: "Tiers match CI's
own record of them" (`ci.yml:308`) and "The analyzer's wall clock and RSS,
against CI's own record" (`ci.yml:467`). Over 400 runs the tier gate failed
14, with the adopt jobs another 15; project memory records reds on files the
branch never touched and green runs that are not evidence a cost went away.
A shared runner makes a timing verdict per PR a noise source.

## Required Fix

Both steps stop failing the PR: they report (a `::notice::` naming file and
ratio) and upload their candidate as today. A scheduled workflow on `main`
(daily) reads the carried readings and, when a file or the analyzer holds
over its gate on two consecutive scheduled runs, fails and names it for a
row. The PR keeps a per-test hang ceiling (`UX-1111`).

## Out of Scope

The gate's thresholds; the adopt jobs.

## Acceptance Test

`tests/unit/test_a_timing_gate_reports_on_a_pr.py` reads both steps and
asserts neither can fail a `pull_request` run, and that the scheduled
workflow runs both checks with a two-run rule. Mutation: restore the PR
failure; it reddens.
