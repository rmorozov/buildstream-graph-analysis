# UX-523: forty files boot the same page

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the parallel run these numbers are under), UX-359 (the page fixture every browser guard measures) | **Serves:** every `make test`; the implementing session's gate | **Topic:** guards

## Motivation

Where the suite's seconds go, read from CI's own reference:

```text
$ python3 - (tests/ci_reference.json, 400 files, 1,330 serial seconds)
browser-tier files              40    685 s   51 % of the suite
  median browser file                 15.4 s
top 12 files, all browser        432 s   32 %
files under 1 s                259     36 s    3 %
collection (5,897 tests)               12.5 s wall
```

Each browser file launches its own Chromium and runs its own
`bga view --export` through a module-scoped fixture
(`tests/browser.py`, `tests/pages.py::export_page`), so the *same*
golden page is exported and booted forty times per run — four times
per worker under `-n auto`, but forty exports. The guards are right
to measure the real page; they are wrong to each pay for it.

## Required Fix

- One export per fixture per session: `export_page` caches on
  (fixture, kwargs) under the session's tmp dir; the forty calls
  become as many distinct pages as there are distinct arguments
  (measure how many — the round expects fewer than ten).
- One Chromium per worker per session: the launch moves to a
  session-scoped fixture in `tests/conftest.py`; each file gets a
  fresh *tab* on the shared browser, which keeps the isolation the
  geometry guards rely on (a tab per file, a boot per test where a
  test mutates the page).
- Before/after, pasted: the browser tier's seconds serial and at
  `-n auto`, on this container and from CI's reference.

## Out of Scope

- Retiring or merging browser guards — a count of what they assert
  is a different task; this one changes what they cost, not what
  they hold.
- The tier floors — files that leave the large tier after this move
  where the measurement says (`UX-238`).

## Acceptance Test

`make test-large` before/after with the browser-tier seconds pasted;
the geometry, control and volume guards green unchanged; a mutation
in one file's page (a planted extra section) is seen by that file
only — the shared export is per fixture, not per suite.
