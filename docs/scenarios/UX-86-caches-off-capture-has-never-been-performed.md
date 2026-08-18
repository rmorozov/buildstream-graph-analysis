# UX-86: the caches-off scenario has never been captured, so half the product is untested on real data

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-81 (infrastructure), UX-55 (done)

## Motivation

Round 9's honest gap, still open and still admitted in three documents:
*every real capture so far is incremental*. The published fdsdk
critical path is the chain through the 25 rebuilt elements, not the
project's real one; coverage, floors, and both efficiency signals have
never been exercised against a full cold build of a real project. The
"caches-off nightly" is one of the two CI scenarios the tool's own
design doc argues it serves — and it is the one where the whole-graph
structural findings (blast radius, choke points, stack consolidation)
mean what they claim.

The workflow's warm-then-cut design exists because a full fdsdk cold
build cannot fit a runner. That constraint bounds the *target*, not the
scenario: a cold capture of a bounded subtree (the existing 25-element
cut built with an empty local cache and remotes ignored from the start,
rather than on top of a warmed base) — or a smaller real project built
cold end-to-end — both produce a genuine caches-off run.

## Required Fix

1. Add a `capture_mode: cold` input to
   `.github/workflows/real-project-capture.yml`: skip the warm phase,
   build the chosen target with empty caches and
   `--ignore-project-artifact-remotes`, publish with `run_mode`
   provenance alongside (not over) the incremental captures (UX-81's
   history makes this non-destructive).
2. Pick a target that fits the 250-minute budget by measurement (start
   from the existing cut set; shrink if needed).
3. Run `bga analyze` + `correlate` on the result in-job, as today, and
   record the first real cold-vs-incremental pair — which is also the
   first real input `bga compare`'s cache-scenario check (UX-78) has
   ever had.

## Out of Scope

- A full 1089-element fdsdk cold bootstrap (does not fit a runner; the
  scenario does not need it).
- Scheduling cadence (UX-81).

## Acceptance Test

One published cold capture whose `run-context` records the mode, with
zero cached elements in its closure, analyze confidence "high", and no
incremental-run caveat in the report. `docs/real-project-guide.md`'s
"the honest gap" paragraph updated to point at the capture instead of
apologizing for its absence.
