# P1-17: Terminology audit against spec Part 43 avoid-list

**Priority:** P1 (low risk, quick — good task for a very small context budget) | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** none

## What was found
Zero matches for any Part 43 avoid-list term anywhere in `bga/`, `docs/guides/cli.md`, or `README.md`. No code change was needed - the codebase was already clean.

## Spec Reference
Read only: `sed -n '2674,2712p' docs/spec/specification.md` (Part 43 — Terminology). It lists preferred terms (e.g. "Measured blame-chain attribution," "Occupancy step function," "Trace epsilon," "Certified headroom") vs. an explicit "avoid" list (e.g. "Interval eclipsing," "Mathematically optimal schedule," "Cold floor as certified bound," "Resource blocker as causal predecessor").

## Current State
Not yet audited. This is a quick grep-and-fix task, not a design task.

## Required Fix
1. `grep -rniE "interval eclipsing|mathematically optimal|cold floor.*certified|resource blocker" bga/ docs/guides/cli.md README.md` (adjust the pattern list to match the full avoid-list from Part 43 exactly — read it first, don't guess the terms).
2. For every match in user-facing output strings (CLI help text, report formatting strings, docstrings that get surfaced to users, README/docs/guides/cli.md prose), replace with the preferred equivalent term from the same Part 43 table.
3. Do **not** change matches inside code comments that are purely internal/historical (e.g. referencing why something was avoided) unless they're misleading — use judgment, but bias toward leaving internal comments alone and fixing only user-facing text.

## Out of Scope
- Don't touch `docs/spec/specification.md` itself (never edit the spec, per `docs/contributing/fixing-guide.md` §5).
- Don't rename internal function/variable names as part of this task unless a name directly surfaces as user-facing text (e.g. a `--flag` name or JSON key) — that's a much bigger, riskier change and out of scope here.

## Acceptance Test
Re-run the grep from step 1 — zero matches remaining in user-facing strings (CLI output, `docs/guides/cli.md`, `README.md`). Paste the before/after grep output into the Verification Log.

## Verification Log
```
$ grep -rniE "interval eclipsing|absolute graph time|pure configuration overhead|mathematically optimal|exact runtime inefficiency|true minimum build time|cold floor.*certified|resource blocker.*causal" bga/ docs/guides/cli.md README.md
(no output - zero matches)
```
