# UX-1348: bga supports Python 3.12, 3.13 and 3.14 only

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1346 | **Found by:** Ruslan, dropping end-of-life Pythons (2026-10-08) | **Serves:** R8 | **Topic:** guards | **Area:** tests | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_pull_request_runs_the_newest_python_only.py`, `tests/unit/test_the_python_floor_is_a_guard.py`, `tests/unit/test_a_run_red_for_another_reason_adopts_nothing.py`

## Motivation

`requires-python = ">=3.9"`, classifiers 3.9-3.12, CI push matrix
`["3.9","3.10","3.11","3.12"]`. 3.9 is past end of life; Ubuntu 24.04
LTS ships 3.12 and BuildStream 2.8.1 runs 3.10-3.14. 3.13 and 3.14 were
never run: on 3.13 three files stack `@classmethod` on `@pytest.fixture`,
which 3.13's removal of classmethod descriptor chaining breaks.

## Required Fix

`requires-python = ">=3.12"`, classifiers 3.12-3.14, the `UX-1340`
hypothesis marker split collapsed to one pin. CI: pull request
`["3.12"]` (the primary cell, now also the floor), push
`["3.12","3.13","3.14"]`; the coverage/touching-map role 3.11 -> 3.13,
the plain `Test` step then 3.14; `clean_312/313/314`; every non-matrix
`setup-python` 3.11 -> 3.12. The four fixtures take `self`. Every guard
encoding the old range follows; a guard holds that no test stacks
`@classmethod` on a fixture. The four 3.14-only reds the first run
found are fixed where they are tests' own (below).

## Out of Scope

Raising ruff `target-version = "py39"` and pyright `pythonVersion =
"3.9"`: `ruff check --target-version py312 --statistics .` reads ~1,174
mechanical findings, a follow-up row. Retiring the `<3.11` `tomllib`
fallbacks and `UX-1346`'s length-assert-then-`zip` sites, now dead.
`python -m bga.cli extract --help` prints `usage: python -m bga.cli` on
3.14 (argparse names `prog` off `__main__.__spec__` before `sys.argv[0]`);
the `bga` console script still prints `bga extract`.

## Acceptance Test

The full suite on 3.12, 3.13 and 3.14 in this container, each a fresh
venv off `requirements.lock`, red only where it is red at the base.

## Outcome (2026-10-08) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ venv3.13/bin/python -m pytest -q -n 4 tests/unit/test_the_mapping_is_law.py \
    tests/unit/test_the_page_has_a_reader.py tests/unit/test_the_palette_is_validated.py   # at 5d25bb79
======================== 96 passed, 16 errors in 10.31s ========================
E  fixture 'probed' not found   (also 'shaped', 'rendered')
```

### After

```text
$ venvX/bin/pip install -r requirements.lock      # rc=0 on 3.12.3, 3.13.16, 3.14.6
$ venv3.12/bin/python -m pytest -q -n 4
==== 8 failed, 12587 passed, 214 skipped, 14 warnings in 909.30s (0:15:09) =====
$ venv3.13/bin/python -m pytest -q -n 4
==== 8 failed, 12587 passed, 214 skipped, 14 warnings in 987.50s (0:16:27) =====
$ venv3.14/bin/python -m pytest -q -n 4
==== 8 failed, 12587 passed, 214 skipped, 13 warnings in 859.93s (0:14:19) =====
```

First run, 3.14 alone, four more reds - each a 3.14 change, fixed in the test:

| test | 3.14 change | fix |
|---|---|---|
| `test_grace_window_drains` closing summary | a SIGINT landing before one `time.sleep(60)` is held until it returns: 5 of 24 red at `-P 8`, 0 of 24 on 3.12 | the fake `bst` sleeps 0.05s x 1200: 0 of 24 |
| `test_the_timeline_speaks_perfetto` streaming | `gzip` buffers writes: first bytes at slice 29,227 (3.12: 2,830) | a distinct argv per slice, read after 20,000: first bytes at 11,806 |
| `test_tools_dispatch` x2 | argparse's `prog` is `python -m <module>` under `-m` | the alias runs the console script's body; the direct run matches `bst_extract_run` |

`test_six_seams_round_21_found` was red at `5d25bb79` on every Python:
`UX-1347`'s module-scope `importorskip("tomllib")`, now a plain import.

The 8 reds left, identical on all three, are 390px browser layout in this
container's Chromium: `test_a_heading_is_its_question_alone` x3
(also red at `5d25bb79` on 3.12), `test_pointer_travel_is_a_budget`
J1/J4, `test_the_narrow_page_keeps_its_place` big-*-steps x3.

### Mutations verified red and reverted (9)

| # | mutation | reddened |
|---|---|---|
| M1 | `@classmethod` back on `shaped` | `test_no_fixture_is_a_classmethod` |
| M2 | PR matrix `["3.14"]` | `..._primary_cell_and_the_floor_alone`, `..._moves_to_the_cell_it_keeps` |
| M3 | `requires-python = ">=3.13"` | `..._primary_cell_and_the_floor_alone` |
| M4 | `full_match` row dropped | `test_the_table_still_reaches_past_the_floor` |
| M5 | `clean_314` dropped from `flake-ledger-adopt` | `adopts_nothing[one-suite-3.14]` |
| M6 | coverage step on 3.12 | `..._off_the_timing_interpreter`, `..._one_make_test_step_holds_per_event_and_cell` |
| M7 | plain `Test` step also excludes 3.14 | `..._one_make_test_step_holds_per_event_and_cell` |
| P1 | `TrackEventWriter` holds every packet until `close` | `test_the_bytes_are_on_disk_before_the_writer_is_closed`, 3.12 and 3.14 |
| D1 | dispatcher keeps `sys.argv[0]` | `test_the_alias_reaches_the_tool_through_the_real_cli`, `test_usage_names_what_the_user_typed` |

M5 was green under `one-suite` on `CELLS[0]` alone; the case now runs per cell.
