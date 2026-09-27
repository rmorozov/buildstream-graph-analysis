# UX-1052: the export carries its viewer JS gzipped, and a guard bounds its bytes

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), Ruslan's question on #297 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `814a2db8`, `python3 -m tools.bga_view
tests/fixtures/macro_micro/run --export mm.html`, the `type="module"`
script's bytes:

```text
export total                                   568 KB   (EXPORT_BUDGET_B 8 MiB)
viewer module, comments stripped (_uncommented) 306 KB
  + leading whitespace removed                 273 KB   -11%
  + esbuild --minify-whitespace                247 KB   -19%
  + esbuild --minify                           185 KB   -40%
  gzip                                          77 KB   -75%
viewer JS source (git ls-tree, bga/viewer/*.js) 525 KB 2026-09-01, 597 KB 09-15, 632 KB 09-27
```

The source grew 20% in four weeks and nothing bounds the module's
bytes. A minifier needs npm, which §6b refuses, and `bga_view.py`'s
`_uncommented` says it "must not become one", so a stack trace quotes
the source. Gzip keeps the code byte-identical: the report half already
ships as `bga-report-gz` and `app.js` inflates it with
`DecompressionStream`.

## Decomposition

Input classes: the export under `file://`, the served page with its
CSP, print, a browser without `DecompressionStream`.

## Required Fix

`tools/bga_view.py` writes the module gzipped beside the report, and a
small inline loader inflates it and imports it (a `blob:` module URL),
in the export only; the served page is unchanged. The page and the
data half's bytes are reported separately, and the page half gets a
bound in `CEILINGS` (§3g).

## Out of Scope

Minification; the data half (`bga-report-gz`, `bga-trace`,
`bga-schemas`).

## Acceptance Test

The export boots under `file://` with zero console errors and CSP
violations (`test_the_page_obeys_its_own_policy.py`); a stack trace
from the loaded module names a source line; a guard holds the page
half under its bound. Mutation: inline the module uncompressed again,
and the bound reds.

## Outcome

Not started.
