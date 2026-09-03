# UX-575: a documented pipe prints a traceback

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-326 (the printed sentences are contracts) | **Serves:** anyone who types the guide's own pipe to `head` | **Topic:** cli

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
