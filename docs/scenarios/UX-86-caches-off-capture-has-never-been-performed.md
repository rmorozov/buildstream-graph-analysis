# UX-86: the caches-off scenario has never been captured, so half the product is untested on real data

**Priority:** Medium | **Status:** 🟡 In Progress — mechanism shipped, capture not yet taken | **Depends on:** UX-81 (done), UX-55 (done)

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

## Fix Implemented (part 1 of 2: the mechanism)

`capture_mode: cold` exists and is dispatchable. In that mode the
workflow:

- **skips the warm and cut phases entirely** — "cold" means no cached
  base, so every step that reads `state-after-warm.txt` is conditioned
  rather than handed an empty file to draw conclusions from;
- **pre-fetches every source in the closure** (`source fetch --deps all`)
  for the same reason the incremental path pre-fetches the cut set: the
  timed build should be dominated by real build work, not by downloads;
- **fails fast if anything is cached at the start** — a cold capture with
  a warm cache is not a cold capture, and finding that out from the
  numbers afterwards is much worse than finding out in twenty seconds;
- **records `capture_mode` in `capture-context.txt`**, so what was *asked
  for* is visible beside the `run_mode` the run directory derives from
  BuildStream's own Pipeline Summary. A cold capture that silently found
  a warm cache then shows up as a disagreement rather than as a fact;
- **publishes to its own pointer** (`captures/fdsdk-cold-latest`) and
  carries the mode in its per-run ref name, so a cold and an incremental
  capture of the same commit — which measure different builds, and which
  `bga compare` refuses to compare (`UX-78`) — cannot land in one
  baseline set through a shared ref glob.

## What is not done, and why

**No cold capture has been taken.** That needs a GitHub runner and hours
of it, which this session does not have; the acceptance test's *"one
published cold capture"* is not met and this task stays open until it is.

The open question the first dispatch answers is Required Fix item 2:
**which target fits the budget.** The default (`components/libxml2.bst`)
certainly does not — freedesktop-sdk roots everything in a full compiler
bootstrap, which is the constraint that produced warm-then-cut in the
first place. The mechanism is deliberately target-agnostic so that
question can be answered by measurement rather than by argument: dispatch
with `capture_mode: cold` and a small target, read the wall clock,
adjust.

Nothing about the mechanism can be verified beyond YAML validity and a
read of the conditions until that dispatch happens, and this task should
be re-checked against a real cold capture rather than closed on the code.

## Verification Log

Mechanism added 2026-08-18; YAML validated, step conditions and the
publish path read directly. No cold capture has been produced, and the
"honest gap" paragraphs in `README.md`, `docs/real-project-guide.md` and
`docs/architecture.md` are deliberately **unchanged** — they will be
accurate until a cold capture exists, and editing them first would be
the exact kind of documentation-ahead-of-code this round's `UX-88` was
filed for.
