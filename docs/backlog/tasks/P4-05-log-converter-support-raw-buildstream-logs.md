# P4-05: `tools/bst_log_to_chrome_trace.py` only supports wrapper-prefixed logs, not raw BuildStream logs

**Priority:** P4 | **Status:** 🟢 Fixed & Verified (2026-08-14) | **Depends on:** none

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

## What was built
Added `--format {auto,wrapped,raw}` and `--start-time` to `tools/bst_log_to_chrome_trace.py`. Decoupled wrapper-prefix stripping from `BST_LOG_RE` matching (`process_line_wrapped`/`process_line_raw`, `process_line` for `auto`). Raw mode synthesizes its own `bst-invocation` span (no wrapper `Executing command:` line exists to trigger one) and converts BuildStream's own elapsed `[HH:MM:SS(.ffffff)]`/`--:--:--` prefix into absolute microseconds anchored at `--start-time` (default: input file mtime).

**Two real bugs found while implementing, verified against a real, installed BuildStream 2.7.0** (not assumed from the log line shape alone - see `docs/spec/ingestion-pipeline.md`'s "Empirically confirmed facts about real BuildStream logs" for the full list):
1. The status-word alternation had `FAIL`, not the real `FAILURE` - a real build failure never matched at all, in *either* mode, silently leaving the task open forever. Invisible against the synthetic fixture, which never generates a failing build. Fixed (kept `FAIL` too, for tolerance).
2. A real BuildStream task emits an *outer* START/terminal bracket plus nested START/terminal pairs for internal sub-phases sharing the identical hash+action key - the prior "new START force-closes whatever's open" handling would have produced 2-3 spurious spans per real task instead of one. Fixed via a per-(hash, action) depth counter.

Also added, needed for `P4-09`/`P4-10` to work from a single real log parse: capturing BuildStream's own `Maximum {Fetch,Build,Push} Tasks:` header lines (`get_scheduler_config()`) and its `Targets:` header line (`converter.targets`), plus recording each event's `action`/`element` directly in Chrome Trace `args` (additive, so the pinned synthetic-fixture output is unaffected) rather than requiring message-text parsing downstream.

## Out of Scope (unchanged from original scope, now more precisely true)
- The wrapped-log path's Chrome Trace *output shape* (event fields, `name` construction, `ph`/`ts`/`pid`/`tid`) is unchanged for the synthetic fixture - verified byte-identical (see Verification Log). `args` gained new additive keys (`action`, `element` on builder events) that nothing in the synthetic fixture's own adapter reads.
- `tools/chrome_trace_to_bga_trace.py` (the Chrome-Trace-to-trace/v9 conversion) was built as a separate, new, general-purpose tool - not folded into this one, and not the same as the synthetic fixture's own `adapter.py`. See `docs/spec/ingestion-pipeline.md`'s "Why a second, separate trace/v9 adapter" section.

## Verification Log
```
$ PYTHONPATH=. python3 -m pytest tests/unit/test_bst_log_converter.py -v
23 passed

$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py -v
16 passed   # byte-identical wrapped-mode output confirmed, including the
            # checked-in-fixture diff test (test_checked_in_fixture_matches_current_model)

# Real raw-log run against a real BuildStream 2.7.0 build
# (tests/fixtures/bst_show_project/, `bst build app.bst`):
$ PYTHONPATH=. python3 tools/bst_log_to_chrome_trace.py --format raw real_build.log chrome_trace.json
$ python3 -c "import json; ev=json.load(open('chrome_trace.json')); \
  b=[e for e in ev if e.get('cat')=='bst-builder' and e['ph']=='B']; print(len(b))"
6   # fetch base, fetch base2, build base, build base2, build app, + 1 main pseudo-task
    # - no spurious nested-sub-phase spans, confirming the depth-counter fix

$ PYTHONPATH=. python3 -m pytest tests/ -q
311 passed (with bst on PATH) / 307 passed, 4 skipped (without)   # was 261/2

$ make check-clean
OK: no ignored files are tracked
```
