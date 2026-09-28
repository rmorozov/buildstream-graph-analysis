# UX-1093: the Enter-on-a-reached-fold journey fails intermittently on the older Pythons

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, main's run on `d7e74b1c` (#295) | **Serves:** every main run's matrix, and whoever reads a red one | **Topic:** guards | **Area:** bga/viewer | **Shape:** judgement

## Motivation

On `d7e74b1c` `test_a_keyboard_journey_reaches_every_chapter.py::TestEnterOpensTheFoldEnterReached::test_enter_on_a_reached_fold_opens_its_chapter`
failed on 3.9 and 3.11 with `assert None == 'change'` on
`chapterOpen`, while 3.10 and 3.12 passed and the next merge,
`814a2db8`, was green with the test unchanged. PRs run 3.12 alone
since `UX-995`, so an intermittent browser test is first seen on main.
`tests/flake_ledger.json` records the drift step's excursions only, so
nothing registered it.

## Required Fix

Find the race - the test reading `chapterOpen` before the page wrote
it, or the page opening the chapter off the event the test waits for -
and fix whichever side is wrong. "Flake" is not a cause.

## Out of Scope

A register of intermittent failures; retries.

## Acceptance Test

The test passes 200 repeated runs on this container, and the Outcome
names the race with the run that showed it. Mutation: reintroduce the
race, and repeated runs red.

## Outcome
