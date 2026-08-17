# UX-58: the Plane 2 shim rewrites a bwrap argv it never records, so the one artifact needed to fix `UX-56` does not exist in any capture

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (blocks `UX-56`'s real fix)

## Motivation

`UX-56` established that Plane 2's element tag comes from bwrap's `--dir`
last path segment, which is the element only under BuildStream's default
build-root layout — and that a real project (`freedesktop-sdk`, build
root `/buildstream-build`) collapses 99.4% of 127,630 processes into one
bucket that is not an element.

Fixing it means finding an *authoritative* element identifier somewhere
in the real bwrap invocation. That task listed three candidates and could
not choose between them, for a concrete reason:

> This needs a real captured argv to settle, which round 6 does not have.

The reason it does not have one is not the tarball budget, as `UX-56`
guessed. It is simpler: **`tools/native_trace/bwrap_shim.py` never
records the argv at all.** It receives BuildStream's complete bwrap
command line, splits it, injects into it, and `os.execv`s it — and writes
nothing anywhere. Every capture this project has ever taken discarded the
one artifact that would answer the question.

## What this blocks, beyond `UX-56` itself

Declared-vs-used (`UX-46`) returned **entirely empty** on the real
`freedesktop-sdk` capture:

```
declared_vs_used: available: true, unused_candidates: [], used: [],
                  uncovered_elements: [], skipped: []
```

Not a bug in that analysis: `read_declared_build_deps` is handed the
Plane 2 element tags, and `buildstream-build` / `expat` / `flit_core` are
not element paths, so nothing resolves. The whole signal is downstream of
the tag, so `UX-56` gates it, and `UX-58` gates `UX-56`.

## Required Fix

1. **Record the argv, opt-in and bounded.** When an env var is set, the
   shim appends the argv it received to a file in its bind directory
   before exec'ing. Bounded on purpose — the first N invocations are
   enough to identify a field, and a real build spawns thousands.
2. **Publish a sample from the capture workflow.** The run currently
   drops the raw native trace wholesale above 40MB; a sample must survive
   that rule, since all-or-nothing is what produced a capture with no
   argv in it.
3. **Then settle `UX-56`** against a real argv rather than against three
   ranked guesses.

## Out of Scope

- Choosing the identifier. That is `UX-56`, and doing it here would be
  guessing again with extra steps.
- Logging the argv unconditionally. It contains full sandbox paths and is
  large; opt-in matches how `--trace-opens` already works.

## Acceptance Test

1. With the env var set, a real traced build writes a file containing at
   least one complete bwrap argv as BuildStream generated it.
2. Without it, the capture is byte-identical to today's.
3. The sample survives the capture workflow's size rule and arrives in
   the published tarball.

## Fix Implemented

`record_argv` in `tools/native_trace/bwrap_shim.py`, active only when
`BST_TRACE_ARGV_LOG` is set, bounded by `BST_TRACE_ARGV_MAX` (default
32). Recorded **before** the rewrite, so the file holds what BuildStream
generated rather than what the shim turned it into. Surfaced as
`--argv-log PATH` on `bst_native_build_tracer run`.

Two design points worth keeping:

- The bound is enforced by re-reading the file, not by a counter, because
  each bwrap invocation is a *fresh* shim process with no memory of the
  last. Two concurrent invocations can therefore both see room and
  overshoot slightly - accepted deliberately, since the alternative is
  locking on a hot path to protect a diagnostic whose only requirement is
  "a few".
- It never raises. A diagnostic that can fail a real build is worse than
  no diagnostic, so every error path ends in "record nothing and let the
  build proceed" - pinned as a test against an unwritable path.

### What the first real capture immediately showed

A real traced build of `examples/07` (BuildStream 2.7.0, real `bwrap`
sandbox) captured three argvs of **349 tokens** each. The element name
appears three times:

```
[ 11] --dir     buildstream/dep-usage-example/base.bst
[ 13] --chdir   buildstream/dep-usage-example/base.bst
[338] PWD      /buildstream/dep-usage-example/base.bst
```

All three are the **same build-root-relative path**. That is a result
`UX-56` needs and did not have: they are not three independent sources
that a project overriding `build-root` would lose one of - they are one
source appearing three times, and `freedesktop-sdk` loses all three at
once. Nothing else in the argv carries element identity (the CAS staging
bind is `cas-tmpdir2wnYto`, randomly named).

So the next step for `UX-56` is more likely to be a mechanism *outside*
the argv than a better field within it. This is pinned as a test so the
next attempt starts from it rather than re-deriving it, and the decisive
version - the same capture against a project that overrides `build-root`
- is now one workflow run away.

## Verification Log

Filed and implemented 2026-08-17 (round 6 follow-up). The empty `declared_vs_used` block
is from the real `native-report.json` published to
`captures/fdsdk-latest`. The absence of any argv recording was read
directly from `tools/native_trace/bwrap_shim.py`, whose `main()` resolves
five environment variables and calls `os.execv` with no intervening
write.
