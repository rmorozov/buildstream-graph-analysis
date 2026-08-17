# UX-58: the Plane 2 shim rewrites a bwrap argv it never records, so the one artifact needed to fix `UX-56` does not exist in any capture

**Priority:** High | **Status:** 🔴 Open | **Depends on:** — (blocks `UX-56`'s real fix)

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

## Verification Log

Filed 2026-08-17 (round 6 follow-up). The empty `declared_vs_used` block
is from the real `native-report.json` published to
`captures/fdsdk-latest`. The absence of any argv recording was read
directly from `tools/native_trace/bwrap_shim.py`, whose `main()` resolves
five environment variables and calls `os.execv` with no intervening
write.
