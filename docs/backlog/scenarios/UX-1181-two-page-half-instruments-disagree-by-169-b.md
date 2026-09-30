# UX-1181: two page-half instruments disagree by 169 B, and two tests still count characters

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-157 walk (2026-09-30) | **Serves:** R1 | **Topic:** guards | **Area:** tests | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

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

## Outcome

Open.
