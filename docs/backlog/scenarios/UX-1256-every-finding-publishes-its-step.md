# UX-1256: findings publish facts, and the steps live only in attribution hints and next steps

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B4, filed at Ruslan's request | **Serves:** R1, R8 | **Topic:** analysis | **Area:** bga | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B4).

A finding publishes `id, severity, title, detail, elements, evidence, reader, copy_text, trace_query(ies)`: no step. The steps exist elsewhere: `attribution_hints.resource_wait_us` says "try --capacity N with a higher N, or `bga sweep`", and `next_steps` carries runnable commands. The High finding "92.6% of wall-clock time is resource wait" reaches the reader without the step its own category already has.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     `_finding()` takes `step` as required keyword, no default: `{text, command?}` or `{why_none}` — omission is a TypeError. Steps from resolve_attribution_hint / _plane2_capacity_hint and next steps; render_findings prints it under the title; schema declares findings[].step.
Rejected:  defaulted step=None plus a guard (mechanism before guard); copying next_steps wholesale.
Files:     bga/findings.py (_finding :377, 43 calls, _opportunity_findings :1502, render_findings :2680), bga/schemas.py findings item (:4419). Retire wait-category's evidence.hint and "-> hint" detail line.
Guard:     tests/unit/test_every_finding_publishes_its_step.py — golden, macro_micro: every Medium+ finding has step.text, wait-category's step equals the resolved hint, schema declares step.
Mutation:  step={'why_none':...} on wait-category.
Class:     product
Split:     one track, first; backbone for 1248, 1249, 1255.
```

## Required Fix

Each finding publishes a `step` (a sentence, and a command where one exists) from the same sources the hints and next steps use, or says why it has none; the text report prints it under the finding. The viewer side is UX-1249.

## Out of Scope

Drawing the step on the page (UX-1249); which findings exist.

## Acceptance Test

On this page every finding at Medium or above carries a step, and `wait-category`'s step equals the resource-wait hint; the schema declares the field. Mutation: drop the field from one finding, and the guard reds.
