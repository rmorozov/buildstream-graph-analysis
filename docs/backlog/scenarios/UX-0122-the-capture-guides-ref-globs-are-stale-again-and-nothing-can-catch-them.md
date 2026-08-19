# UX-122: the capture guide's ref globs are stale again, and nothing can catch them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-97 (done — this is its item 2, recurring in the same file)

## Motivation

UX-97 fixed the mode-less ref glob once and automated the two *counts*
that had drifted; ref name patterns stayed hand-maintained prose, and
they drifted again within two days, in the very file that was fixed:

- `docs/guides/real-project-capture.md:235` — a fetch command using
  `captures/fdsdk/<ref>-b4j4-…` with no mode segment: matches **no
  ref** that exists.
- `:207` — the documented ref-name template omits `<mode>`; the
  correct form appears twenty lines later.
- The same section still documents the three-fetch, five-path manual
  band assembly that `bga baseline` (UX-96) abolished — the guide's
  one mention of the helper is an aside in an unrelated sentence.
- `docs/guides/cli.md:538` — the exit-6 list says two commands return
  it; `bga baseline` is a third (as `cli.md:364` itself states).

## Required Fix

1. Fix the two globs, replace the manual assembly block with the
   `bga baseline` invocation, add `bga baseline` to the exit-6 list.
2. The recurrence-stopper, same shape UX-97 gave the counts: a docs
   test that extracts every `captures/…` pattern from the docs and
   validates it against the workflow's own ref-name expression
   (`${SHORT_REF}-${CAPTURE_MODE}-b${BUILDERS}j${MAX_JOBS}-${run_id}`)
   — a pattern that cannot match a name the expression generates fails
   the suite.

## Out of Scope

- Renaming the refs themselves.

## Acceptance Test

`git ls-remote origin` piped against each documented glob matches ≥1
existing ref; the new docs test fails when a mode-less glob is
reintroduced (verified by mutation); the guide's baseline-assembly
section is one `bga baseline` command.
