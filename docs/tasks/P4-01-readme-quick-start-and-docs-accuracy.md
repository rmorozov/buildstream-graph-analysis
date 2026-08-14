# P4-01: README quick-start (Pareto principle) + fix stale/broken doc examples

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated — usability/documentation. `docs/cli.md` and `README.md` should describe the CLI as it actually is today (Part 37's full subcommand list, `--cold`/`--diagnostics`/`--capacity`/`--replay`, exit codes).

## Current State (confirmed by reading, not guessing)
- `README.md`'s Quick Start (`README.md:43-61`) never shows how to get a run directory `bga` can actually read in the first place - it jumps straight to `bga analyze /path/to/buildstream/cache/artifacts/run-<uuid>`, implying a raw BuildStream artifact-cache path is directly consumable. It is not: `bga` reads a directory containing `run-context.json`/`graph.json`/`trace.json` (v9 schema, Part 32), which nothing in this repo produces directly from a live BuildStream cache. A brand-new user following the README literally has no path from "I ran BuildStream" to "I have a report."
- The "Example Output" block (`README.md:70-86`) doesn't match real `bga analyze` text output (compare against `bga/report/text.py::format_text` - it's missing the Attribution Breakdown's real category names/percentages format, and omits `confidence`/`violations` entirely since - see `P4-02` - those aren't in text output today either).
- `docs/cli.md`'s example workflows have two confirmed-broken commands:
  - `docs/cli.md:130`: `jq '.floors.certified_headroom_us'` - the real JSON field (confirmed via `bga analyze <fixture> --format json`) is `certified_headroom`, no `_us` suffix. This `jq` command returns `null` today.
  - `docs/cli.md:147`: `jq '.signals.criticality_probability | sort_by(.probability) | reverse | .[0:10]'` - `criticality_probability` is a JSON *object* keyed by element UID (`{"a.bst": {"probability": ...}}`), not an array; `sort_by`/array-slicing on it fails in `jq` as written. Needs `to_entries` first.
- `pyproject.toml`'s `[project.urls]` (`pyproject.toml:38-42`) are placeholder `your-org/bga` URLs.

## Required Fix
1. Rewrite `README.md`'s Quick Start section around the Pareto principle: the smallest number of commands that gets a first-time user from zero to a report. Concretely: point at a checked-in fixture that already exists and needs no real BuildStream project (`tests/fixtures/golden/mixed_task_kinds/` from `P3-08`, or the synthetic multi-subproject fixture) as the "try it right now" path, e.g. `pip install -e . && bga analyze tests/fixtures/golden/mixed_task_kinds`, then a short pointer to `tools/bst_log_to_chrome_trace.py` (see `P4-05`) for real data, honestly scoped to what that tool currently does.
2. Fix the two broken `jq` examples in `docs/cli.md` (confirm the correct field names/shapes against a real `--format json` run before writing the fix, don't guess).
3. Regenerate the "Example Output" block from a real `bga analyze` run against a checked-in fixture, not hand-written prose.
4. Fix the placeholder GitHub URLs in `pyproject.toml` if the real repo URL is known (`rmorozov/buildstream-graph-analysis` per this session's own PR history) - trivial, but currently just wrong.

## Out of Scope
- Building a real ingestion path from a live BuildStream cache to a v9 run directory - that gap is real (see the brainstormed backlog item on this) but is a product/architecture question, not a docs fix. Document what exists honestly rather than inventing a pipeline that doesn't.
- Redesigning report content/structure - that's `P4-02`.

## Acceptance Test
1. A person with no prior context can `pip install -e .` and produce a report by copy-pasting the Quick Start section verbatim, with every command actually working.
2. Every `jq` example in `docs/cli.md` produces real, non-null, correctly-shaped output when run against a real `--format json` report.
3. `pyproject.toml`'s URLs resolve to the real repo (or are removed if genuinely unknown, not left as `your-org` placeholders).

## Verification Log
_(append real command + output here once run, before marking 🟢)_
