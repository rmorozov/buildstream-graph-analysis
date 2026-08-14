# P4-07: Mark the original compliance review as a historical snapshot, not current state

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated - documentation hygiene. Brainstormed while scoping the other `P4` usability tasks.

## Current State
`docs/bga-spec-compliance-review.md` is the original review that kicked off this whole multi-round fixing effort - at the time it was written, it accurately reported the CLI as completely non-functional (constructor mismatch, undeclared `networkx` dependency, etc., its own P0 section). That description is no longer true - `docs/fix-progress-tracker.md` now shows every P0/P1/P2/P3 item resolved and verified. A new contributor who opens `docs/bga-spec-compliance-review.md` first (it's alphabetically first in `docs/`, and a natural thing to read given its name) would form a badly wrong impression of the tool's current state, since nothing in that file itself says "this was the state as of the start of the fixing effort - see the tracker for current status."

## Required Fix
Add a short, prominent note at the very top of `docs/bga-spec-compliance-review.md` (before the executive summary) stating it's a historical snapshot from before the fixing effort described in `docs/fix-progress-tracker.md`, with a link to that tracker for current status. Don't rewrite or delete the review's content - it remains useful as a historical record of what was found and why the tracker's task decomposition looks the way it does.

## Out of Scope
- Don't touch `docs/fixing-guide.md` or `docs/fix-progress-tracker.md` - both are already living documents that describe current state accurately.
- Don't delete or move the file to an `archive/` subdirectory unless the team has a stated convention for that - a header note is the minimal, low-risk fix.

## Acceptance Test
Opening `docs/bga-spec-compliance-review.md` cold, without any other context, makes it immediately clear (within the first few lines) that it's a historical document and where to find current status.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
