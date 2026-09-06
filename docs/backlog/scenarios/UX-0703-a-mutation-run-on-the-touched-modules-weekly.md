# UX-703: a mutation run on the touched modules, weekly

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-524 (the touching map), UX-698 (the weekly workflow) | **Serves:** the falsify skill, which is a hand ritual per guard and cannot be run over the suite | **Topic:** guards | **Area:** unassigned | **Shape:** bounded

## Motivation

`falsify` mutates one guard by hand and pastes the red. The reverse
question — which module can change without any guard going red — has
never been asked of the whole tree; `REVIEW.md` calls a guard nobody
falsified "a guard nobody knows can fail", and 7,206 tests hold 104
modules with no number for how many would notice. Full mutation over
62k lines is hours; over the week's touched modules, with the
touching map choosing the tests, it is minutes.

## Required Fix

`mutmut` in `quality.yml`'s weekly schedule: the modules touched since
the last run (`git diff --name-only`), the tests `dev_touching.select`
names for them, `--max-children` the runner's cores; the survivors
land in a ledger table in `docs/audits/mutation.md` with the module,
the mutant and the guard that should have caught it. A survivor is a
filing, not a failure — the run never blocks.

## Out of Scope

- Blocking on a score — a percentage is a ratio at the noise floor
  when the week touched one module.
- Browser guards — a mutant that boots the page 36 times is the
  round-79 cost again; Python modules only.

## Acceptance Test

One weekly run's table in `docs/audits/mutation.md` with at least one
survivor named; mutation of the instrument: delete a guard the map
names for a touched module — the survivor count for that module rises
in the next run's row.

## Outcome

**The gap, measured.** `python3 tools/dev_mutation.py --module
tools/dev_track_cost.py --max-children 4` (401 lines, 3 guard files,
32 tests, 0.48 s to run them all): **392 survivors**, grouped by
function, e.g. `x_report` (no tests x46) — `main`/`report` never
exercised by a unit guard at all, exactly "no number for how many
would notice".

**The close, measured.** `tools/dev_mutation.py`: touched modules from
`dev_touching.changed_files`, guards from
`dev_touching.naming(*dev_touching.select([module]))`, `mutmut`
scoped via a temporary `[tool.mutmut]` block (restored after every
run) with `source_paths` widened to the whole tree — a guard reads
paths relative to its own file's parents, and `mutmut`'s copy is one
directory deeper, so a narrower copy fails for a reason that is not
the mutation. Acceptance case, `tools/dev_page_census.py` (2 guard
files, 50 mutants): baseline **4 killed / 46 survivors**; guard file
`test_a_new_control_class_lands_declared.py` removed — `mutmut`
reports "Stopping early, because we could not find any test case for
any mutant" (zero coverage), and the tool counts every un-verdicted
mutant as a survivor rather than dropping it: **50/50 survivors**, the
count rising as required.

**Mutations** (`tests/unit/test_the_weekly_mutation_run_names_its_survivors.py`):

| mutation | reddened | count |
|---|---|---|
| dropped the `not startswith("test_")` filter | `test_touched_modules_keeps_only_bga_and_tools_python_source` | 1 failed |
| `_function()` returns the mutant id unchanged (no grouping) | `test_render_row_groups_by_function_not_by_mutation_site` | 1 failed, 3 rows vs 2 |
| "no test names this module" reworded | `test_no_guard_naming_the_module_is_its_own_row` | 1 failed |
| ledger opened `"w"` instead of `"a"` | `test_write_ledger_appends_a_new_dated_section` | 1 failed |

All four reverted from the pre-mutation copy; full file green after
each (`4 passed`).
