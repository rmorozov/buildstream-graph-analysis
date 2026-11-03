# UX-1376: `correlate` on a run with no Plane 2 answers in the format it was asked for

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** walk seed 6 (2026-11-03) | **Serves:** R3 | **Topic:** cli | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

[`walk-seed-6.md`](../../audits/walk-seed-6.md) finding 3: `bga correlate
inc --format json` on a Plane 1-only run exits 2 with 0 bytes on stdout and
a text error that says to pass a Plane 2 report or use `@last`. A run
captured without Plane 2 has neither, and a script asking for JSON gets no
JSON to read.

## Decomposition

Input classes: Plane 2 absent, beside and passed; `--format` json and text.
Journey: extends the walk's seed 6 class (Plane 2 absent).

## Required Fix

Under `--format json`, the refusal is a JSON object naming the reason; the
text names what the run lacks (it was captured without Plane 2) before what
to pass.

## Out of Scope

Inferring Plane 2 facts from Plane 1.

## Acceptance Test

`bga correlate <plane1-only run> --format json` prints one JSON object with
the reason on stdout and exits non-zero; the mutation that prints the text
error instead reddens the guard.

## Outcome
