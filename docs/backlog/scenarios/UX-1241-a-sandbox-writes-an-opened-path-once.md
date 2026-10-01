# UX-1241: every process of a sandbox writes every path it opened, so a C++ element's log repeats the same headers hundreds of times

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1240 | **Found by:** Ruslan's report from his own project (2026-10-01): a 650 MB `plane2.log.gz`; he chose the hook-side dedup on 2026-10-01 | **Serves:** R5 | **Topic:** capture | **Area:** tools | **Shape:** bounded

**Guard:** test_a_sandbox_writes_a_path_once.py

## Motivation

The hook dedupes opened paths per process (`g_open_hashes`) and writes
them at exit. The parser unions an element's paths, so a path the
element's tenth compile also opened is read, interned and dropped.
Measured on three real builds under the hook (`BST_TRACE_OPENS=1`,
4-core container, gcc 13.3):

```text
build                                   processes  path lines  distinct  log
abseil-cpp cmake + make -j4                 2,327     188,965     4,092  10.6 MB
xz 5.6.3 configure + make -j4 + check       7,125     396,307     5,029  32.9 MB
```

98% of path lines are repeats within the element. UX-1240 made the
report cheaper per line; this removes the lines.

## Decomposition

Input classes: paths shared by every process, a process's own path, a
process with nothing new, a window flush, a crowded table, a table that
cannot open, no `BST_TRACE_OPENS`, no invocation id. No journey
extended: the report's read set is unchanged by construction.

## Required Fix

In `tools/native_trace/hook.c`: a path another process of the same
sandbox already wrote is not written again. One table of 64-bit path
hashes per sandbox, a file the hook maps shared and fills with a
lock-free insert; any failure or a crowded table writes the path. The
header is written even when no path is left, so `processes` and the
per-pid counts hold. `tools/native_trace/bwrap_shim.py` names the
table per invocation, `BST_TRACE_OPENS_SEEN=<bind dst>/opens-seen-<id>`.

## Out of Scope

The record list (`UX-313`); START/END lines, now most of a deduped log;
dedup across sandboxes of one element.

## Acceptance Test

`tests/unit/test_a_sandbox_writes_a_path_once.py`: 13 processes under
the real hook write each shared path once and the element's read set is
the no-table one; a process with nothing new still writes its header; a
16-slot table and an unopenable one write every path; the shim names
one table per invocation, and none without `BST_TRACE_OPENS`.

## Outcome (2026-10-01) — 🟢 Done

**Premise:** held — 98% of path lines repeat within the element.

### The close, measured

The same builds from clean trees, the hook with and without the table;
`parse_open_lines` on each log, gzip -6:

```text
build    table  path lines  distinct  procs  log        gz        wall
abseil   no       188,965     4,092    448   10.59 MB   1.06 MB
abseil   yes        4,092     4,092    448    1.85 MB   0.15 MB   41.6s
xz       no       396,307     5,029  1,811   32.85 MB   2.20 MB   24.9s
xz       yes        5,627     5,029  1,811   10.47 MB   0.61 MB   24.9s
```

`distinct` and `procs` agree; the two xz sets differ only in gcc's
random `/tmp/cc*.o` names (4,275 each way). xz's 598 extra lines start
with `/` but are lines of configure's multi-line sed commands. The
tables filled 4,092 and 5,029 of 32,768 slots and never crowded.
Build wall moved 0.0 s on xz.

Report cost, UX-1240's tree, the real logs above scaled x20
(`scale.py`, 197,680 processes), the deduped log emulated from the
full one by keeping each element's first copy of a path:

```text
log      raw      gz       report wall / VmHWM   report sha256
full     949 MB   75 MB    19.5s / 385 MB        ed307ed9a56fd198
deduped  263 MB   16.6 MB   9.7s / 385 MB        ed307ed9a56fd198
```

Wall -50%, gzipped log -78%, report identical. Peak memory does not
move: it is the record list's (`UX-313`).

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | the arena is not compacted | written once, header kept: 2 failed |
| M2 | a hash found reads as new | 2 failed |
| M3 | a crowded table drops the path | the 16-slot clause, 1 failed |
| M4 | a process with nothing new writes no header | 1 failed |
| M5 | no table writes no path | 2 failed |
| M6 | one table for every sandbox | the shim clause, 1 failed |
| M7 | a new hash is never inserted | 2 failed |

### Deviation from the Required Fix

The table is 256 KiB per sandbox and is left in the bind directory under
`.bga/tmp`, which the capture deletes at its end; the hook cannot remove it, since
a build's root shell leaves by `_exit` and never runs the destructor.
