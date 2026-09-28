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

### The gap, measured

Not reproduced: the race is **inferred, not observed**. 145 fresh
loads, a per-Tab trace (tag, `data-toc`, `data-step`,
`data-toc-chapter`) of 40 Tabs each, found the first closed fold at
the same stop every time - fresh browser per load, measure-then-journey
on one target (race 2's shape), `taskset -c 0` beside busy loops, and
two processes concurrently:

```text
unloaded, one target   10 loads  {(11, 'change'): 10}
taskset -c 0, 2 busy   20 loads  {(11, 'change'): 20}
  + measure first      35 loads  11 change x35
two processes          80 loads  {(11, 'change'): 80}
stop 1-12: SELECT, BUTTON previous, BUTTON next, INPUT, BUTTON decide(open),
           A decision, A evidence, A overview, A findings, A headline, A next_steps,
           BUTTON change(closed)
```

CI's signature is reproduced by the Decision's mutation - one extra
stop in the Enter load only (`[data-step="top"]` unhidden) - on the
count replay: `assert None == 'change'`, focus on `A`. So the
failure is the count replay meeting a load with a different stop
count ahead of the fold; which of the Decision's races moved it on 3.9
and 3.11 this container did not show.

### The close, measured

The Enter load walks: Tab until focus is on the fold `journey` found
(cap `TAB_CAP`; later Tabs are swallowed), then Enter.

```text
$ REP=200 python3 -m pytest -p rep200 -p no:randomly -n 2 \
    tests/unit/test_a_keyboard_journey_reaches_every_chapter.py::TestEnterOpensTheFoldEnterReached
200 passed in 566.91s (0:09:26)
$ python3 -m pytest -n 0 tests/unit/test_a_keyboard_journey_reaches_every_chapter.py
9 passed in 50.14s
$ make lint
clean: 577 finding(s) match tests/quality_baseline.json
```

(`rep200` is a scratch plugin: an autouse fixture parametrised 200 ways.)

### Mutations verified red and reverted (4)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `[data-step="top"]` unhidden in the Enter load only, on the old count replay | `test_enter_on_a_reached_fold_opens_its_chapter` | 1 failed: `assert None == 'change'` (`A`) |
| M2 | M1 on the walk | - (holds) | 1 passed |
| M3 | the hold's `e.preventDefault()` removed | same | 1 failed: `the walk did not end on change's fold in 40 Tabs`, `assert None == 'change'` |
| M4 | the `Enter` step removed | same | 1 failed: `assert 'false' == 'true'` |
