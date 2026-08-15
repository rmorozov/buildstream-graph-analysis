# UX-04: "Biggest Opportunity" names a category but not what to do about it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** none

## Motivation

Filed while brainstorming `bga`'s main user scenarios, specifically first-run triage: "I just built my project, is it slow, where do I look first?" Confirmed against a real run (`bga analyze tests/fixtures/synthetic_multi_subproject --diagnostics`):

```
Key Findings:
  Biggest Opportunity: 5.6% of wall-clock time is IDLE (8.00s)
```

This correctly identifies the single largest attribution category, but a user unfamiliar with this tool's own category definitions (Part 11: `DEPENDENCY_WAIT`/`RESOURCE_WAIT`/`SCHEDULER_WAIT`/`IDLE`/`RETRY_WAIT`/...) has no way to know, from the report alone, that `IDLE` specifically means "no task was dependency-ready at all" (a graph-shape problem) as opposed to `RESOURCE_WAIT` ("ready, but a resource was saturated" - a capacity problem) or `SCHEDULER_WAIT` ("ready, capacity was free, but nothing got dispatched" - a scheduling-heuristic problem) - three categories with three completely different fixes, each spelled out precisely in the spec but not surfaced anywhere in the report itself.

## Required Fix

1. A small, static mapping (one line per `AttributionCategory`, presentation-only, no computation change) from category to a plain-language explanation plus a concrete next step, e.g.:
   - `DEPENDENCY_WAIT` → "waiting on an upstream element to finish - shorten or parallelize that dependency chain"
   - `RESOURCE_WAIT` → "a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try `--capacity N` with a higher N, or `bga sweep` to find the real knee point"
   - `SCHEDULER_WAIT` → "capacity was available but nothing was dispatched - try a different `--heuristic` in `bga replay`"
   - `IDLE` → "nothing was dependency-ready at all - likely a critical-path/graph-shape issue, not a capacity one; check Critical Path"
   - `RETRY_WAIT` → "this element needed a retry - investigate why the first attempt failed/was discarded"
   - `EXECUTION_ON_CHAIN` → "real work on the critical path - the only way to reduce this is to reduce the work itself"
2. Shown next to "Biggest Opportunity" in the text report's Key Findings block (`bga/report/text.py`), and as a `hint` field alongside each category in `--format json`'s attribution breakdown (additive key, doesn't change existing field names/values).
3. Keep the mapping's wording generic and structural (referencing the category's own defined meaning, e.g. via `docs/specification.md` Part 11) - not build-system-specific advice that might not apply to every project shape.

## Fix Implemented

`bga/report/_shared.py`'s new `ATTRIBUTION_CATEGORY_HINTS` dict (keyed by `AttributionCategory` enum member, one static string per category, all 8 values including `UNTRACKED_HEAD`/`UNTRACKED_TAIL` - not just the 6 this task's own motivation section named) plus `ATTRIBUTION_CATEGORY_HINTS_BY_KEY` (the same dict re-keyed by the lowercase `<category>_us` string `result.attribution`/`--format json` actually use) - a single source of truth for both:
- **Text report** (`bga/report/text.py`'s `_format_key_findings`): the hint for whichever category "Biggest Opportunity" names is appended as an indented `-> ...` line directly under it.
- **JSON report** (`bga/report/json.py`): a new, additive `attribution_hints` sibling key next to the existing `attribution` dict, using the same `<category>_us` keys - `attribution` itself is completely untouched (same field names/values as before).

No change to how any category is computed or classified - purely presentation.

## Out of Scope

- Any change to how attribution categories are computed or classified - this is presentation-only, one static string per category.
- Per-element (as opposed to per-category) hints - the existing "Elements Most Worth Optimizing First" list already does the per-element ranking; this task is about explaining the *category*, not re-ranking elements.

## Acceptance Test

1. Every `AttributionCategory` value has a non-empty hint string; a test enumerates the enum and asserts none are missing (a real guard against a future new category silently lacking one).
2. The text report's Key Findings block includes the hint for whichever category `Biggest Opportunity` names, verified against a real run's output.
3. `--format json` includes the hint field in the attribution section without changing any existing field.
4. Full suite green.

## Verification Log

Done for real, 2026-08-15. New tests: `tests/unit/test_attribution_hints.py` (4 tests - every `AttributionCategory` has a non-empty hint, `ATTRIBUTION_CATEGORY_HINTS_BY_KEY` covers exactly the 8 real `result.attribution` keys, the text report shows the correct hint directly under "Biggest Opportunity" for a dominant `DEPENDENCY_WAIT` fixture, and `--format json`'s new `attribution_hints` key is present without changing the existing `attribution` field's keys/values). Golden fixture (`tests/fixtures/golden/mixed_task_kinds`) regenerated via the file's own documented command, diff reviewed (only the new `attribution_hints` block plus a harmless key-reorder from Python dict construction order). Full suite green (`make lint`, `pytest` - 494 passed, same 7 pre-existing environment-only failures as `main`).

Real re-verification against this task's own cited command: `bga analyze tests/fixtures/synthetic_multi_subproject --diagnostics` now prints:
```
  Biggest Opportunity: 5.6% of wall-clock time is IDLE (8.00s)
    -> nothing was dependency-ready at all - likely a critical-path/graph-shape issue, not a capacity one; check Critical Path
```
