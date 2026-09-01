# UX-502: the comment that tells the story

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-497 (the budget these are over) | **Serves:** every session that opens a dev tool to use it, not to relive it | **Topic:** docs

## Motivation

The dev tools carry their own history in-line. Measured in round 74:

```text
tools/dev_tier_drift.py       206 comment lines / 46 code lines   (448 %)
tools/dev_trace_coverage.py   module docstring 85 lines
tools/dev_plane_capability.py module docstring 55 lines
grandfathered over the 25-line cap (UX-497)   8 of 11 files
```

`dev_tier_drift.py`'s docstring walks through three rejected CI
designs with their measured factors. That record is valuable and it
already exists — in `UX-418`'s and `UX-420`'s Outcome sections, which
is where the guide (§3.6) says superseded explanations live. In the
tool, every session that runs `--against` pays for the narrative first.

## Required Fix

For each grandfathered file: a docstring of what it does, how it is
invoked, and one sentence per non-obvious decision *with the task id
that holds the argument* — under 25 lines — and the in-body comment
blocks reduced the same way. Nothing is lost: each deleted paragraph
is checked to exist in the named task file, and where it does not, it
is appended there first (§3.6, the annotation rule).

Before/after per file, pasted: docstring lines, comment lines, code
lines. The `UX-497` grandfather table shrinks to empty in the same
commit, one entry per file brought under the cap.

## Out of Scope

- Any behaviour change in the tools — a refactor-stream item: the
  measurement moves, nothing else does.
- The test files' docstrings — many are long for the same reason;
  measure them first and file separately if they are the same shape.

## Acceptance Test

`tests/unit/test_the_register_is_terse.py` green with an empty
`GRANDFATHERED`; the tools' own guards green; per-file before/after
lines pasted.
