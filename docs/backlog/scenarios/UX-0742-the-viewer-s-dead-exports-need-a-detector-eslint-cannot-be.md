# UX-742: the viewer's dead exports need a detector eslint cannot be

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-699 (the linter that ships without this), UX-340 (`dev_js_deps`, the module graph already derived) | **Serves:** the session deleting viewer code and wanting to know what nothing reads | **Topic:** guards | **Shape:** bounded | **Area:** tools

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
