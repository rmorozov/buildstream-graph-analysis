# UX-1181: two page-half instruments disagree by 169 B, and two tests still count characters

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_page_half_is_read_once.py`

## Motivation

Page: the round-157 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `73af3af3`, Chromium 1440x900 and 390x844.

After `UX-1174`, `_embedded` leaves out the script tags that `export()` counts, so the two page-half instruments disagree by 169 B (`pagebytes.py` reads 144,179 B and `export()`'s `page_bytes` 144,197 B at `73af3af3`). `test_the_page_is_the_modules_and_nothing_else` and `test_the_data_is_the_documents_and_the_schemas` still count characters where `UX-1174` moved the page-half guard to bytes.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

One instrument reads the page half, in bytes, and every guard that measures it uses that one; the two named tests count bytes.

## Out of Scope

The page budget (160,000 B, the owner's).

## Acceptance Test

`_embedded` and `export()` agree on the page half to the byte on the golden page; the two named tests count bytes; a non-ASCII character in the page moves each by its byte width. Mutation: count characters in one, and its guard reds.

## Decision

Route: one function, `page_half(html) -> int` in `tools/bga_view.py`, owns the data-block pattern and returns the UTF-8 bytes of the html with its data blocks removed. `export()` sets `page_bytes = page_half(page)` and `data_bytes = bytes - page_bytes`, so page + data == bytes by construction. The 169 B: `size - _embedded` counted the `<script>` tags as page, `export()` does not.

Rejected: a guard asserting two helpers agree (the one function makes the mistake impossible); keeping the out-of-tree `pagebytes.py` reading.

Retired: `_embedded`, `_page_half` (`test_the_report_you_can_attach.py`), `_DATA` (`test_the_viewer_js_ships_compressed.py`); the `re.sub` in `test_the_exports_data_half_has_a_budget.py::_halves` (a fourth page-half counter, in characters) reads `view.page_half` too.

Deviation from the architect: clause (3) is "no test or tool outside `bga_view.py` `re.sub`s the octet-stream pattern", not "spelled in one file": six tests parse the blocks (`findall`), which is not a page-half reading.

## Outcome

Gap measured, `export()` then `size - sum(block bodies)` (the old `_embedded` reading) against `export()`'s `page_bytes`, at `8a531cbb`:

```text
golden       bytes 315,044  page_bytes 144,200  old 144,369  diff 169
macro_micro  bytes 376,003  page_bytes 144,200  old 144,369  diff 169
```

Close measured, same fixtures, `view.page_half(html)` against `page_bytes`: 144,200 = 144,200 on both; page + data == bytes. `page_bytes` itself is unchanged (144,200); readings that went through `_embedded` drop 169 B. Page net 0 B (tools/ only).

```text
PYTEST_XDIST= python3 -m pytest test_a_page_half_is_read_once.py test_the_viewer_js_ships_compressed.py \
  test_the_exports_data_half_has_a_budget.py test_the_report_you_can_attach.py test_the_export_ships_no_indentation.py
88 passed in 29.40s
```

Mutations (`test_a_page_half_is_read_once.py`, 5 tests):

| mutation | result |
|---|---|
| `page_half` returns characters, not `.encode()` bytes | 2 failed, 3 passed (the byte-width clause, and the modules test's slack) |
| modules test reads `len(view._DATA_BLOCK.sub('', html))` | 1 failed, 4 passed |
| data test sums `len(block)` characters | 1 failed, 4 passed |
| a test file re-splits the page with `re.sub(...octet-stream...)` | 1 failed, 4 passed |

Deviation: the architect's clause (3) narrowed to `re.sub` of the pattern (see Decision); `_halves` in the data-budget test re-based onto `page_half` (its page reading is now bytes, 169 B and the non-ASCII width apart, inside its slack); the modules test reads `view.page_half` and needs a module-level `view` import in `test_the_report_you_can_attach.py`. `tests/quality_reference.json` adopted for `tools/bga_view.py`. New guard needs a `tests/tiers.py` row (orchestrator's).

