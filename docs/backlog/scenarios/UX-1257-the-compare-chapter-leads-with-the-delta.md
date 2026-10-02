# UX-1257: "What changed since last time?" has an empty lead, and the first screen never says the delta

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-162 view UI review on a 2,402-element two-plane page (2026-10-01), brainstorm B5, filed at Ruslan's request | **Serves:** R4, R7, R8 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_compare_chapter_leads_with_the_delta.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 40 --width 60 --workload binaries` (2,402 elements), `bga capture report --json plane2.log --project-dir <d> > plane2.json` in the newest snapshot (39,854 processes, 601 binaries), served by `bga view @last` on main `050d9035`, Chromium 1440x900 and 390x844 (view UI review, round 162, `view-ui-review/round-162/review.md` §B5).

Every chapter has a one-line lead except `#chapter-compare`, whose lead is empty. The run picker knows @prev was 2,832.2 s and @last 2,829.8 s, and the culprits table says "1,212 grew, 1,178 shrank, 12 unchanged", but neither the chapter head nor the first screen says "-0.1%, inside the noise band". For the gatekeeper and the lead, that sentence is the first thing they read.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

Architect, round 163 (2026-10-01):

```text
Route:     compare.py publishes the wall delta % (additive in compare/v2); one exported compareLead(comparison) in chapters.js builds "−0.1% (2.4 s faster) than @prev, inside the noise band" from verdict_kind; app.js passes compare.json to chapters(); decision.js draws the same sentence; one snapshot: one absence sentence in the panel, chapter absent.
Rejected:  viewer dividing delta by baseline (Direction 7); two sentence builders.
Files:     bga/compare.py, bga/schemas.py, bga/viewer/chapters.js, bga/viewer/app.js, bga/viewer/decision.js, tests/unit/test_the_compare_chapter_leads_with_the_delta.py
Guard:     two_plane_run(runs=2): compare lead == decision sentence, carries % and verdict; runs=1 one absence sentence.
Mutation:  compare answer returns null; remove the decision call.
Class:     product
```

## Required Fix

The compare chapter's lead is the wall delta against the baseline with its noise-band verdict; the decision panel shows the same sentence when a baseline exists.

## Out of Scope

The comparison itself; runs with no baseline, which say so in one sentence.

## Acceptance Test

On this page the compare lead reads the delta and its verdict, and the decision panel shows the same sentence; a single-snapshot store reads one absence sentence. Mutation: empty the lead, and the guard reds.

## Outcome

The gap measured, at `9b55e0d4`, the Motivation's page (`two_plane_run(shape=(--layers 40 --width 60 --workload
binaries), runs=2)`, exported in place, Chromium): `{'chapter': True, 'lead': [], 'panel': [], 'absent': 0}` - the
old `answer` read `payload.comparison`, which `analyze/v5` never carries.

The close measured, same page: `{'chapter': True, 'lead': ['-0.1% (2.5 s faster) than the run before, inside the
noise band.'], 'panel': [<the same sentence>], 'absent': 0}`. `--layers 8 --width 14`: `-1.8% (2.4 s faster) than
the run before, outside the noise band: improved.` in both. One snapshot: no `#chapter-compare`, panel `No earlier run
to compare against.`, once. `compare/v2` gains `total_duration_delta_share` (always written, `null` with no baseline
total). Page half: macro_micro 160,033 -> 160,409 B; the 2,402-element page 160,035 -> 160,411 B (of 165,000).
Guard: 3 passed (3.9 s); with the compare, schema, chapters, said-once and attach guards 230 passed, 2 skipped.

| mutation | reddened | run printed |
|---|---|---|
| `compareLead` returns `null` | `test_the_lead_is_the_delta_and_the_panel_says_it_too` | 1 failed, 2 passed |
| drop the decision panel's `section.append(... compare-lead ...)` | both browser tests | 2 failed, 1 passed |
| `_delta_share` returns `None` | the lead test, `test_compare_publishes_the_delta_as_a_share_of_the_baseline` | 2 failed, 1 passed |
| reverted | | 3 passed |

Verifier fix: `test_the_sign_and_the_verdict_word_are_the_comparisons` runs `compareLead` under node on a constructed
slower-regressed and faster-inside-band comparison; `cli.md` names `total_duration_delta_share` (surface 609 keys).

| mutation | reddened | run printed |
|---|---|---|
| `delta < 0` -> `delta > 0` in `compareLead` | both constructed cases | 2 failed, 3 passed |
| `regressed` reads `...: improved` | `[slower-regressed]` | 1 failed, 4 passed |
| reverted | | 5 passed |

Round 163 merge: `test_each_sentence_is_drawn_once.py` has no exemption, so the panel no longer repeats the
lead; it draws the delta clause (`compareDelta`) as a link to `#chapter-compare`, and the guard pins that.
