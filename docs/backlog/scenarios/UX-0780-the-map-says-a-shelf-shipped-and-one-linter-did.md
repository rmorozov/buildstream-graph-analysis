# UX-780: the map says a shelf shipped, and one linter did

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-746 (which built this table and checked triggers, not contents) | **Serves:** the round pricing whether the analysis shelf exists before deciding to build it | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

The fixing guide's §6 map describes a workflow by what two tasks
intended, not by what the file does:

```console
$ sed -n '418,419p' docs/contributing/fixing-guide.md
.github/workflows/quality.yml               PR + weekly - the gate-only
                                            analysis shelf (UX-698/UX-699)
$ grep -c "^  [a-z-]*:$" .github/workflows/quality.yml
1
$ grep -A 3 "^jobs:" .github/workflows/quality.yml
jobs:
  eslint:
    runs-on: ubuntu-latest
$ head -3 docs/backlog/scenarios/UX-0698-*.md | tail -1 | cut -c1-46
**Priority:** High | **Status:** 🔴 Not Started
$ head -3 docs/backlog/scenarios/UX-0699-*.md | tail -1 | cut -c1-48
**Priority:** Medium | **Status:** 🟢 Done
```

One job: `eslint bga/viewer`, eighteen lines, which is `UX-699`.
`UX-698` — *the* gate-only shelf: code scanning, a lockfile and
`pip-audit`, Dependabot, secret scanning — has not started. The row
names both ids and describes the one that did not land.

`test_the_context_map_is_the_tree.py` passes (30 tests) and cannot
catch this: it asserts every mapped path exists and every path is
mapped, in both directions. The *description* beside the path is prose
no guard reads — which is the review's own shape, applied to a table
whose mechanical half is guarded and whose meaning half is not.

The cost is a decision: a round reading this map prices the analysis
shelf as done and skips `UX-698`.

## Required Fix

The row describes `quality.yml`, not `UX-698`'s ambition. Two changes,
and the second is the one that lasts:

1. Correct the row to what the file runs today, citing `UX-699` only.
2. Decide whether a map description can cite an **open** id at all.
   Citing one is how this happened: `(UX-698/UX-699)` reads as
   provenance and was written as intent. If a citation means "this row
   exists because of that row", an open id is legitimate and the
   description must still be true; if it means "that row built this",
   only closed ids belong. State the rule and let the guard read it —
   the map already knows every id's status through
   `dev_close_task.py`.

## Out of Scope

- Building `UX-698`'s shelf. That row is open on its own terms and
  this one does not touch its priority.
- The other ~102 map descriptions. Review 20 checked the CI-workflow
  block and the schema/skill/hook references; a full per-row sweep is
  `UX-689`'s, and its own Motivation already names the map as the
  growing part.

## Acceptance Test

Add a second job to `quality.yml` and watch the row's description
red, or point a row at an open id and watch the new rule red naming
it — whichever (1) or (2) lands.

## Outcome

_Not started._
