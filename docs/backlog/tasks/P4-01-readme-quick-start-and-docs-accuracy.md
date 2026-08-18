# P4-01: README quick-start (Pareto principle) + fix stale/broken doc examples

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** none

## Spec Reference
Not spec-mandated — usability/documentation. `docs/guides/cli.md` and `README.md` should describe the CLI as it actually is today (Part 37's full subcommand list, `--cold`/`--diagnostics`/`--capacity`/`--replay`, exit codes).

## Current State (confirmed by reading, not guessing)
- `README.md`'s Quick Start (`README.md:43-61`) never shows how to get a run directory `bga` can actually read in the first place - it jumps straight to `bga analyze /path/to/buildstream/cache/artifacts/run-<uuid>`, implying a raw BuildStream artifact-cache path is directly consumable. It is not: `bga` reads a directory containing `run-context.json`/`graph.json`/`trace.json` (v9 schema, Part 32), which nothing in this repo produces directly from a live BuildStream cache. A brand-new user following the README literally has no path from "I ran BuildStream" to "I have a report."
- The "Example Output" block (`README.md:70-86`) doesn't match real `bga analyze` text output (compare against `bga/report/text.py::format_text` - it's missing the Attribution Breakdown's real category names/percentages format, and omits `confidence`/`violations` entirely since - see `P4-02` - those aren't in text output today either).
- `docs/guides/cli.md`'s example workflows have two confirmed-broken commands:
  - `docs/guides/cli.md:130`: `jq '.floors.certified_headroom_us'` - the real JSON field (confirmed via `bga analyze <fixture> --format json`) is `certified_headroom`, no `_us` suffix. This `jq` command returns `null` today.
  - `docs/guides/cli.md:147`: `jq '.signals.criticality_probability | sort_by(.probability) | reverse | .[0:10]'` - `criticality_probability` is a JSON *object* keyed by element UID (`{"a.bst": {"probability": ...}}`), not an array; `sort_by`/array-slicing on it fails in `jq` as written. Needs `to_entries` first.
- `pyproject.toml`'s `[project.urls]` (`pyproject.toml:38-42`) are placeholder `your-org/bga` URLs.

## Required Fix
1. Rewrite `README.md`'s Quick Start section around the Pareto principle: the smallest number of commands that gets a first-time user from zero to a report. Concretely: point at a checked-in fixture that already exists and needs no real BuildStream project (`tests/fixtures/golden/mixed_task_kinds/` from `P3-08`, or the synthetic multi-subproject fixture) as the "try it right now" path, e.g. `pip install -e . && bga analyze tests/fixtures/golden/mixed_task_kinds`, then a short pointer to `tools/bst_log_to_chrome_trace.py` (see `P4-05`) for real data, honestly scoped to what that tool currently does.
2. Fix the two broken `jq` examples in `docs/guides/cli.md` (confirm the correct field names/shapes against a real `--format json` run before writing the fix, don't guess).
3. Regenerate the "Example Output" block from a real `bga analyze` run against a checked-in fixture, not hand-written prose.
4. Fix the placeholder GitHub URLs in `pyproject.toml` if the real repo URL is known (`rmorozov/buildstream-graph-analysis` per this session's own PR history) - trivial, but currently just wrong.

## Out of Scope
- ~~Building a real ingestion path from a live BuildStream cache to a v9 run directory~~ - this note is now stale: that pipeline was built (`P4-05`/`P4-08`/`P4-09`/`P4-10`, `tools/bst_extract_run.py`). This task's own fix documents it honestly in the Quick Start rather than inventing a pipeline - it just no longer needs inventing, it exists.
- Redesigning report content/structure - that's `P4-02`.

## Acceptance Test
1. A person with no prior context can `pip install -e .` and produce a report by copy-pasting the Quick Start section verbatim, with every command actually working.
2. Every `jq` example in `docs/guides/cli.md` produces real, non-null, correctly-shaped output when run against a real `--format json` report.
3. `pyproject.toml`'s URLs resolve to the real repo (or are removed if genuinely unknown, not left as `your-org` placeholders).

## What was built
- `README.md`'s Quick Start rewritten around the Pareto principle: two commands (`pip install -e .` + `bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics`, `P3-08`'s checked-in fixture) get a first-time user to a real report with zero BuildStream install needed, plus a pointer to `make dev-run`. A second block honestly documents the now-real path from an actual BuildStream project + build log to a `bga`-ready run directory via `tools/bst_extract_run.py` (`P4-10`) - this used to be genuinely out of scope/nonexistent; it isn't anymore.
- `docs/guides/cli.md`'s "Basic Usage" section no longer implies a raw BuildStream cache/artifacts path is directly `bga`-readable (`/path/to/buildstream/cache/artifacts/run-<uuid>` → `/path/to/run-directory`, with an explicit "not a raw cache path" note and a pointer to `tools/bst_extract_run.py`).
- Both confirmed-broken `jq` examples in `docs/guides/cli.md`'s "Example Workflows" fixed and verified against a real `--format json` run: `.floors.certified_headroom_us` (nonexistent, silently returns `null`) → `.floors.certified_headroom`; `.signals.criticality_probability | sort_by(...)` (fails - that field is a JSON object keyed by element UID, not an array) → `.signals.criticality_probability | to_entries | sort_by(.value.probability) | reverse | .[0:10]`. The example workflow paths were also changed from the same misleading raw-cache-path pattern to an honest `/path/to/run-directory` placeholder.
- `README.md`'s "Example Output" block regenerated from a real `bga analyze` run against the checked-in fixture (previously hand-written prose that didn't match `format_text`'s real output shape at all - wrong header format, wrong field labels, and predating `P4-02`'s Key Findings/Confidence blocks entirely).
- `pyproject.toml`'s `[project.urls]` fixed from placeholder `your-org/bga` to the real `rmorozov/buildstream-graph-analysis` repo.
- Added `tests/unit/test_docs_examples.py` (6 tests) as permanent regression coverage - runs the README's Quick Start command for real, confirms the real JSON field shapes both `jq` examples depend on, and (when `jq` is on `PATH`) runs both fixed `jq` commands for real against a live report.

## Verification Log
```
$ pip install -e . -q && bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics
============================================================
Build Efficiency Report
...
$ echo $?
0

$ PYTHONPATH=. python3 -m bga.cli analyze tests/fixtures/golden/mixed_task_kinds --format json --diagnostics > /tmp/report.json
$ jq '.floors.certified_headroom_us' /tmp/report.json   # the old, broken example
null
$ jq '.floors.certified_headroom' /tmp/report.json      # the fixed example
0
$ jq '.signals.criticality_probability | sort_by(.probability) | reverse | .[0:10]' /tmp/report.json   # old, broken
jq: error (at /tmp/report.json:274): object (...) and array (...) cannot be sorted, as they are not both arrays
$ jq '.signals.criticality_probability | to_entries | sort_by(.value.probability) | reverse | .[0:10]' /tmp/report.json   # fixed
[{"key": "app.bst", "value": {"probability": 1.0, ...}}, ...]

$ PYTHONPATH=. python3 -m pytest tests/unit/test_docs_examples.py -v
6 passed

$ PYTHONPATH=. python3 -m pytest tests/ -q
336 passed (with bst on PATH)

$ make check-clean
OK: no ignored files are tracked
```
