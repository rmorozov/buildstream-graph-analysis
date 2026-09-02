# UX-523: forty files boot the same page

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-336 (the parallel run these numbers are under), UX-359 (the page fixture every browser guard measures) | **Serves:** every `make test`; the implementing session's gate | **Topic:** guards

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured — and not where the filing put it

Three browser files, serial, `_drive`/`_launch`/`export_page`:

```text
DRIVES 70 in 112.3s (85.5 %) | LAUNCHES 3 in 1.0s (0.8 %) | EXPORTS 3 in 5.0s (3.8 %)
                                    88 passed, 1 skipped in 131.28s
```

The two cuts this item names are **4.6 %** between them. The seconds are
in the drives: 1.2s of each 1.6s drive was `SETTLE_FLOOR_MS`, `UX-482`'s
sleep beside the condition that replaced it, ~430 times a run.

### After

```text
                              before      after     cut
37 browser files, serial     629.14s    247.70s    2.54x
37 browser files, -n auto    192.77s    118.10s    1.63x
the three above, serial      131.28s     55.04s    2.39x
  of which drives      70 in 112.3s  70 in 39.8s
```

`537 passed, 3 skipped` both sides; the same 37 files each time.

### What the floor was covering

Two wrong answers first, both proxies for "the page has finished":
`#report || document.body` settles a **served** page on its static
skeleton while the payload fetches; `#report` alone settles on the
sections while `boot()` still wires the controls after them - five
guards red between them. So `boot()` says it, in a `finally` so the
failure page counts as finished.

### Mutations verified red and reverted (11)

| # | mutation | red |
|---|---|---|
| M1 | the 1,200ms floor comes back | 1 |
| M2 | an unbooted page counts as settled | 1 |
| M3 | the settle loop is gone | 1 |
| M4 | every open launches its own browser | 2 |
| M5 | the shared browser dies with its block | 1 |
| M6 | a dead browser is handed out anyway | 1 |
| M7 | nothing closes it at exit | 1 |
| M8 | the page never says it booted | 1 |
| M9 | the settle keys on `#report` again | 1 |
| M10 | a page drops its declaration | 1 |
| M11 | a module never stamps it | 1 |

M5 was green on its first writing: the guard reused the module's shared
browser, whose handle owns **no process**, so its `__exit__` is a no-op
whatever it says; from an empty `_SHARED` it discriminates. M6 found a
real defect while being written - `shared.process` is `None` after a
`_stop` and the reuse check read `.poll()` on it.

**M9-M11 are a third miss, found on round 80's merge.** The condition
asked for `#report`, `index.html`'s section; `perfetto.html` has none
and two `fetch`es, so the page whose whole state is what those fetches
found kept the heuristic - three clauses of
`test_one_page_behind_the_button.py` red under the suite, green alone.
A page **declares** it will speak now (`data-bga-boots`) and both entry
points stamp it.

### Deviation from the Required Fix

Two, both measured. **The export cache is not built**: 0.15-0.40s a
call, 3.8 % of the tier, against a key that would have to cover the
snapshot tree the caller is also given. **The shared browser lives in
`tests/browser.py`, not a `conftest.py` fixture**: thirty-eight files
construct `Browser(chrome)` directly, and reference-counting in
`__enter__` gets one browser in ten lines. Filed not fixed: `UX-537` -
forty-eight guards build their own `document`, none models
`documentElement`, hence the `?.`.

```text
=== 5910 passed, 27 skipped in 361.14s ===   ruff -> All checks passed!
```
