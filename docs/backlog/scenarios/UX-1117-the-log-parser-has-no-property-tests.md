# UX-1117: the scheduler-log parser is tested only on the logs someone thought to write

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose BuildStream version prints a line the fixtures never held | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_log_reader_holds_its_properties.py, absent from tests/

## Motivation

Plane 1 is parsed from free text (`tools/bst_log_to_chrome_trace.py`,
`handle_bst_event`, `parse_timestamp`, `parse_elapsed_to_seconds`); the suite
has golden and hand-written fixtures and no generated inputs — `hypothesis`
is not in the dev extra, and no test file generates log lines.

## Decomposition

Input classes: well-formed interleaved event lines; lines the grammar does not match; elapsed strings of every width; timestamps across midnight.
Journey: Plane 1 ingest in `bga analyze`.

## Required Fix

`hypothesis` joins the dev extra. Property tests over the Plane 1 reader:
any interleaving of well-formed START/SUCCESS/FAILURE lines yields spans
that nest and never end before they start; any line the grammar does not
match is counted, not raised on; elapsed strings round-trip. A fixed
`derandomize` profile in CI so a run is reproducible.

## Out of Scope

The Plane 2 readers (a second row once this one's harness exists).

## Acceptance Test

`tests/unit/test_the_log_reader_holds_its_properties.py`. Mutation: make
the reader drop a SUCCESS whose element has a trailing space; the
generated-input property finds it within the default example budget.
