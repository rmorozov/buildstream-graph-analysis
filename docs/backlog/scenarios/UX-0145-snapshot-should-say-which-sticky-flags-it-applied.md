# UX-145: snapshot should say which sticky flags it applied

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-126 (done — these are its surprise edges) | **Topic:** cli

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


---

## What was built

1. **Sticky flags say themselves**, and only when they change something:

   ```text
   Using /path/to/project/.bga/config: --trace-spine=off
   ```

   Printed when the stored config differs from the defaults *and* the
   user did not pass that flag on this invocation — a flag on the command
   line they just typed is neither news nor "remembered". A project at
   the defaults prints nothing.
2. **`bga baseline --candidate` takes `@last`**, through
   `run_store.resolve` rather than a copy of it, resolved before anything
   is fetched. It was outside `bga.cli`'s threading for the same reason
   `cache-logs --native-report` was (`UX-134`): the command dispatches
   straight to `tools/`.
3. **The envelope note no longer claims a direction it cannot show.**
   `memory_envelope_direction()` returns `unchanged` for a delta that
   rounds to zero at the one decimal of GB the line prints — the observed
   *"Memory envelope grew: 0.6 GB -> 0.6 GB (+0.0 GB, +0%)"*.

The direction rule is a named function rather than an expression inline,
because the first attempt at a test reimplemented the condition in the
test file and therefore tested itself. A guard now asserts the renderer
calls it.
