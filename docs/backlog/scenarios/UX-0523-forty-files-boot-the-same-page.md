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

Three browser files, serial, `_drive`/`_launch`/`export_page` counted:

```text
DRIVES 70 in 112.3s (85.5 %) | LAUNCHES 3 in 1.0s (0.8 %) | EXPORTS 3 in 5.0s (3.8 %)
                                    88 passed, 1 skipped in 131.28s
```

The two cuts this item names are **4.6 %** between them. The seconds
are in the drives, and 1.2s of each 1.6s drive was `SETTLE_FLOOR_MS` -
the sleep `UX-482` left beside the condition that replaced it, "so
nothing observes earlier than it used to". ~430 drives a run.

### After

```text
                                    before      after     cut
37 browser files, serial           629.14s    247.70s    2.54x
37 browser files, -n auto          192.77s    118.10s    1.63x
the three above, serial            131.28s     55.04s    2.39x
  of which drives            70 in 112.3s  70 in 39.8s
```

`537 passed, 3 skipped` on both sides. Not `make test-large`
before/after: a fresh worktree has no staged `examples/`, so 32 of its
528 items skip there. These 37 files are the same set on both.

### What the floor was covering

Two wrong answers before the right one. `#report || document.body`
stops changing settles a **served** page on its static skeleton while
the payload is fetching (three run-switching guards, two handoff
guards, red); `#report` alone, non-empty and stable, settles on the
sections while `boot()` is still wiring the controls after them (the
same two handoff guards, red again). Both are proxies for "the page has
finished", so `boot()` says it - `data-bga-booted`, in a `finally` so
the failure page counts as finished - and the driver waits for that. A
page with no `#report` has no `boot()` and settles on `body` as
before.

### Mutations verified red and reverted (8)

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

M5 was green on its first writing: the guard reused the module's
shared browser, whose handle owns **no process**, so its `__exit__` is
a no-op whatever it says. From an empty `_SHARED` it discriminates. M6
found a real defect while being written - `shared.process` is `None`
after a `_stop`, and the reuse check read `.poll()` on it.

### Deviation from the Required Fix

Two, both measured. **The export cache is not built**: 0.15-0.40s a
call, 3.8 % of the tier, against a key that would have to cover the
snapshot tree the caller is also given. **The shared browser lives in
`tests/browser.py`, not a `conftest.py` fixture**: thirty-eight files
construct `Browser(chrome)` directly, and reference-counting inside
`__enter__` gets the same one browser in ten lines rather than
thirty-eight files.

Filed rather than fixed: `UX-537` - forty-eight guard files build their
own `document`, none models `documentElement`, and that is why the
marker is written through `?.`.

```text
=== 5910 passed, 27 skipped, 1 warning in 361.14s (0:06:01) ===
ruff check bga/ tools/ tests/ .claude/hooks/   ->  All checks passed!
```
