# UX-575: a documented pipe prints a traceback

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-326 (the printed sentences are contracts) | **Serves:** anyone who types the guide's own pipe to `head` | **Topic:** cli | **Area:** bga

## Motivation

```text
$ bga analyze tests/fixtures/macro_micro/run --format json | head -2
{ … two lines … }
Traceback (most recent call last): … BrokenPipeError: [Errno 32] Broken pipe
Error: [Errno 32] Broken pipe
exit 2
```

`cli.md:752` documents exactly that pipe; `bga analyze --schema |
head -3` (`bga/cli.py:2107`) does the same. Every JSON emitter is
affected: the CLI never handles `SIGPIPE`/`BrokenPipeError`, and the
installed-command sweep runs no piped shape.

## Required Fix

One handler at the CLI boundary: a broken pipe on stdout exits 0
silently (the reader chose to stop), stderr untouched. The sweep
gains one piped invocation per JSON emitter (`| head -1`) asserting
no traceback and exit 0.

## Out of Scope

- Streaming output — the emitters may still build the document first.

## Acceptance Test

The documented pipe prints two lines and exits 0; mutation: remove
the handler — the sweep's piped clause reds on every emitter.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** held — and understated: the traceback is one of two shapes,
and the second exits 120 without `main()` ever seeing an exception.

### The gap, measured

```text
$ bga analyze tests/fixtures/macro_micro/run --format json 2>err | head -2
{
  "schema": "analyze/v5",
exit=2
$ cat err
Plane 2: .../tests/fixtures/macro_micro/plane2.json
Unexpected error
Traceback (most recent call last): ... in _execute_and_write: print(output)
BrokenPipeError: [Errno 32] Broken pipe
Error: [Errno 32] Broken pipe

$ bga --version 2>err | true     # PYTHONUNBUFFERED unset
exit=120
$ cat err
Exception ignored in: <_io.TextIOWrapper name='<stdout>' mode='w' encoding='utf-8'>
BrokenPipeError: [Errno 32] Broken pipe
```

`_execute_and_write`'s `except Exception` called the pipe an unexpected
error and returned 2. The second shape the filing missed: on a pipe
stdout is block-buffered, so an output under 8192 bytes reaches no
`write` syscall while `main` is on the stack — the interpreter flushes
at exit, past every `except`, and CPython answers 120. This container
sets `PYTHONUNBUFFERED=1`, which hides that shape; the first three
measurements taken with it were of the wrong population.

### After

```text
$ bga analyze tests/fixtures/macro_micro/run --format json 2>err | head -2
{
  "schema": "analyze/v5",
exit=0
$ cat err        # the pre-existing note, and nothing else
Plane 2: .../tests/fixtures/macro_micro/plane2.json
$ bga --version 2>err | true ; cat err
exit=0
```

Three lines in `bga/cli.py`: the two broad handlers re-raise
`BrokenPipeError`, `main` flushes stdout in a `finally` so the deferred
shape raises where it can be caught, and the handler points stdout's
descriptor at `/dev/null` so the exit flush finds nothing to fail on.
`--bogus` still exits 1 (`UX-574`'s code), unpiped and piped.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A | drop `except BrokenPipeError: raise` in `_execute_and_write` | the analyze pipe clause, 1 of 8 |
| B | `main`'s handler re-raises instead of returning `EXIT_OK` | 8 of 8 |
| C | `sys.stdout.flush()` in the `finally` → `pass` | blast, whatif, `--version`: 3 of 8 |
| D | `_stop_writing_to_stdout` returns first | whatif, `--version`: 2 of 8 |

The first draft read three lines and *then* closed: four of the five
schemas fit the kernel's 64K pipe buffer whole (analyze 115783 bytes,
correlate 26768, compare 17435, blast 4519, whatif 3375), so those four
never broke the pipe and passed under B. It closes first now.

### Deviation from the Required Fix

The piped clause is a new file, not the installed sweep; `UX-579` joins
it to the documented lines.

```text
$ make test-touching
108 file(s) selected · 2064 passed, 71 skipped in 63.63s (0:01:03)
$ make lint
All checks passed!
```

<!-- 80 lines, held by test_the_register_is_terse.py::TestOutcomes. -->
