# UX-1093: the Enter-on-a-reached-fold journey fails intermittently on the older Pythons

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, main's run on `d7e74b1c` (#295) | **Serves:** every main run's matrix, and whoever reads a red one | **Topic:** guards | **Area:** bga/viewer | **Shape:** mechanical

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

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     fix the test side: the fixture finds the fold at a Tab count in one load, and the
           test replays that count in a fresh load. Replace the replay with a walk in one session:
           Tab until the focused element's `data-toc-chapter` is the fold found (cap TAB_CAP),
           then Enter. First reproduce with a per-Tab trace (tag, data-toc, data-step,
           data-toc-chapter) of both loads and paste the diverging stop
Rejected:  a longer `{"wait": 100}` (:108) - a duration for a condition (fixing guide §5)
           a retry - Out of Scope
           a page-side fix - data-toc-chapter is written synchronously before bgaBooted
Files:     tests/unit/test_a_keyboard_journey_reaches_every_chapter.py; tests/cdp.mjs only if
           the reproduction shows race 2
Guard:     the same test: the fold reached by Tab alone reads data-open "false" before Enter
           and "true" after
Mutation:  one extra Tab stop after boot in the fresh load only (e.g. unhide [data-step="top"]):
           the count replay reds with `assert None == 'change'`, the walk holds; revert the walk
           and it reds
Class:     product - holds UX-1016's keyboard claim; one red main matrix so far, rate unmeasured
Split:     one track, implementer on opus (UX-1039)
Question:  none
Races:     1 (likely) the Tab-stop count ahead of the fold differs between loads: the current
           rail row hides other rows' .sections links (style.css:892) and scrollspy moves it
           asynchronously (nav.js:792, 818-825); the Top button's hidden state follows scrollY
           (nav.js:700-703). 2 cdp.mjs:238 may read the previous document's bgaBooted
           (app.js:1170) on the reused target (browser.py:237). Not reproduced in 28 runs;
           try taskset -c 0 with busy loops, -p no:randomly, 200 runs
```

## Outcome
