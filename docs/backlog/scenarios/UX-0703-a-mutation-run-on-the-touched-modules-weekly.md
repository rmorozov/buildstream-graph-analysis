# UX-703: a mutation run on the touched modules, weekly

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-524 (the touching map), UX-698 (the weekly workflow) | **Serves:** the falsify skill, which is a hand ritual per guard and cannot be run over the suite | **Topic:** guards

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
