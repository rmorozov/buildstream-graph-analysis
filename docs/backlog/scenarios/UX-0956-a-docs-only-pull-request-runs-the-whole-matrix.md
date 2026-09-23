# UX-956: a docs-only pull request runs the whole matrix, and the selector that could narrow it misses the guards that read documents by glob

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-522, UX-943 | **Blocks:** — | **Found by:** round 138 — Ruslan, 2026-09-23: "for docs only changes i also propose making lighter ci gate" | **Serves:** every docs-only pull request, which waits on four interpreters and three `bst` jobs | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

Every pull request runs `test` on four Pythons, then `bst-smoke`,
`bst-tests` and `bst-examples`, whatever it touches. A diff that
touches only `docs/**` or `*.md` cannot change what those jobs build,
but it can redden many guards: derived counts, the spread figure, the
register, links, the round register. So a lighter lane has to be a
derived set, not a hand list.

`tools/dev_touching.py` is the nearest selector: grep over the changed
path, plus `tests/tiers.py`'s CENSUS. A guard that globs a docs
directory (`SCENARIOS.glob("UX-*.md")`) names no single file, so a
per-file grep cannot select it unless it is census, and census is
defined against source modules, not documents.

## Required Fix

A docs-only detector in `ci.yml` that the heavy jobs skip on with a
job-level `if:`, a one-Python lane that runs the lint, the index check
and a derived test set, and a guard that reddens when a test reads
documents and the lane would not select it. New logic lives in new
modules; pushes to `main` always run the full workflow; a lane run
adopts nothing.

## Out of Scope

Narrowing `dev_touching`'s own grep (`README.md` as a bare-name token
selects every test naming any README). `UX-942`'s selector gap through
a tool's constant. Required-check settings on GitHub, which only the
owner can change.

## Acceptance Test

`tests/unit/test_a_docs_only_diff_runs_its_guards.py` green, and red
under three mutations: a glob-reading doc test dropped from the derived
set, `bst-examples`' `if:` removed, a `.py` path counted as docs.

## Outcome

**Round 138, 2026-09-23**

The gap, on a one-task-file diff and on a guide, with `dev_touching.select`
(scratch `measure2.py`, tree at this branch):

```text
diff                  select   missed by select (of five worked readers)
UX-0955 task file     31       pasted_guide_block, documentation_debt,
                               every_task_names_its_area,
                               documented_invocations, premise
docs/guides/cli.md    55       the same four without pasted_guide_block
#171 (9 docs paths)   70       (README.md's bare name reached most)
```

The close. Both tools read `git diff --name-only <base>` on stdin.
`tools/dev_docs_only.py` (stdlib only, so the `changes` job needs no
install) prints `docs_only=true` only for a `pull_request` whose every
path is under `docs/` or ends `.md` outside `tests/`; a push, or an
empty list - what a failed `git diff` leaves - is `false`.
`tools/dev_docs_lane.py` runs `select(diff)` plus `doc_readers()`,
derived from each test's AST: a walk or `git ls-files` reaching a docs
constant through the scope's bindings, or a reference to a `bga/`,
`tools/` or `tests/` helper function that does, closed across modules
(`dev_scenario.audits_documents` reaches docs through
`dev_finding_coverage.tracked_paths`).

```text
doc_readers()                    62 test files, 41 outside CENSUS
lane, UX-0955 task file          31 -> 72
lane, docs/guides/cli.md         55 -> 91
lane, #171's diff                70 (71 once this guard names README.md) -> 97
#171 lane, -n auto, this box     2862 passed, 5 skipped: 101.0 s at load 3.7;
                                 96 files, 180.5 s at load 6.2 earlier
```

Two of the 97 are large-tier (`test_the_page_has_a_volume_budget.py`,
`test_the_vocabulary_has_the_shape.py`): both name `styleguide.md`,
which #171 touched, so the lane keeps them.

`ci.yml`: a `changes` job; `test`, `bst-smoke`, `bst-tests`,
`bst-examples` carry `if: needs.changes.outputs.docs_only != 'true'`;
`docs-lane` runs on 3.11: `make check-clean`, `make lint`,
`dev_close_task.py --check`, `dev_docs_lane.py --run`. The spread
figure is checked by `test_the_cost_row_is_derived_from_the_selector.py`,
which is CENSUS, so the lane runs it. Every job with `contents: write`
already requires `github.event_name == 'push'`, and `docs_only` is
`false` on a push, so a lane run adopts nothing; the guard asserts it.

```text
mutation                                              guard
doc_readers() drops test_a_pasted_guide_block_...     red: witness + worked example
doc_readers() drops test_the_builders_question_...    red: witness alone
bst-examples' if: removed                             red: heavy-job clause
is_docs() accepts .py                                 red: 2 path rows + docs_only
each reverted                                         30 passed
```

Deviation: the detector is a second module, not a `--docs-only` flag
on the lane tool - `test_a_ci_job_installs_what_its_tool_imports.py`
reads `dev_touching`'s `import tiers` as third-party, and a `pip
install` on the job every heavy job waits on is latency on every PR.
Paths come on stdin and pytest runs in-process, so neither tool adds a
`subprocess` finding to `tests/quality_baseline.json`.
`list_branches` reports `main` `protected: false`; rulesets are not
readable from here. `ci.yml` has no `workflow_dispatch`, and any
event but `pull_request` is `false`, so the lane is first seen on the
first docs-only PR after this merges - the round-closing PR if it
touches only docs. This PR's own CI is code: the full matrix.
