# UX-57: the hook's fixed path buffer drops 70% of a real build's opens, which silently excludes every heavy element from declared-vs-used analysis

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-46` (which introduced the buffer and the `dropped` counter that made this answerable) | **Topic:** capture

## Motivation

Round 5 recorded the hook's per-process path budget as an open question,
in as many words:

> Its per-process path budget is a fixed 8192 slots / 256 KiB, chosen
> without evidence, and a large real build is what would say whether that
> is generous or naive — the `dropped` counter exists precisely so this
> can be answered rather than guessed.

Round 6's real `freedesktop-sdk` capture answers it. Naive:

```text
opens_captured:
  buildstream-build   paths: 65101   dropped: 149053   processes: 90646
```

**70% of observed opens were not recorded.**

## Why that is worse than a missing statistic

`UX-46` deliberately refuses to call a dependency unused when the read
set was truncated — an element with dropped paths is reported as
*uncovered* rather than as having unused dependencies, because a subset
of a read set is exactly the input that turns a used dependency into a
false "unused".

That refusal is correct, and it means the drop is not a partial result:
**every element heavy enough to fill the buffer was excluded from
declared-vs-used analysis entirely.** The heavier the element — the more
files it reads, the more likely it has an unused dependency worth finding
— the more certainly it went unanalyzed. The signal was inverted against
the elements it exists to serve.

## Compression was measured, and rejected

The obvious response is to store the paths more compactly, and a path set
looks highly compressible: they share long directory prefixes.

Front-coding — storing each path as `<shared prefix length><suffix>`
against the previous one — is the only compression available to a hook
that must record paths as they arrive, in a fixed buffer, with no
allocation. Measured on a real 3,658-path set from an `examples/06`
capture:

| storage | bytes | ratio |
|---|---|---|
| raw (today) | 161,508 | 1.00× |
| front-coded, insertion order | 114,295 | **1.41×** |
| front-coded, if sorted | 56,065 | 2.88× |

The 2.88× is not available: sorting requires having all the paths first,
which is the thing the buffer cannot do. The real figure is **1.41×**,
which moves the ceiling from roughly 6,000 paths to roughly 8,500 —
still below `OPEN_SLOTS`, so the table becomes the binding limit instead
of the arena and almost nothing is gained. In exchange it costs a wire
format change and a decoder on the reading side.

So compression is the wrong lever here, and this is recorded rather than
left for the next attempt to re-derive.

## Required Fix

1. **Stop having a ceiling.** When a window fills, write it out and start
   a new one instead of dropping. Paths repeated across windows are
   harmless: the parser unions them per element, so the final read set is
   exact either way. This makes the drop counter structurally zero for
   the case that was causing it.
2. **Raise the budgets anyway**, so a flush is rare rather than routine.
   This is close to free: both buffers live in `.bss`, which is anonymous
   zero pages faulted in only when written, so a process that records 30
   paths pays for 30 paths regardless of how large the buffers are
   declared. A real `examples/06` capture averages **32 unique paths and
   1.4 KiB of arena per process** (max 149 / 7 KiB), so the ordinary
   process never comes near either number.
3. **Keep the counters honest across windows.** `dropped` is a running
   per-process total re-reported in each window, so summing blocks would
   multiply one process's drops by how many times it flushed; and
   counting blocks as processes would report one busy compiler as dozens.

## Out of Scope

- The `unknown` element bucket and `UX-56`'s tagging collapse, which is
  why the real figures above are attributed to `buildstream-build`. The
  drop rate is the same regardless of which bucket it lands in.
- Recording *relative* paths, still deliberately skipped: they can only
  be interpreted against their opener's cwd, which the hook does not know.

## Acceptance Test

1. A process that overruns its window writes more than one `OPENS` block,
   numbered in order, with **zero** drops.
2. Every distinct path opened survives the flushes — the union across
   windows is exact.
3. A process that fits in its window writes exactly one block, as before.
4. One process flushing repeatedly is still counted as one process, and
   its drops are not multiplied by its window count.
5. A log captured before this change, with no `part=` field, still parses.

## Fix Implemented

`record_open` now flushes and retries instead of dropping, at most twice
— the second attempt runs against an empty window in which the path
provably fits and a free slot provably exists, which is what makes the
retry terminating. `OPEN_SLOTS` 8192 → 32768 and `OPEN_ARENA_BYTES`
256 KiB → 1 MiB, both now `#ifndef`-guarded so the flush path can be
compiled small and exercised for real by a test rather than only by a
build large enough to fill a megabyte.

The `OPENS` header gained `part=N`, appended rather than inserted so the
parser reads pre-`UX-57` logs unchanged; the parser tracks drops per pid
and windows separately from processes.

### Verified on a real build

A real traced build of `examples/07-declared-vs-used-dependencies`
(BuildStream 2.7.0, real `bwrap` sandbox, `--trace-opens`, exit 0):

```text
opens_captured:
  base.bst       paths: 35  dropped: 0  processes: 10  windows: 10
  unrelated.bst  paths: 33  dropped: 0  processes: 10  windows: 10
  user.bst       paths: 39  dropped: 0  processes: 10  windows: 10
declared_vs_used: 1 unused candidate, 4 used, 0 uncovered
```

One window per process, nothing dropped, and `UX-46`'s verdict on
`examples/07` unchanged — `unrelated.bst` still correctly identified as
declaring a dependency it never reads.

Tests: 7 new (`tests/unit/test_open_window_flush.py`), which compile the
real `hook.c` with a 16-slot / 256-byte window and run a real process
under it, so the flush path is exercised rather than reasoned about.

Suite: 962 → 969.

## Verification Log

Filed and implemented 2026-08-17 (round 6, after the user's observation
that dropped traces might want better data structures or compression —
which is what prompted measuring compression rather than assuming it).

The 65,101 / 149,053 figures are from the real `freedesktop-sdk`
`native-report.json` published to the `captures/fdsdk-latest` branch. The
front-coding ratios were computed directly from the 114 `OPENS` blocks in
a real `examples/06` raw trace log, by front-coding each block's paths in
their real recorded order and again after sorting them — the sorted
figure is included precisely to show what the achievable one is *not*.
The per-process averages come from the same 114 blocks.
