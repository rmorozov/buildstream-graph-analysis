# UX-742: the viewer's dead exports need a detector eslint cannot be

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-699 (the linter that ships without this), UX-340 (`dev_js_deps`, the module graph already derived) | **Serves:** the session deleting viewer code and wanting to know what nothing reads | **Topic:** guards | **Shape:** bounded | **Area:** tools

## Motivation

`UX-699` set out to find dead viewer exports with
`eslint-plugin-import`'s `no-unused-modules`. It shipped without that
rule, because the rule cannot work in this tree and two separate
measurements say so.

**It crashes.** With every package present and the flat config loading
correctly, `npx --package eslint@9 --package eslint-plugin-import@2
--package globals@17 -- eslint bga/viewer` exits **2** inside
`no-unused-modules.js:636` — the rule needs a `package.json` findable
above the linted file, and
`test_the_viewer_renders_the_schema.py::test_there_is_no_package_json_anywhere_near_it`
forbids one anywhere in the tree. `UX-699`'s track worked around it by
writing a throwaway `package.json` beside the checkout in CI; that is
untested against a real runner's layout and was dropped with the rule.

**And it cannot red.** `tests/viewer.mjs` re-exports the viewer
wholesale (`export * from`), which marks every export used for as long
as it is in scope, so the Acceptance Test's own mutation - `export
function unused() {}` in `shapes.js` - produces nothing. Excluding the
barrel instead surfaces **121** findings rather than the 5 the filing
predicted. Neither number is the answer to "what does nothing read".

A rule that crashes without a hack and cannot discriminate when it runs
is the shape this repository names in `CLAUDE.md`: a guard whose setup
excludes the thing it tests.

## Required Fix

The judgement first: **eslint is the wrong instrument for this
question in this tree**, and the next attempt should not begin by
re-configuring it.

`tools/dev_js_deps.py` (`UX-340`) already derives the viewer's module
graph - order, cycles, what would cross a cut - from the source rather
than from a plugin's opinion of it. An export nothing imports is a
fact about that graph. The route to weigh first is a clause on the
tool that already reads the population, with `tests/viewer.mjs`'s
barrel handled explicitly as what it is: a test fixture, not a reader.

Measure before choosing: how many exports does `dev_js_deps`' graph
show unread, with the barrel counted and with it excluded, against the
five the whole-tree grep found (`forgetIds`, `SPARK_WIDTH`,
`sourceOf`, `forgetUnmapped`, `focusTargets` - all now deleted).

## Out of Scope

- `eqeqeq` and `no-undef`, which `UX-699` shipped and which work: the
  eqeqeq mutation reddens (1 error, exit 1) and reverts to green.
- Adding a `package.json`, in the tree or beside it. The guard that
  forbids one is deliberate.

## Acceptance Test

The detector names an export nothing reads and stays silent on one the
page uses. Mutation: add an unread export to a viewer module and
confirm the detector names it; import it from a real viewer module and
confirm it goes quiet.

## Outcome (round 103, 2026-09-07) — 🟢 Done

**Premise:** held — eslint is wrong here, and the graph alone is not
right either: 108 is not 5.

**The gap, measured.** `dev_js_deps`' graph over `bga/viewer`, barrel
*counted* (every export of a module `tests/viewer.mjs` re-exports
marked used): **0** unread - it agrees with `no-unused-modules`'
default-scope answer for the same reason, a wildcard `export *`. Barrel
*excluded* (only real cross-module imports inside `bga/viewer` count):
**108** unread - next to the **121** `no-unused-modules` found scoped
the same way, both dominated by exports a *test* reads only through the
barrel's dynamic `await import(...)`, invisible to either instrument.
Neither is the five: the graph alone cannot tell a dead export from one
only a test reads. Per the row's instruction that is a finding about
the question, so a second stage was added rather than the 108 shipped.

**The close, measured.** `dev_js_deps.dead_exports()`: barrel-excluded
graph candidates, each confirmed against a whole-tree text search (the
same check that cleared `UX-699`'s five by hand) before being named.
On the current tree: **1** confirmed (`takesWindow`, `questions.js`) -
new, not one of the five (`forgetIds`, `SPARK_WIDTH`, `sourceOf`,
`forgetUnmapped`, `focusTargets`), all already deleted by `UX-699`.

Acceptance Test, on the real tree (`git diff --stat` clean before and
after, mutation reverted):

```console
$ python3 tools/dev_js_deps.py --dead-exports bga/viewer
questions.js: takesWindow
$ # + `export function ux742Unused() {...}` in shapes.js
$ python3 tools/dev_js_deps.py --dead-exports bga/viewer
questions.js: takesWindow
shapes.js: ux742Unused
$ # sections.js: import { CONTROLS, classify, ux742Unused } from "./shapes.js";
$ python3 tools/dev_js_deps.py --dead-exports bga/viewer
questions.js: takesWindow
```

**Mutations** (`tests/unit/test_the_graph_is_derived_not_guessed.py::TestTheDeadExportDetector`,
reverted from a pristine copy each time):

| mutation | reddened | count |
|---|---|---|
| drop the `-1` (own declaration) term | `test_an_export_nothing_imports_is_named` | 1 failed, 12 passed → reverted: 13 passed |
| confirm only within `directory`, not the whole tree | `test_a_reader_outside_the_directory_is_not_a_false_positive` | 1 failed, 12 passed → reverted: 13 passed |

**The census read its own record**, twice. Writing `takesWindow` into
this Outcome put four mentions in a tracked `.md` and the next run
called it alive; excluding `docs/` re-broke it one layer down, on the
comment that explained the exclusion. The corpus is now every tracked
file except `docs/` and this module (`reads_code()`) — not a suffix
rule: seven of eight candidates are alive only because a Python page
guard drives them by name.

| mutation | reddened |
|---|---|
| `docs/` counted as a reader | `_prose_about_a_name_is_not_a_reader` + 1 |
| the detector's own source counted | `_the_detectors_own_source_is_not_a_reader` |
| the corpus made a `.js/.mjs/.html` suffix rule | `_a_python_reader_elsewhere_still_counts` + 1 |

### Deviation from the Required Fix

Two, both on merge. The track forced **two new baseline entries**
(`PLR0915` on `main()`, `S607` on a second `git ls-files`) where
`UX-705` exists to shrink that list; both are gone — the CLI clause is
`_report_dead()`, the tracked-file list is `UX-687`'s `tracked_paths`
whose `git ls-files` is already baselined, and `forced_by` is cleared.
`takesWindow` is named, not deleted: the row asked for the detector.

```text
$ python3 tools/dev_js_deps.py --dead-exports bga/viewer
questions.js: takesWindow
$ make test
7626 passed, 82 skipped, 1 warning in 434.31s (0:07:14)
$ make lint
All checks passed! / clean: 292 finding(s)
```

