# UX-1092: a scenario declares its guard in one field, backfilled from the inferred column

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1000 | **Blocks:** — | **Found by:** round 149 — the first weekly retro, `docs/audits/retro-2026-09-28.md`, proposal 3; promotes the r140 `coverage` line on `tools/dev_area_pages.py` | **Serves:** whoever assesses an area's coverage, and every filing the `coverage` class comes from | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** test_every_task_declares_its_guard.py, test_an_area_page_names_each_guard.py

## Motivation

9 of the week's 15 bookkeeping lines are `coverage`: a guard that
reads nothing. The area pages read covered 366 of 567, 245 of those
inferred from Outcome prose, and every pass over the prose found a new
shape. A guard named in one field at filing makes both exact.

## Required Fix

A task header carries a `Guard:` field naming the test file(s), or
`none` with a reason. `dev_area_pages.py` reads the field and stops
inferring. Closed rows are backfilled from the inferred column, each
backfill checked against the file existing.

## Out of Scope

Judging whether a named guard is strong; a `Guard:` on progress-tracker rows.

## Acceptance Test

`dev_close_task.py --check` refuses a row with no `Guard:` field or one
naming a missing file, and the area pages read 0 inferred. Mutation:
drop one row's field, and the check reds.

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     `**Guard:** test_a.py, test_b.py` (or `**Guard:** none — <reason>`) on its own line 5
           of every task file; dev_area_pages.guard_files reads only it; dev_close_task --check gains
           guard_problems: no field, `none` without a reason, or a name absent under tests/ reds.
           The backfill is a one-shot script the integrator runs on the merged tip, never committed.
           At c324f250 over 1023 files: 177 declared, 452 inferred, 394 name nothing
Rejected:  the field inside the header line - --move/--shape rewrite it, so every backfill conflicts
           only ids >= 1092 - the page still reads 452 inferred
           a committed --backfill-guards mode - dead after one run; the Outcome records the command
           inference kept as a fallback - two sources of truth
Files:     tools/dev_area_pages.py (retire the Outcome/Decision inference); tools/dev_close_task.py;
           tests/unit/test_an_area_page_names_each_guard.py (retire the inferred fixtures);
           tests/unit/test_every_task_declares_its_guard.py (new); .claude/agents/implementer.md,
           docs/contributing/rules.md (the field at filing); docs/backlog/scenarios/UX-*.md (backfill:
           two dead names become `none — named <file>, absent from tests/`, 394 `none — no guard named at close`)
Guard:     the new file: check() refuses a sandboxed row with no field, `none` with no reason, or
           test_absent.py; area_page_body never prints "(inferred)" on the real tree
Mutation:  drop one row's field -> check reds; guard_files back on the Outcome -> 0-inferred reds;
           drop the presence lookup -> test_absent.py passes and the claim reds
Class:     bookkeeping; promotes the r140 coverage line; cap lifted for r149
Split:     A (implementer): tool, check, guard, script, run in the worktree only. B (integrator):
           re-run the script on the merged tip, --check 0 problems, --areas inferred 0, commit
Question:  none
```

## Outcome (round 149, 2026-09-28) — 🟢 Done

**Premise:** held — 452 of 1023 files carried a guard only in Outcome
prose and 393 named none; one field per file makes both exact.

### The gap, measured

```text
$ python3 old_dap.py (HEAD's dev_area_pages.guard_files over every task file)
{'declared': 178, 'inferred': 452, None: 393}
$ old area pages, summed:   covered 414 / 629 (declared 151, inferred 263)
$ python3 tools/dev_close_task.py --check      (new check, before the backfill)
  FAIL  every task file names its guard, and the guard exists (UX-1092) - 1023 problem(s)
1023 problem(s) over 9 propert(y/ies), 1023 backlog row(s)
```

Every file lacked the field; 263 of the pages' 414 covered rows rested on
prose the page could not tell from a citation.

### After

```text
$ python3 <scratchpad>/ux1092_backfill.py "$PWD"
backfilled 1022 file(s): {'named': 627, 'none-absent': 2, 'none-closed': 373, 'none-open': 20}
$ python3 <scratchpad>/ux1092_backfill.py "$PWD"    # again: git diff byte-identical
backfilled 0 file(s): {'named': 0, 'none-absent': 0, 'none-closed': 0, 'none-open': 0}
$ python3 tools/dev_close_task.py --check
  ok    every task file names its guard, and the guard exists (UX-1092)
0 problem(s) over 9 propert(y/ies), 1023 backlog row(s)
$ python3 tools/dev_area_pages.py --areas, summed: grep -c '(inferred)' -> 0
covered 415 / 629 (none 214, no line 0)
```

415 = 414 + this row (the old reader took `test_absent.py` from its
Decision). The two dead names are `test_the_workflow_runs_what_it_says.py`
and `test_absent.py`. The backfill is not committed with step A: the
integrator re-runs the script on the merged tip (step B).

### Mutations verified red and reverted (5)

| # | mutation | reddened |
|---|---|---|
| A | drop this row's `**Guard:**` line | 2 failed: `TestTheRealTree` both |
| B | `guard_files` falls back to the Outcome's backticked names | 4 failed: no-line cell, `covered 1 / 4`, outcome-only row, body `**Guard:**` |
| C | drop the presence lookup in `guard_problems` | 1 failed: `test_a_named_file_absent_from_tests` |
| D | drop the no-field refusal | 1 failed: `test_a_row_with_no_field` |
| E | accept `none` with no reason | 1 failed: `test_none_with_no_reason` |

Restored: 17 passed. Run from copies (`mutate.py`, `PYTHONDONTWRITEBYTECODE=1`).
`TestTheRealTree` is red on step A's commit alone (1023 problems) and
green once step B lands.
