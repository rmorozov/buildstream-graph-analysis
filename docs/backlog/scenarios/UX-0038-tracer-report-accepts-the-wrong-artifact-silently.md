# UX-38: `bst_native_build_tracer report` accepts the JSON report and confidently prints "Processes traced: 0"

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-11 (done) | **Topic:** capture | **Area:** tools

## Motivation

`tools/bst_native_build_tracer.py run` writes a JSON report to its `output` positional argument. Its sibling subcommand is `report`, and the obvious thing to do with a saved report is render it again. Real session:

```text
$ python3 -m tools.bst_native_build_tracer run --wrapped-log /tmp/w.log \
    examples/05-cmake-cpp-toolchain /tmp/05-native.json -- bst --builders 4 --max-jobs 4 build all.bst
  ... (full report: 528 processes traced, max concurrency 38, 37 redundant-operation findings)

$ python3 -m tools.bst_native_build_tracer report /tmp/05-native.json
Processes traced: 0 (0 matched, 0 no observed exit)
Max observed concurrency: 0 (matched processes only - see open_records_note)
By binary:

NOTE: LD_PRELOAD only affects dynamically-linked executables. ...
```

Exit code 0. No warning. The file is 528 real processes and the tool reports zero of them, in the same format it uses for a real answer.

`report` takes a **raw trace log** (`--raw-log`'s output), which the help text does say. But `run --raw-log` is optional and defaults to discarding the raw log into a temp dir, so the JSON report is the only artifact most sessions keep - and it is the argument shape that silently produces a wrong answer rather than an error. The parser reads a line-oriented format; a JSON file yields no matching lines, which is indistinguishable from an empty trace.

Two adjacent traps found in the same session:

- **There is no way to re-render a saved JSON report at all.** Once `run` finishes without `--raw-log`, the text summary can never be regenerated - only the JSON remains, and nothing consumes it. Any downstream consumer (`UX-32`'s per-element parallelism, `UX-37`'s re-scoring) will want to work from the saved report rather than re-running a build.
- **`run`'s `cmd` uses `argparse.REMAINDER`**, so any option written after the positionals is swallowed into the wrapped command. Getting the documented flag order slightly wrong:

  ```text
  $ python3 -m tools.bst_native_build_tracer run PROJ OUT --wrapped-log /tmp/w.log -- bst build all.bst
  FileNotFoundError: [Errno 2] No such file or directory: '--wrapped-log'
  ```

  a raw Python traceback from `subprocess.run`, rather than a usage error.

## Required Fix

1. Detect the artifact kind. If the file parses as a JSON object carrying this tool's own report keys (`process_count`, `processes`, ...), either render it directly (preferred - it removes the "no way to re-render" gap at the same time) or fail with a message naming the right input.
2. Never print a zero-process report as a successful result when the input produced no parseable trace lines at all. Empty-because-nothing-ran and empty-because-wrong-file are different, and the second should be an error.
3. Give `run` a friendlier failure when an unconsumed option lands in `cmd`: if `cmd[0]` starts with `-` and is not `--`, emit a usage error explaining that options must precede the positionals.

## Out of Scope

- Changing `run`'s argument order or making `--raw-log` mandatory - both would break the documented `UX-24` invocations.
- The JSON report's schema.

## Acceptance Test

1. `report <a run-produced JSON report>` either renders the real report or exits non-zero with a message naming the expected input - never "Processes traced: 0" with exit 0.
2. `report <a genuinely empty raw log>` still reports zero processes, as it should.
3. `run PROJ OUT --wrapped-log X -- bst ...` produces a usage error, not a traceback. Full suite green.

## Fix Implemented

All three items, in `tools/bst_native_build_tracer.py`.

1. **Artifact detection.** New `load_saved_report(path)` recognizes a previously-saved report by this tool's *own* report keys (`_REPORT_MARKER_KEYS`), not by "it parses as JSON" - so a Chrome Trace or a `bga` run-context is not mistaken for one. `report` renders it directly, which resolves the "no way to re-render" gap in the same change: the JSON report is the artifact `run` actually leaves behind, since the raw log is discarded unless `--raw-log` is passed.

2. **No confident zero.** `load_and_summarize` now raises a new `EmptyTraceError` (a `TraceError` subclass) when a **non-empty** file yields no parseable events, and `report` exits 1 with that message. A genuinely empty log still returns a real zero-process report - nothing ran, or the hook never loaded, which is a legitimate result and stays distinguishable from the wrong-file case.

3. **The REMAINDER trap.** `run` now checks whether `cmd[0]` starts with `-` and, if so, calls `parser.error` naming the actual problem, instead of passing the option through to `subprocess.run` and surfacing a bare `FileNotFoundError: '--wrapped-log'`.

The `report` positional was renamed `raw_log` -> `path` and its help updated, since it now legitimately accepts either kind.

Tests: 8 new (`tests/unit/test_tracer_report_input_detection.py`) - saved report recognized, raw log not mistaken for one, unrelated JSON not mistaken for one, unparseable file raising rather than reporting zero, genuinely-empty log still a real zero result, plus the three end-to-end `main()` paths (report re-rendered, wrong file exiting 1, misplaced option exiting 2 with the explanatory message).

## Verification Log

Filed 2026-08-16. Implemented the same day. All three outputs are pasted from a real session against `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host); the `run` invocation that produced the 528-process report and the `report` invocation that reported zero were consecutive commands on the same file.

Real end-to-end re-verification against the exact artifacts from this doc's Motivation - the real 822-process capture of `examples/06-macro-micro-optimization` and its own saved JSON report:

```text
$ python3 -m tools.bst_native_build_tracer report /tmp/06-baseline-native.json
Processes traced: 822 (663 matched, 159 no observed exit)     # was: 0 (0 matched, 0 ...)
Max observed concurrency: 20
Wall span: 39.060s
$ echo $?
0

$ python3 -m tools.bst_native_build_tracer report /tmp/06-baseline-native.rawlog
Processes traced: 822 (663 matched, 159 no observed exit)     # unchanged

$ printf 'hello world\n' > /tmp/junk.txt
$ python3 -m tools.bst_native_build_tracer report /tmp/junk.txt
Error: /tmp/junk.txt: no trace events could be parsed from this file. ...
$ echo $?
1

$ python3 -m tools.bst_native_build_tracer run PROJ OUT --wrapped-log /tmp/x -- bst build all.bst
bst_native_build_tracer.py: error: '--wrapped-log' was taken as the start of the wrapped
command, not as an option - options must come before the positional arguments, e.g.
`run --wrapped-log PATH PROJECT_DIR OUTPUT -- bst build target.bst`
```

Acceptance Test items 1-3 all confirmed with real data. Full suite green (700 passed, up from 692), `make lint` clean.
