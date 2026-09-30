# UX-1174: the page-size guard subtracts the embedded data's characters, not its bytes

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_report_you_can_attach.py::TestTheSizeDiscipline::test_a_non_ascii_datum_leaves_the_page_half_where_it_was`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

`UX-1166` read +395 B by `test_the_viewer_js_ships_compressed.py` against +152 B real: the guard subtracts the embedded data's character count from the page's byte count, so each non-ASCII character in the data counts 2 B against the page ("—" is 3 bytes in UTF-8, 1 character).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Choice.** Every page-half reading in `TestTheSizeDiscipline` counts UTF-8 bytes: `_embedded` encodes each block, and a new `_page_half` (the file with its data blocks removed, encoded) replaces the backstop's and `_weigh`'s `len(page)`. The exporter's `json.dumps` escapes non-ASCII today, so a raw datum is built by hand into the export; the page's own 14 non-ASCII characters are the live 18 B under-read.
- **Files.** `tests/unit/test_the_report_you_can_attach.py` only; `test_the_viewer_js_ships_compressed.py` already encodes both halves.
- **Guard.** `test_a_non_ascii_datum_leaves_the_page_half_where_it_was` in the same file, beside the helper it holds: one raw `—` in a JSON block moves neither reading, and `_page_half` equals `export()`'s `page_bytes`.
- **Mutation.** `_embedded` back to `len(found)`; `_page_half` back to a character count.

## Required Fix

The guard measures the page half in bytes on both sides of the subtraction, or encodes the data before it subtracts.

## Out of Scope

The budget itself (160,000 B, the owner's call in `UX-1167`).

## Acceptance Test

A page whose data gains one non-ASCII character reads the same page half. Guard: `test_the_viewer_js_ships_compressed.py` with a non-ASCII datum. Mutation: subtract `len(data)` again, and the guard reds.

## Outcome

**Gap measured** - `gap.py` (scratch): `export()` on `golden`, then the same file with `"datum": "—"` written raw into `bga-run`, at `83f10ca8`:

```text
golden                   export page_bytes 151,228  backstop 151,210  bytes-_embedded 151,397
golden + raw — datum     export page_bytes 151,228  backstop 151,210  bytes-_embedded 151,399
```

The exported data is ASCII (0 non-ASCII characters in golden's or macro_micro's blocks: `json.dumps` escapes), so the live error is the page's own 14 non-ASCII characters - the backstop reads 18 B low; `_embedded`'s character count moves the page +2 B per raw `—` only once an exporter writes one raw. `UX-1166`'s +395 B is not reproduced from this base.

**Close measured** - the same script on this commit:

```text
golden                   export page_bytes 151,228  backstop 151,228  bytes-_embedded 151,397
golden + raw — datum     export page_bytes 151,228  backstop 151,228  bytes-_embedded 151,397
```

`PYTEST_XDIST= python3 -m pytest tests/unit/test_the_report_you_can_attach.py tests/unit/test_the_viewer_js_ships_compressed.py tests/unit/test_the_register_is_terse.py -q`: 1343 passed.

**Mutation table** - each reverted from a copy, then green (12 passed, `-k TestTheSizeDiscipline`):

| mutation | reddened | the run printed |
|---|---|---|
| `_embedded` sums `len(found)` again | `test_a_non_ascii_datum_leaves_the_page_half_where_it_was`: `(151229, 151454)` vs `(151229, 151456)` | 1 failed, 11 passed |
| `_page_half` returns `len(page)` | the same test: `(151211, 151229)` | 1 failed, 11 passed |
