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

**Gap measured.** Base `71d3dcda`, both committed fixtures exported
through `export()` (`halves.py`: page = the file less its
`application/json|octet-stream` blocks, the split every size guard uses):

```text
golden       total   508,053  page 342,017   (PAGE_BUDGET_B 344,000, in a test)
macro_micro  total   568,335  page 342,017
```

**Close measured.** The module ships as `<script type="application/gzip"
id="bga-module-gz">` (base64, `mtime=0`); a 17-line, 718 B inline loader
inflates it with `DecompressionStream` and `import()`s a `blob:` URL, or
writes a sentence into `#report` when the browser has none. The export
has no CSP meta, and under `file://` it boots clean. `PAGE_BUDGET_B`
moved from the test into `CEILINGS` at 150,000 B; cli.md's table has
its row. The served page is not touched.

```text
golden       total   304,567  page 138,531  data 166,036
macro_micro  total   364,849  page 138,531  data 226,318
$ python3 -m tools.bga_view tests/fixtures/macro_micro/run --export mm.html
Wrote .../mm.html (356 KiB: page 135 KiB, data 221 KiB). ...
$ pytest -q -n 2 test_the_viewer_js_ships_compressed.py test_the_page_obeys_its_own_policy.py \
    test_the_console_stays_clean.py test_the_ceilings_reach_a_reader.py \
    test_the_report_you_can_attach.py test_focus_is_an_investigation.py test_why_is_this_ranked_first.py
81 passed in 34.93s
$ pytest -q -n 2 <135 files naming bga_view/export_page/export_uri>   (before the 3 fixes below)
3 failed, 1967 passed, 43 skipped in 800.27s
```

Chrome, the golden export's `blob:` frames for a dispatched `keydown`:
`blob:null/…:4270:15`, `:4270:36`, `:7674:15`; each lands on `key` in
`inflated_module(html)` (`if (event.key !== "[" …`), which equals
`_viewer_module()` byte for byte.

**Mutation table** (each restored from a scratch copy, `cmp` clean):

| mutation | reddened | count |
|---|---|---|
| inline the module uncompressed again | `test_the_page_half_is_under_its_bound` (342,017 > 150,000); also `test_the_page_itself_stays_within_its_budget`, `…_a_backstop_away_from_where_it_is` | 1 of 1 (-k), 2 of 3 in attach |
| loader prepends a line to the code | `test_the_export_boots_and_a_stack_names_a_source_line` (4271:15 is `metaKey`) | 1 of 1 |
| no-`DecompressionStream` branch never taken | `test_a_browser_without_decompression_says_so` (ReferenceError) | 1 of 1 |
| gzip the module with leading spaces stripped | `test_the_module_inflates_to_its_source_byte_for_byte` | 1 of 1 |
| rename `PAGE_BUDGET_B`'s `CEILINGS` entry | `test_the_ceilings_reach_a_reader.py`, 3 clauses | 3 of 5 |

A first stack mutation (`"\n" + code` inside the Python literal) was a
JS syntax error, not a shifted line; rejected and replaced.

**Deviation.** Beyond `tools/bga_view.py`: 14 tests read the module
through `inflated_module()` instead of a `<script type="module">`
regex, 3 grepped the export for module identifiers, the attach
harness inflates in node, `docs/guides/ci-comment.md`'s 488 -> 356 KiB,
and `tests/quality_reference.json` (`bga_view.py` 1,997 -> 2,064 lines,
longest function 164 -> 166).
