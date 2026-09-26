# UX-1034: reader chips print R1 to R5 inside section headings

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4g.3 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** bounded

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844. Section headings read "What this capture supports **R4**"; §4g.3 says no internal key reaches the reader.

## Decomposition

Input classes: every section heading with a reader chip; each reader. The journey extends reading a heading into knowing who it is for.

## Required Fix

The chip in `bga/viewer/` names the reader in words, or leaves the heading.

## Out of Scope

The R-numbers in the docs, which are for authors.

## Acceptance Test

The reader-strings guard (§4g) reds on `\bR[1-9]\b` in rendered headings. Mutation: restore the chip text, and the guard reds.

## Outcome

Gap: `bga/viewer/chapters.js`'s `applyRole` wrote the raw `R1`-`R5`
role id straight into the chip's `textContent` (`owns ? chosen : …
readers.join(" ")`) — the exact string §4g.3 forbids.

Close: added `READER_WORDS` (off `findings.READERS`' uid, e.g. R3 →
"graph owner") and routed both branches through it. `styleguide.md`
§4g gains item 7. `tests/unit/test_a_reader_never_sees_the_register.py`
gains `test_no_reader_id_in_rendered_text`, reading `\bR[1-9]\b`
against `innerText` on both fixtures:

```text
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_a_reader_never_sees_the_register.py -q
14 passed in 4.28s
```

First draft prefixed each word with "the" ("the graph owner"); on
sections without a chosen reader every declaring section's chip
renders unconditionally on landing, and the extra word per chip put
`macro_micro` 6 words over §3e's `test_the_page_has_a_volume_budget.py`
cap (12,806 of 12,800). Dropped "the".

Mutation table:

| mutation | reddened | count |
|---|---|---|
| restore `readers.join(" ")` (raw ids) in the un-chosen branch | `test_no_reader_id_in_rendered_text[golden]`, `[scale]` | 2 failed |
