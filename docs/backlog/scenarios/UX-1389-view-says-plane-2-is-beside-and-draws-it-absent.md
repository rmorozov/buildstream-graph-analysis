# UX-1389: `bga view` says Plane 2 is beside the run, then draws it absent

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** walk seed 7 (2026-11-27) | **Serves:** R6, R3 | **Topic:** viewer | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_page_draws_the_plane_2_report_beside_the_run.py`

## Motivation

[`walk-seed-7.md`](../../audits/walk-seed-7.md) findings 2 and 3: on
`tests/fixtures/macro_micro/run` with its `plane2.json` beside it, `bga view run
--export e.html` prints "Plane 2 was captured — its report is beside this run —
but the raw trace log ... was not kept", and the page it writes says "Plane 2 was
not captured for this run, so there is no per-process detail". `bga analyze` and
`bga correlate` find that `plane2.json` unasked; `bga view` has no `--plane2`
and does not. A CI user reads two answers to one question.

## Decomposition

Input classes: Plane 2 report beside the run, given by flag, absent. Journey: extends the walk's seed 7 class.

## Required Fix

`bga view` reads the Plane 2 report the other commands find beside a run, or
its message stops saying one is there. Either way the stderr and the page agree.

## Out of Scope

Keeping the raw trace log for a timeline.

## Acceptance Test

On the fixture above, the export's planes census and its stderr agree on
Plane 2, and a mutation that drops the beside-the-run lookup reddens it.

## Outcome

Premise: falsified as filed. `bga view` already attaches the sibling (`_analyze_now` -> `plane2.attachable`, `UX-329`):
`bga view run --export e.html` on a copy of `tests/fixtures/macro_micro/run` with `plane2.json` beside it at `7e7b5db3`
gave `grep -c cc1plus e.html` 1 and census `{'plane2': True, 'trace': 'none'}`. The disagreement is real in one state:
an `analyze.json` stored beside the run before `plane2.json` arrived, which `view` serves as written.

Gap: that state (`bga analyze run --format json > analyze.json`, then `plane2.json` copied beside `run`, `bga view run --export v.html`)
-> `grep -c cc1plus v.html` 0, `grep -c "not captured for this run" v.html` 1, while stderr read "Plane 2 was captured — its report is beside this run".

Close: `served_analysis` in `tools/bga_view.py` drops a stored analysis whose `plane2_absence` is `NOT_CAPTURED` when `plane2.attachable(run)`
finds a report (`payloads` and `analysis_note` both call it); the same run -> `cc1plus` 1, "not captured for this run" 0.
`python3 -m pytest -q -p no:xdist tests/unit/test_the_page_draws_the_plane_2_report_beside_the_run.py` -> 2 passed.
`dev_sizes.py --check` named `tools/bga_view.py file_lines 2257 -> 2271`, adopted in a `sizes:` commit.

| mutation | reddened | count |
|---|---|---|
| `and plane2_shape.attachable(run)[0]` -> `and False` | `test_a_stored_analysis_without_plane_2_is_reanalysed_beside_a_report` | 1 failed, 1 passed |
| `(stored or {}).get("plane2_absence") == plane2_shape.NOT_CAPTURED and` -> `True and` | `test_a_stored_analysis_that_saw_plane_2_is_still_served` | 1 failed, 1 passed |
| reverted | — | 2 passed |

Review rework (2026-11-27): two gaps in `served_analysis`, measured by the two new tests against the pre-rework code
(`4 items: 2 failed, 2 passed`). (1) `bga analyze run --plane2 /elsewhere/report.json` stores `plane2_coverage` yet `plane2_absence == NOT_CAPTURED`
(it describes what sat beside `run/`); an empty report then placed beside `run/` made `payloads` drop it and lose `plane2_coverage`.
(2) a sibling `plane2.json` padded to `VIEW_MAX_BYTES + 1` made `attachable` return `(None, refusal)`; checking `[0]` alone served "not captured".
Close: a stored `plane2_coverage` keeps the analysis; a refusal replaces `plane2_absence` on a copy (the stored Plane 1 figures stay), worded by `attachable(run, stored=True)`: "this run's stored analysis was made without it", not "published no analysis", which a stored analysis contradicts.
Full file -> 4 passed; `dev_sizes.py --check` named `tools/bga_view.py file_lines 2271 -> 2276`, adopted in a `sizes:` commit.

| mutation | reddened | count |
|---|---|---|
| drop `or stored.get("plane2_coverage")` | `test_a_stored_analysis_that_joined_an_explicit_report_is_kept` | 1 failed, 3 passed |
| `return {**stored, "plane2_absence": refusal} if refusal else stored` -> `return stored` | `test_a_report_over_the_size_bound_is_named_not_called_absent` | 1 failed, 3 passed |
| `attachable(run, stored=True)` -> `attachable(run)` | `test_a_report_over_the_size_bound_is_named_not_called_absent` | 1 failed, 3 passed |
| reverted | — | 4 passed |
