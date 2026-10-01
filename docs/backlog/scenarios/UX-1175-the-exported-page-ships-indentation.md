# UX-1175: the exported page ships indentation

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_export_ships_no_indentation.py`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Measured by `UX-1167`: stripping leading whitespace from the JS saves 5,148 B (111,732 to 106,584 gz) once multi-line template literals are safe, and tightening the CSS saves about 3,480 B.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

The exporter strips leading whitespace from JS outside template literals and tightens the CSS, so the page half shrinks by the measured bytes; the stack still names a source line.

## Decision

- **JS:** `_comment_spans`'s scanner becomes `_lexed_spans`, which also yields every string, template and regex literal; `_uncomment_js` then drops a line's leading spaces and tabs unless the line starts inside one of those literals. No line is joined, so a stack's line number and the text it quotes still hold (only its column moves, and the module is the inflated source).
- **CSS:** `_uncommented_css` collapses whitespace outside quoted strings and drops it around `{ } ; ,`, after `:`, and a `;` before `}`. Spaces a combinator or `calc()` reads are left.
- **Files:** `tools/bga_view.py`, `tests/quality_reference.json` if it grows.
- **Guard:** `tests/unit/test_the_export_ships_no_indentation.py`: every template literal in the modules and a built literal with indented content survive byte-identical, code lines carry no indentation, the CSS strings survive, and golden's page half is 5,000 B under the pre-strip figure. Mutation: strip indentation on every line, literal or not, and the guard reds.

## Out of Scope

Changes to the page's rendered text; the budget.

## Acceptance Test

The golden page half is at least 5,000 B smaller, `test_the_export_boots_and_a_stack_names_a_source_line` passes, and no template literal changes. Guard: that test plus a literal-preservation test. Mutation: strip inside a template literal, and the guard reds.

## Outcome

**Gap measured** - `view.export` of `golden` and `macro_micro` (`pages.snapshot_copy`), a scratch `measure.py`, base `83f10ca8`:

```text
golden       page 151,228 B   total 322,076 B   module raw 329,322 B  gz 84,538 B   css 31,680 B
macro_micro  page 151,228 B   total 383,030 B   (the page half is the same file)
```

**Close measured** - same script:

```text
golden       page 142,828 B   total 313,676 B   module raw 295,199 B  gz 80,794 B   css 28,272 B
macro_micro  page 142,828 B   total 374,630 B
saving       8,400 B on the page half: module block 4,992 B (gz -3,744 B, base64), css 3,408 B
guards       test_the_export_ships_no_indentation.py 29 passed in 1.76 / 1.69 / 1.71s
             test_the_viewer_js_ships_compressed.py + test_the_export_carries_no_commentary.py 60 passed
             (the stack test among them); 21 export-reading files: 405 passed, 26 skipped
```

**Mutation table** - `tests/unit/test_the_export_ships_no_indentation.py` (29 tests), each mutation alone, `tools/bga_view.py` restored from its copy, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | reddened | run |
|---|---|---|
| `_unindented_js` strips every line, literal or not | the built literal; template literals of `app.js`, `element.js`, `nav.js`, `questions.js`, `shapes.js` | 6 failed |
| `_uncomment_js` skips `_unindented_js` | the built literal; every indented line starts inside a literal; golden 5,000 B smaller | 3 failed |
| `_uncommented_css` tightens inside quoted strings too | the built CSS case (the real sheet's strings carry no hazard it touches) | 1 failed |
| `_uncommented_css` drops every space, not collapses | Chromium parses the same rules; the built CSS case | 2 failed |
| all reverted | - | 29 passed |
