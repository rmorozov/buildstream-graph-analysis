# UX-38: `bst_native_build_tracer report` accepts the JSON report and confidently prints "Processes traced: 0"

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-11 (done)

## Motivation

`tools/bst_native_build_tracer.py run` writes a JSON report to its `output` positional argument. Its sibling subcommand is `report`, and the obvious thing to do with a saved report is render it again. Real session:

```
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

  ```
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

## Verification Log

Filed 2026-08-16. All three outputs are pasted from a real session against `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host); the `run` invocation that produced the 528-process report and the `report` invocation that reported zero were consecutive commands on the same file.
