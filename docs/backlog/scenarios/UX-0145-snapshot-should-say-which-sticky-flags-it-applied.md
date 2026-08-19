# UX-145: snapshot should say which sticky flags it applied

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-126 (done — these are its surprise edges)

## Motivation

Three small edges from round 14's verification of the new loop, none
wrong, each a surprise waiting:

1. **Sticky flags apply silently.** `.bga/config` merges over defaults
   on every `bga snapshot`, and nothing at capture time names the
   effective trace flags. Set `--trace-spine=off` once; three weeks
   later a bare `bga snapshot` runs spine-off and the capture's
   unexplained blind spot is discovered at read time. What-ran *is*
   recorded (context and report) — recording a surprise is not
   preventing it. One stderr line closes it:
   `Using .bga/config: --trace-opens --trace-spine=auto`.
2. **`bga baseline --candidate` takes no `@last`** — the one
   run-directory argument outside `cli.py`'s alias threading, against
   UX-126's "every command that takes a run directory" claim (the
   narrowing went unrecorded). Thread it or record the deviation.
3. **"Memory envelope grew: 0.6 GB -> 0.6 GB (+0.0 GB, +0%)"** — the
   compare note fires its "grew" wording on a zero delta (observed
   live in round 14's snapshot run). A delta of zero is "unchanged".

## Required Fix

The stderr line (printed whenever config contributed anything beyond
defaults, naming the file); the alias for `baseline --candidate` (via
the same resolver, not a copy); the envelope wording gated on a
non-zero delta (with whatever rounding threshold the existing
significance rules already use).

## Out of Scope

- Making builders/max-jobs sticky (UX-126 declined with reasons; that
  decision stands).

## Acceptance Test

A snapshot with a non-default `.bga/config` prints the line; one with
defaults prints nothing extra; `bga baseline --candidate @last` works
from inside a project; a zero-delta envelope renders "unchanged" and
the golden fixture pins it.
