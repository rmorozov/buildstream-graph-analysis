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

The five decisions are taken here so the track has none left:

1. **The five dead exports are deleted, not referenced.** Measured,
   per name, across the whole tree:

   ```console
   forgetIds (controls.js)        viewer 0  tests 0  docs 1
   SPARK_WIDTH (drawings.js)      viewer 0  tests 0  docs 1
   sourceOf (rawjson.js)          viewer 0  tests 0  docs 1
   forgetUnmapped (shapes.js)     viewer 0  tests 0  docs 1
   focusTargets (tablefocus.js)   viewer 0  tests 0  docs 1
   ```

   The one `docs/` hit is this file naming them. Referencing dead code
   to quiet a linter is the fake fix; they go.
2. **The linter runs at the CI gate only, never in `make lint`.**
   `UX-397`'s decision stands - the dev extra stays Python-only, and
   nothing in the tree may need `node` at test time. `npx` does resolve
   in this container (`npx --yes eslint@9 --version` -> `v9.39.5`,
   exit 0), so a track can develop against it; that is not licence to
   depend on it.
3. **Pin the major.** An unpinned `npx --yes eslint` lets a new major
   silently change the finding set, which is the reason `UX-693`
   pinned ruff and `tests/quality_baseline.json` records
   `ruff_version`. Pin, and record the resolved version beside the
   findings the same way.
4. **Re-measure the 70.** Round 93's count is nine rounds old and the
   viewer has moved since - `UX-667` alone rewrote `nav.js` and
   `chapters.js`. Measure on the track's own base, paste it, and treat
   the 70 as context rather than a target.
5. **A baseline, not zero.** The Acceptance Test's "0 problems"
   conflicts with the Required Fix's "the 70 enter the baseline";
   the baseline wins. Fix the three named classes - the 5 dead
   exports, the 6 `==`, the 8 undeclared globals - and whatever
   remains enters `UX-694`'s baseline by identity, so a *new* problem
   is red and the standing ones are recorded rather than hidden.

The surfaces: `eslint.config.js` at the root, `.github/workflows/quality.yml`,
the five viewer modules the dead exports live in, `views.js` for the
six `==`, and the baseline file.

## Out of Scope

- A bundler, TypeScript or a formatter — `UX-397` declined a JS
  toolchain; a linter run by `npx` at the gate adds no file to the
  tree but its config.
- Style rules — the styleguide governs the page, not the source.

## Acceptance Test

`npx eslint bga/viewer` → 0 problems on the adopting commit;
mutation: add `export function unused() {}` to `shapes.js` — red on
`no-unused-modules`; `if (a == b)` in `views.js` — red on `eqeqeq`.
