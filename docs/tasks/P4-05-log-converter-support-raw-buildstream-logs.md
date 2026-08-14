# P4-05: `tools/bst_log_to_chrome_trace.py` only supports wrapper-prefixed logs, not raw BuildStream logs

**Priority:** P4 | **Status:** 🔴 Not Started | **Depends on:** none

## Spec Reference
Not spec-mandated directly (this tool is upstream of bga's own ingestion, Part 32's trace/v9 is the actual contract) - but it's the only real BuildStream-log-to-trace conversion path in this repo (`tests/fixtures/synthetic_multi_subproject/` relies on it), so its input coverage directly affects how usable `bga` is against a real project.

## Current Broken/Narrow Behavior (confirmed by reading `tools/bst_log_to_chrome_trace.py`)
Every line must match `PREFIX_RE = r"^\[.*?\]\s*\[(.*?)\]\s*[A-Z]+:\s*(.*)$"` (`tools/bst_log_to_chrome_trace.py:20`) *before* `process_line` even attempts to look for a BuildStream log line inside it - this is the CI wrapper's own outer prefix (`[tag][UTC timestamp] LEVEL: message`), not anything BuildStream itself emits. A raw, unwrapped BuildStream log line like:
```
[00:00:00][a59d6897][   build:my_package.bst] SUCCESS Staging dependencies at: /
```
does not match `PREFIX_RE` at all (there's no `[A-Z]+:` LEVEL-with-colon segment before the message) - `process_line` returns immediately for every such line, and the converter silently produces an **empty trace** (just the metadata events, zero `bst-builder`/`bst-invocation` spans) rather than erroring or actually parsing it. Confirmed by inspection of `PREFIX_RE` against `BST_LOG_RE`'s own documented example format (`tools/bst_log_to_chrome_trace.py:28`) - they're structurally incompatible as a single combined pattern.

There's also a real semantic gap, not just a regex fix: the wrapper's outer `[UTC timestamp]` gives an absolute epoch anchor (`parse_timestamp`, `%Y-%m-%d %H:%M:%S,%f`); BuildStream's own inner `[00:00:00]` prefix is *elapsed time since the bst invocation started*, not a wall-clock timestamp - a raw log has no absolute time anchor at all. Any raw-log support needs to either accept a `--start-time` (or default to file mtime / "now") to convert BuildStream's own elapsed `HH:MM:SS[.ffffff]` into absolute microseconds, or produce trace/v9-relative timestamps directly (0-based) - bga's `run-context.wall_clock` doesn't strictly require real epoch time, it just needs internal consistency (Part 3.1: microsecond integers, no particular epoch mandated).

## Required Fix
1. Decouple the two parsing layers currently fused together: (a) optional wrapper-prefix stripping (`PREFIX_RE`, `EXEC_CMD_RE`, `RETURN_CODE_RE` - all wrapper-specific), and (b) `BST_LOG_RE` matching against whatever's left. Try `BST_LOG_RE` directly against each raw line when there's no wrapper prefix, instead of requiring the wrapper layer to have already stripped one.
2. Add an explicit `--format {auto,wrapped,raw}` CLI flag (default `auto`: try wrapped-prefix parsing first per line, fall back to direct `BST_LOG_RE` matching) - don't silently guess in a way a user can't override, and don't make raw-log support regress the existing, working wrapped-log path (`tests/fixtures/synthetic_multi_subproject/` must keep working byte-for-byte the same afterward).
3. Design and document the raw-log timestamp anchor decision from the paragraph above (probably a `--start-time` flag defaulting to the log file's mtime, converting BuildStream's own `[HH:MM:SS(.ffffff)]` elapsed prefix into absolute microseconds from that anchor).
4. Update the module's own docstring (currently says "Parses a wrapper script's log output" unconditionally, `tools/bst_log_to_chrome_trace.py:2-12`) once both modes are real.

## Out of Scope
- Don't change the wrapped-log path's existing behavior or output shape - `tests/test_synthetic_multi_subproject.py` pins it, and it's the one currently-verified-working path.
- Don't build the graph/v9-from-BuildStream-project-metadata half of the pipeline (element dependency graph, cache keys) - this tool only produces Chrome Trace (trace-shaped) output; the graph.json side is a separate, larger gap (see the brainstormed backlog note on the missing end-to-end ingestion path).

## Acceptance Test
1. A raw (unwrapped) BuildStream log sample produces real `bst-builder`/`bst-invocation` trace events (not an empty trace) with `--format raw`, and `--format auto` correctly detects it without the flag.
2. The existing wrapped-log fixture (`tests/fixtures/synthetic_multi_subproject/`) still produces byte-identical Chrome Trace output after this change (`--format auto` or `--format wrapped` on it, diffed against the current output).
3. A new test file (e.g. `tests/unit/test_bst_log_converter.py`) covers both formats with hand-built log samples of each kind, plus the elapsed-time-to-absolute-microseconds conversion specifically.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
