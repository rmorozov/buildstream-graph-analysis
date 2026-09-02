# UX-122: the capture guide's ref globs are stale again, and nothing can catch them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-97 (done — this is its item 2, recurring in the same file) | **Topic:** docs

## Motivation

UX-97 fixed the mode-less ref glob once and automated the two *counts*
that had drifted; ref name patterns stayed hand-maintained prose, and
they drifted again within two days, in the very file that was fixed:

- `docs/design/capture-workflow.md:235` — a fetch command using
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

---

## Fix Implemented

The three stale things, and the check that stops the fourth.

- The mode-less fetch glob and the mode-less ref template both gained
  their `<capture-mode>` segment.
- The three-fetch, five-path manual band assembly is replaced by the
  `bga baseline` one-liner that abolished it, with the old block folded
  into a `<details>` — a reader may still meet it in an older CI job.
- `cli.md`'s exit-6 list names `bga baseline` as the third command that
  returns it, which `cli.md` itself already said twenty lines earlier.

### The recurrence-stopper reads the generator

`tests/unit/test_capture_ref_patterns.py` extracts the workflow's own
`RUN_REF=` assignment, builds a regex for the *shape* it generates, and
checks every `captures/…` token in the guides against it. Each `${VAR}`
becomes "one segment, which may be a real value, a `<placeholder>`, a
`*`, or an unexpanded shell variable" — anything except **nothing**,
which is what a dropped segment looks like.

Checked by putting the bug back:

```text
E   AssertionError: docs/design/capture-workflow.md documents
    `captures/fdsdk/953683fb-b4j4-*`, which is not the shape the workflow
    publishes (`captures/fdsdk/${SHORT_REF}-${CAPTURE_MODE}-b${BUILDERS}j${MAX_JOBS}-${{ github.run_id }}`,
    e.g. `captures/fdsdk/953683fb-incremental-b4j4-32223468993`)
```

### Only the documents that tell a reader what to type

The check scans `docs/guides/`, `docs/spec/` and the README — not
`docs/backlog/` or `docs/audits/`, which are append-only history. `UX-81`'s
file quotes the ref shape as it was the day it shipped, before the mode
segment existed, and **this task's own file quotes the broken glob as the
defect**. Forcing those to match today's generator would either rewrite
history or forbid a task from quoting the bug it fixed.

That boundary is written into the test as a named constant with the
reason attached, because it is the sort of scope decision that looks
arbitrary a year later.

## Verification Log

Done 2026-08-19. Seven tests, including the reintroduce-the-bug check
above; the four historical patterns the first draft flagged are what
produced the guides-only scope rather than a suppression list.
