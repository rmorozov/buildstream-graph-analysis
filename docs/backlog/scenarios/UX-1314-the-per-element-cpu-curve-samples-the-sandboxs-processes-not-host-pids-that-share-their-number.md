# UX-1314: The per-element CPU curve samples the sandbox's processes, not host pids that share their number

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** UX-1134's architect, round 152; promoted from the bookkeeping ledger in round 169 | **Serves:** R1, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`ElementCpuSampler._run` (`tools/bst_native_build_tracer.py:1210-1222`)
reads the host's `/proc/<pid>/stat` with pids taken from the trace log.
Those pids are namespace-local: the hook sets `g_pid = getpid()` inside
`bwrap --unshare-pid` (`tools/hook.c:821`), and the spine writes
`START pid=%d` as sandbox pid 2 (`tools/spine.c:443`, `:48-53`).

Every sandbox therefore starts at pid 2, so concurrent elements
overwrite each other in `_live`, which is keyed by pid. Host `/proc/2`
is `kthreadd` (cpu ~0) and the next low pids are kernel threads, so a
sample is near-zero or absent; a larger pid that does exist reads an
unrelated host process. `cpu_time.per_element_series`
(`tools/bst_native_build_tracer.py:1246`, `bga/schemas.py:5030`) is
never per-element CPU. Nothing in `bga/viewer` reads it today (grep),
so the page is unaffected until something does. Read from the code, not
reproduced against a live bwrap capture.

## Decomposition

Input classes: one element in a sandbox; two concurrent elements (both
pid 2); an element that forks a deep process tree; a host with
kernel threads at the pids the sandboxes report. Journey: a real
`bga capture -- bst build` with `--jobserver auto` under bwrap, read
`cpu_time.per_element_series` against `top` per sandbox.

## Required Fix

Shape with or after UX-1134, which plans the same mechanism: the shim
adds `"pid": os.getpid()` to its decision row (the host pid it execs
bwrap with), and the series becomes the sum of utime+stime over the
host `/proc` descendants of each element's sandbox root, never the
trace log's namespace pids.

## Out of Scope

The viewer drawing the series; the per-process CPU in the trace log.

## Acceptance Test

Two concurrent elements under bwrap each get their own series, and each
series follows that element's descendants' CPU (checked against the
sum of their `/proc` times); a guard replays a scripted `/proc` root in
which two sandboxes both report pid 2. Reading taken in this container.

## Outcome
