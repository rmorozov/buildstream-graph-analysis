# UX-1166: key paths and dashes still reach reader text

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_key_path_stays_where_it_is_copied.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

`#document_shape` shows the raw key path "findings.[].evidence.blast_radius_distribution.deciles.p10"; " - " appears 140 times as a dash; null values print as dashes (`UX-1159`'s guard reads the page part at 1440 only).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Choice.** A new schema hint `bga:key_path` marks `document_shape.deepest_path`; `renderPairs` prints it as `pathTrail` (each named step's schema label, joined by `›`) and keeps the path on `data-raw`. A dash in producer prose is `—`: every non-docstring string literal in `bga/{schemas,findings,correlate,provenance,analyzer,plane2,cache_trend,cli}.py` and `bga/report/_shared.py`, the tracer's seven report notes and the viewer's reader strings; a list bullet (`  - `) and an f-string's `{a - b}` are untouched. A null prints `ABSENT` (`none`) in `format.js`, `views.js` and `bga/shown.py`, as §1's table already says.
- **Files.** The above; styleguide §1a row and §4g item 8; committed analyses by `dev_refresh_analysis.py --write`; `macro_micro/plane2.json`'s six notes as the tracer now writes them (`UX-1159`'s precedent); the README quick-start lines from a fresh run.
- **Guard.** `UX-1159`'s file, extended: `#document_shape` leaves the copy list (a string drawn as itself there is read too), a `.[]` step counts as a key path, both widths, and the two-plane review page; plus a spaced-hyphen test on the page and over every schema description, and a lone-dash literal test over the viewer and `shown.py`.
- **Mutation.** Drop the hint; restore one `-` in a finding, a canned query and a split description; restore `return "—"` in `duration`.

## Required Fix

The path reads as the label a reader knows, and neither " - " nor a null dash stands for a value.

## Out of Scope

The schema descriptions `UX-1159` fixed.

## Acceptance Test

At 1440 and 390 no reader text contains a key path or a spaced hyphen dash. Mutation: restore one, and the guard reds.

## Outcome

**Gap measured** - on the base (`3e6feb45`), every door open, visible text nodes outside `pre`/`code`; the two-plane page is `gen-synthetic --seed 1 --store --layers 8 --width 14` plus its `capture report --json`:

```text
                 spaced " - "     lone null dash   #document_shape raw path
golden           96 at 1440, 96 at 390     0       1 (findings.[].evidence.steps.[].entering.[])
macro_micro     153 at 1440, 153 at 390    0       1
two_plane       133 at 1440, 133 at 390    0       1 (findings.[].evidence.blast_radius_distribution.deciles.p10)
schema descriptions walked 1173, with a spaced hyphen 314
lone-dash null literals 9: format.js:174,184,192 views.js:444,446,527 shown.py:11,27,32
```

No fixture reaches a null the formatters print, so the null half is held on the source.

**Close measured** - the same instruments on this commit:

```text
golden 0 · macro_micro 0 · two_plane 0 spaced, at 1440 and at 390; lone null dash 0; raw path 0
#document_shape  findings.[].evidence.blast_radius_distribution.deciles.p10
                 => Findings › Evidence › Blast radius distribution › Deciles › P10
schema descriptions with a spaced hyphen 0 · lone-dash null literals 0
page with its data removed (golden, bytes)  149,931 -> 150,083  (+152)
TestTheSizeDiscipline's own reading          150,140 (its len() of the data counts an em dash as 1)
```

**Mutation table** - each reverted from a copy, then green (9 passed):

| mutation | reddened | the run printed |
|---|---|---|
| `deepest_path` loses `KEY_PATH: True` | `test_no_reader_text_holds_a_key_path[golden,macro_micro,two_plane]` | 3 failed, 6 passed |
| finding "by design: {named} — structural" back to `-` | `test_no_reader_text_spaces_a_hyphen_for_a_dash[two_plane]` | 1 failed, 8 passed |
| `questions.js` "the element uid — the same" back to `-` | `test_no_reader_text_spaces_a_hyphen_for_a_dash[golden,macro_micro,two_plane]` | 3 failed, 6 passed |
| `duration` returns `"—"` for null again | `test_no_null_is_drawn_as_a_dash` | 1 failed, 8 passed |
| `execution_on_chain_us`'s split description "- the part" restored | `test_no_schema_description_spaces_a_hyphen` + the page test on all three | 4 failed, 5 passed |

The first run of the hint mutation reddened `two_plane` alone: golden's path has no `snake_case` step, so `_KEY` gained the `.[]` alternative.

**Deviation.** Re-based, claims kept: `test_the_cpu_floor_divides_by_cores`'s `GOLDEN_NOTE` and two `docs/design/rendered-strings.json` rows follow the new dash; `format.js`'s header counts 20 of 23 hints for `test_the_contract_names_its_vocabulary`; the README quick-start block's three lines are pasted from a fresh `bga analyze … --diagnostics`. The page grows 152 B, over the brief's ~150 B share; the size guard reads +395 B because it subtracts the data's characters, not its bytes.
