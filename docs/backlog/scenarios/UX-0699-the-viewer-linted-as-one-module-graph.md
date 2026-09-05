# UX-699: the viewer linted as one module graph

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-397 (the JS-dependency decision) | **Serves:** the session editing a viewer module, which today has no linter of any kind | **Topic:** viewer | **Shape:** judgement

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
