# UX-1349: browser tests are 59% of CI's test seconds, against UX-690's 40%

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** main's first clean push run after UX-1348, run 37943350480 attempt 2 on `216fcc30` (2026-10-09) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** mechanical | **Reading:** runner:test

**Guard:** `tests/unit/test_the_suite_holds_its_shape_budget.py::test_the_browser_row_holds_the_ledger`

## Motivation

The CI reference adopts only from a push run whose every cell is clean,
and the 3.9 cell was red 2026-09-29..10-09 (UX-1340), so the reference
sat still for ten days. Its first refresh, `records` `3f75d927`:

```text
$ python3 tools/dev_shape_budget.py      # reference 2d88ac2f -> 3f75d927
browser   642 s -> 1862 s of 3142 s total
browser budget: 59.3% measured, 40% the Required Fix states, 51.2% the ledger holds
```

The growth is new browser files, led by
`test_the_narrow_page_keeps_its_place.py` (131 s),
`test_an_element_view_answers_whole.py` (52 s),
`test_the_builder_sweep_is_drawn.py` (51 s). The owner adopted 59.3% on
2026-10-10 to turn main green, and asked for this row to cut it back.

## Required Fix

Bring the browser share back toward 40% without dropping a claim: share
one page build per fixture across browser files, or move a geometry check
that needs no layout to the DOM shim. Re-adopt the ledger at the new share.

## Decision

Route:     Build each page once per test session and share it. In `tests/pages.py`, `export_uri` (store=False, no kwargs) and a new `two_plane_uri(shape=(), runs=2, name="both")` build under `$TMPDIR/bga-pages-<PYTEST_XDIST_TESTRUNUID or pid>/<sha256 of kind+fixture/shape+runs+name>`, each build into `.tmp-<pid>` then `os.rename`d into place (a racing worker's build is thrown away); both return the shared URI and write nothing into `into`. `export_page` stays uncached for callers that read `into`. Browser call sites doing `view.export(str(pages.two_plane_run(...)), page)` and using only the URI move to `two_plane_uri`. Measured on the 4-core container at d13ab454 (150 browser files, `-n 4`): 1823 passed, 659 s wall, 2538 junit s; 302 exports of 2 distinct pages cost 166 s, 67 store-run exports 404 s (`("--layers","20","--width","60")` at 15 sites).
Rejected:  moving layout-free checks to the DOM shim: the larger cost (559 Chrome drives, 971 s) but a per-test judgement over ~150 files that three arms cannot take from one brief; a follow-up row.
Rejected:  sharing only `pages.pages()`: 30 of 142 sites, no store-run exports.
Files:     `tests/pages.py` (`_shared`, cached `export_uri`, `two_plane_uri`); `tests/conftest.py` (`pytest_sessionfinish` on the controller only, `not hasattr(config, "workerinput")`, removes the cache root); the browser `tests/unit/test_*.py` whose `two_plane_run`+`view.export` result is used only as a URI (`grep -rn "pages.two_plane_run(" tests/unit`); any `export_uri` caller reading `into` afterwards switches to `export_page`; `tests/unit/test_a_page_is_built_once_per_session.py` (new). `tests/shape_ledger.json` is not written here.
Guard:     `tests/unit/test_a_page_is_built_once_per_session.py`, `tools.bga_view.export` wrapped in a counter, cache root on a fresh monkeypatched id: (1) `export_uri(golden, d1)` and `(golden, d2)` return one URI with exports == 1, same for `two_plane_uri(SHAPE)` twice; (2) golden vs macro_micro, and two shapes, give different URIs with exports == 2; (3) the shared page's text equals a fresh `export_page` of the same fixture once the run_dir path is swapped. `test_the_guards_measure_the_page.py` stays green.
Mutation:  (a) `_shared` always builds: (1) reddens; (b) the key drops fixture or shape: (2) reddens; (c) `_shared` builds `FIXTURES["golden"]` whatever is asked: (3) reddens.
Class:     optimization: cuts CI test seconds, 166 s + 404 s of 2538 browser junit s shareable. ~220 lines; the round's over-150-lines row.
Split:     one track. Container close: the same before/after command, `PYTHONPATH=. python3 -m pytest -n 4 -p no:cacheprovider --junitxml=R <browser files from dev_shape_budget.shapes()["browser"]>` summed with `dev_tier_drift.measured(R)` (baseline 2538 s, 659 s wall). CI only: the share on a refreshed `tests/ci_reference.json`, and `--adopt` of `tests/shape_ledger.json` after that refresh.
Question:  this route alone projects to ~52-54%, not 45%; reaching 45% needs the shim route too. Default taken (2026-10-10, round 173): this row closes on "the browser seconds fall, measured, and the ledger re-adopts lower after CI's refresh"; the shim route is filed as its own row.

## Out of Scope

Skipping, quarantining or deleting a browser test; changing the 40% target.

## Acceptance Test

`python3 tools/dev_shape_budget.py` on a CI reference adopted after the fix
reads the browser share at or under 45%, with every browser test still run.

## Outcome

**Gap measured** (b1323876, 150 browser files from `dev_shape_budget.shapes()["browser"]`, `-n 2` — the container is shared, load average 20-28 on 4 cores):

```text
$ PYTHONPATH=. python3 -m pytest -n 2 -p no:cacheprovider --junitxml=before.xml <150 files>
1 failed, 1822 passed, 16 skipped in 3455.03s      # the failure: narrow_rail_jump_box[jump], y 6691 != 6000, on the base
before junit s: 6591.7                              # dev_tier_drift.measured summed
```

**Close measured** (this branch, same command, same files):

```text
2 failed, 1821 passed, 16 skipped in 2705.15s      # taken while test_the_header_keeps_its_budget (1 of the 2) was failing: it read `into`; fixed after; rerun `pytest -n 2 tests/unit/test_the_header_keeps_its_budget.py` 9 passed in 17.07s
after junit s: 5192.2                               # -1399.5 s (-21%) junit, -750 s (-22%) wall
```

The share on a refreshed `tests/ci_reference.json` and the ledger `--adopt` are CI's, after merge.

**Mutation table** (`tests/unit/test_a_page_is_built_once_per_session.py`, 5 tests; three more fixtures moved to `two_plane_uri`):

| mutation | reddened | run printed |
|---|---|---|
| (a) `_shared` always builds (`if done.is_dir()` -> `if False`) | `test_one_fixture_is_exported_once`, `test_one_shape_is_exported_once` | 2 failed, 3 passed |
| (b) key drops fixture and shape | `test_another_fixture_or_shape_is_another_page` | 1 failed, 4 passed |
| (c) `export_uri` builds `FIXTURES["golden"]` whatever is asked | `test_the_shared_page_is_the_fresh_page[macro_micro]` | 1 failed, 4 passed |
| reverted from copy | — | 5 passed |
| (d) controller `rmtree(cache_root())` -> `pass` (`test_the_page_cache_does_not_outlive_an_xdist_session`, `-n 2` subprocess, private TMPDIR, ~6-10 s) | its one test | 1 failed |
| (e) `pytest_configure` uid propagation -> `pass` | same | 1 failed |
| reverted from copy | — | 25 passed (moved files, both guard files, header file) |
