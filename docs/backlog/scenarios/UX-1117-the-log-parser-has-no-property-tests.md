# UX-1117: the scheduler-log parser is tested only on the logs someone thought to write

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose BuildStream version prints a line the fixtures never held | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_log_reader_holds_its_properties.py, absent from tests/

## Motivation

Plane 1 is parsed from free text (`tools/bst_log_to_chrome_trace.py`,
`handle_bst_event`, `parse_timestamp`, `parse_elapsed_to_seconds`); the suite
has golden and hand-written fixtures and no generated inputs — `hypothesis`
is not in the dev extra, and no test file generates log lines.

## Decomposition

Input classes: well-formed interleaved event lines; lines the grammar does not match; elapsed strings of every width; timestamps across midnight.
Journey: Plane 1 ingest in `bga analyze`.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `hypothesis` in the dev extra and requirements.lock. New small test over `WrapperTraceConverter`: raw mode `process_line_raw` (raw_start_time_us=0), wrapped mode `process_line` after an `Executing command: bst build x.bst` line. Properties: (1) balanced START/terminal pairs over distinct hashes, elements padded "", " ", "  ", give one B and one E per hash on its tid with E.ts >= B.ts, both modes, wrapped timestamps nondecreasing across midnight, under TZ=UTC; (2) a line BST_LOG_RE does not match never raises and adds no span; (3) elapsed strings round-trip and "--:--:--" is 0.0. Profile in the module: `derandomize=True, database=None, max_examples=100`
Rejected:  the row's "counted" clause - no counter exists and every build-output line is unmatched, so a count is noise (the Outcome records it); importorskip (a skip nobody sees)
Files:     pyproject.toml ([dev]), requirements.lock, tests/unit/test_the_log_reader_holds_its_properties.py
Guard:     that file, properties (1)-(3), small tier
Mutation:  in handle_bst_event before the strip, `if status != "START" and element.endswith(" "): return` - (1) reddens
Class:     product. Finding for a new row: `parse_timestamp` (:292-298) reads the UTC wrapper stamp as local time (bst_run_wrapped.py:49 writes UTC); off by the TZ offset outside UTC
```

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
