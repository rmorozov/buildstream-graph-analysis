# UX-699: the viewer linted as one module graph

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-397 (the JS-dependency decision) | **Serves:** the session editing a viewer module, which today has no linter of any kind | **Topic:** viewer | **Area:** unassigned | **Shape:** judgement

## Motivation

`bga/viewer/*.js` (12,906 lines, 5 modules over 1,000) has never been
linted. `eslint` per file with browser globals and five rules, round
93: **70** problems — `no-unused-vars` 55, `no-undef` 8
(`IntersectionObserver`, `setInterval`, `clearInterval`), `eqeqeq` 6
(all in `views.js`). Per file, 55 "unused" are mostly exports read by
another module — the resolver is the missing half. A whole-tree grep
found 5 exports nothing references: `forgetIds` (`controls.js`),
`SPARK_WIDTH` (`drawings.js`), `sourceOf` (`rawjson.js`),
`forgetUnmapped` (`shapes.js`), `focusTargets` (`tablefocus.js`).
`dev_js_deps --graph`: no cycles.

## Required Fix

An `eslint.config.js` at the root with `sourceType: "module"`,
browser globals, `eslint-plugin-import` (`no-unused-modules` with
`unusedExports`), `eqeqeq`, `no-undef`; run at the gate via
`npx --yes` in `quality.yml` (`UX-698`) — the dev extra stays
Python-only, `UX-397`'s decision. The 5 dead exports are deleted or
referenced, the 6 `==` fixed, the 8 globals declared. The 70 enter the
baseline (`UX-694`) by identity, so a new one is red.

## Out of Scope

- A bundler, TypeScript or a formatter — `UX-397` declined a JS
  toolchain; a linter run by `npx` at the gate adds no file to the
  tree but its config.
- Style rules — the styleguide governs the page, not the source.

## Acceptance Test

`npx eslint bga/viewer` → 0 problems on the adopting commit;
mutation: add `export function unused() {}` to `shapes.js` — red on
`no-unused-modules`; `if (a == b)` in `views.js` — red on `eqeqeq`.

## Outcome

**The gap, measured.** `npx --yes --package eslint@9 --package eslint-plugin-import@2
--package globals@17 -- eslint bga/viewer` crashes (`ERR_INVALID_ARG_TYPE` in
`fileIsInPkg`, exit 2) as committed: `no-unused-modules` needs a `package.json`
findable above the linted file, and none exists anywhere in this tree's ancestry -
confirmed by the pre-existing `test_there_is_no_package_json_anywhere_near_it`,
which a first attempt at this fix violated. With one placed temporarily for
measurement: `eqeqeq` 6, all in `views.js` (lines 372/374/376/433/522×2, the
`== null`/`!= null` idiom); `no-undef` 0 - the `globals` npm package's `browser`
set already carries `IntersectionObserver`/`setInterval`/`clearInterval` (336
errors with `globals: {}`, for comparison, confirming the rule is live);
`import/no-unused-modules` at default scope (`src=[cwd]`): **0** findings, because
`tests/viewer.mjs`'s `export * from` barrel (every viewer module, `UX-337`) marks
every export of every file it re-exports "used", wholesale; scoped to
`bga/viewer` alone: **121** findings across nearly every module - the barrel and
the `await import(...)` strings embedded in `tests/unit/test_*.py` (the real
consumers) are invisible to static analysis either way. Not the 5-dead/50-resolved
split the Motivation assumed.

**The close, measured.** Deleted the 5 confirmed-dead exports (`forgetIds`,
`SPARK_WIDTH`, `sourceOf`, `forgetUnmapped`, `focusTargets` - 0 refs anywhere
but their own declaration and this filing). Fixed the 6 `eqeqeq` sites with a
local `notNullish` helper in `views.js`. Removed one stale `no-console`
eslint-disable comment that this config's rule set turned into a "no problems
were reported" warning. `npx eslint bga/viewer` (`package.json` present): **0
problems**, exit 0. 6 touched viewer files: 120,149 B → 119,600 B (-549 B); the
two budget guards (`test_the_report_you_can_attach.py`,
`test_the_page_has_a_volume_budget.py`) pass unchanged, 57 passed/2 skipped -
no bound moved.

**Mutations** (reverted from a pristine copy each time):

| mutation | reddened | count |
|---|---|---|
| `if (a == b)` in `views.js` | `eqeqeq` | 1 error, exit 1 → reverted: 0, exit 0 |
| `export function unused() {}` in `shapes.js` | **did not redden** | 0 problems, exit 0, at every `src` scope tried |

**Deviation.** `import/no-unused-modules` does not discriminate on this codebase:
`tests/viewer.mjs`'s wildcard barrel is the intended cross-module bridge for
every unit test, and the plugin counts `export * from X` as using every name in
X, forever - so nothing in `bga/viewer` can ever redden while the barrel is in
scope, and (121, not 5) redden if it is excluded. Wired per decision #2 anyway,
with this caveat open. `dev_baseline.py` (eslint support, per `UX-694`'s own
Outcome) was not touched - out of the mission's seven numbered checks. Second:
the plugin crashes with no `package.json` above the linted file, which an
existing guard forbids inside this tree; `quality.yml` writes one beside the
checkout, untested against a real runner's layout. `dev_touching.py --spread
--write`: no diff (no `tools/` or top-level `tests/` file added).
