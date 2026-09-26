# UX-1036: `bga view --export` prints a double period before its timeline hint

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §4g | **Serves:** R1 | **Topic:** cli | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/bga_view.py:1926` formats `No Perfetto timeline in it: {omitted}. ` and `omitted` is a sentence from `bga/plane2.py` that already ends in a period, so the export prints "goes missing.. `bga timeline` renders one".

## Required Fix

`tools/bga_view.py` strips the trailing period of `omitted` or drops its own.

## Out of Scope

The absence sentences' wording.

## Acceptance Test

`tests/unit/test_the_export_message_is_punctuated.py` exports a run with Plane 2 but no raw log and asserts no `..` in stderr. Mutation: restore the format string, and the guard reds.

## Outcome

Gap measured: `written["omitted"]` (from `bga/plane2.py`, e.g.
`CAPTURED_NO_RAW_LOG`) already ends in a period; `tools/bga_view.py:1926`
appended `. \`bga timeline\` renders one...` unconditionally, printing
`"...goes missing.. \`bga timeline\`..."`.

Close measured: `written["omitted"].rstrip(".")` before the format
string. `tests/unit/test_the_export_message_is_punctuated.py` (new,
Plane 2 captured, no raw log, real `bga_view.main(["--export", ...])`):
`1 passed in 0.43s`; `".." not in captured.err` holds.

Mutation table:

| mutation | reddened | count |
|---|---|---|
| restore `f"...{written['omitted']}. ..."` (drop the `.rstrip(".")`) | `test_no_double_period_before_the_timeline_hint` | 1 failed / 1 |

Deviation: none from the Required Fix; the guard names `bga/plane2.py`, so `test_the_loop_stays_fast.py` lists it among the wide modules (`c50bfc59`).
