# UX-105: the hook's blind spot is itself unmeasured

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — (first step of Direction 4)

Direction 4 — see [`design/directions.md`](../../design/directions.md).

## Motivation

Every Plane 2 report carries the same footnote: statically-linked
processes ran but produced no trace entry, and "this tool cannot detect
its own absence" (`tools/native_trace/hook.c`'s own header). That is
honest and useless in equal measure: it fires identically on a capture
that missed nothing (a pure glibc gcc toolchain) and on one that missed
*everything* (`examples/01`'s manual elements run static busybox — their
Plane 2 capture is empty today, and only a reader who knows the
staging script would guess why).

Whether a binary is static is knowable **before the build runs**: an
ELF executable with no `PT_INTERP` program header (and no `DT_NEEDED`)
does not invoke the dynamic linker and will not load the hook. The
staged sandbox roots sit on disk at capture time; scanning them makes
the blind spot a per-element, named measurement — and produces the
ground-truth binary list `UX-106`'s tracer is verified against.

## Required Fix

1. A census pass in the capture path (`bst_native_build_tracer`): walk
   each staged sandbox root's executable files, classify ELF binaries
   as static (no `PT_INTERP`) vs dynamic, and record per element:
   static executable count, their names/paths, and the dynamic count.
   Pure stdlib ELF header parsing (a 64-byte header + program headers;
   no new dependency), symlink-aware, non-ELF executables (scripts)
   counted as their interpreter's class.
2. The report's disclaimer becomes data-driven: silent when the census
   finds zero static executables; when it finds them, one line naming
   the worst offenders — *"N static executable(s) staged for
   `<element>` (busybox, …): processes exec'd from these produce no
   trace records"* — and a per-element
   `static_executables` field in the JSON for `UX-107`'s coverage
   arithmetic.
3. The census is also exposed standalone (a flag on `bga capture
   report` or the tracer CLI) so it can run against an already-staged
   project without a build.

One honest limit, stated in the payload: staged-but-never-exec'd
static binaries inflate the *risk* count, not the *missed process*
count — the census bounds what the hook can miss; only `UX-106`'s
spine measures what it did miss.

## Out of Scope

- Any tracing change (`UX-106`).
- Interpreting scripts' shebang chains beyond one level.

## Acceptance Test

On `examples/01-resource-contention` (staged via
`stage_runtimes.sh`): the census reports busybox as a static
executable for the manual elements, and the capture report's
disclaimer names it instead of the generic footnote. On
`examples/06` (staged glibc toolchain): zero static executables, no
disclaimer line at all. The JSON carries per-element counts in both
cases; two runs over the same staging are identical.

---

## Fix Implemented

`classify_elf` / `census_static_executables` / `census_project` in
`tools/bst_native_build_tracer.py`, reached three ways: automatically
from `bga capture run`, from `bga capture report --project-dir` on an
already-saved report, and standalone as **`bga capture census
PROJECT`** — which builds nothing and does not invoke BuildStream.

### `e_type` decides as much as `PT_INTERP` does

The task specifies "no `PT_INTERP`" as the test, and implemented that
way it is wrong. The first real run, against `examples/06`'s staged
glibc toolchain, reported **five static executables**:

```text
lib/x86_64-linux-gnu/ld-linux-x86-64.so.2
lib64/ld-linux-x86-64.so.2
usr/lib/bfd-plugins/liblto_plugin.so
usr/lib/gcc/x86_64-linux-gnu/13/liblto_plugin.so
usr/libexec/gcc/x86_64-linux-gnu/13/liblto_plugin.so
```

Shared objects have no `PT_INTERP` either — they are loaded, not exec'd
— so `PT_INTERP` alone calls every library on the system a static
binary. Classification therefore reads `e_type` as well:

| shape | verdict |
|---|---|
| `ET_EXEC`, no `PT_INTERP` | **static** — the thing `LD_PRELOAD` cannot reach |
| anything with `PT_INTERP` | **dynamic**, `ET_EXEC` and PIE alike |
| `ET_DYN`, no `PT_INTERP` | **library**, counted separately |

The last row carries the one real ambiguity, stated rather than
resolved: a *static-PIE* executable has exactly that shape and is
indistinguishable from a shared object without parsing the dynamic
section for `DT_SONAME`/`DT_NEEDED`. Static-PIE is rare and a library is
not, so counting the bucket as libraries **under**-reports the blind
spot — the safe direction for a number whose whole job is to say "the
trace may be missing something".

Pure stdlib, 32- and 64-bit, either endianness, because a cross-built
sysroot is exactly the case where this question matters.

### Per element, through the build closure

An element's sandbox holds what its own sources stage *and* what its
build dependencies stage, so the census propagates over the declared
build closure. That is what makes it name the element a reader cares
about rather than only the one that imported the binary.

### The acceptance, run

`examples/01-resource-contention`, whose Plane 2 capture is empty:

```text
$ bga capture census examples/01-resource-contention
5 static executable(s) staged, reaching 10 element(s) of 10
    bin/cat  bin/env  bin/sh  bin/sleep  bin/true
  all.bst: 5 static via runtime.bst
  runtime.bst: 5 static from its own sources
  work-a.bst: 5 static via runtime.bst
```

and the same build, traced, now explains its own emptiness instead of
printing the generic footnote:

```text
Processes traced: 0
NOTE: 5 static executable(s) staged for 10 element(s) - cat, env, sh, sleep
(+1 more). Processes exec'd from these produce no trace record at all:
LD_PRELOAD only reaches a binary that invokes the dynamic linker. Affected:
all.bst, runtime.bst, work-a.bst, work-b.bst (+6 more). This bounds what the
trace can be missing; it does not measure what it did miss (UX-105).
```

`examples/06` (staged glibc toolchain) reports zero static executables
and gets a third message rather than either of the other two:

```text
NOTE: no statically-linked executable is staged by this project's own sources,
so LD_PRELOAD had nothing to miss among them. Binaries arriving from a remote
artifact cache or produced by the build are outside what this census can see
(UX-105).
```

Two censuses of one project are byte-identical.

### One thing the re-render path needed

`bga capture report` on a *saved* JSON report fell back to the generic
footnote even with `--project-dir`, because the census only ran on the
raw-log path. The census reads files on disk and runs nothing, so it is
as available to a saved report as to a fresh one — and leaving it out
reproduced the same "fires identically whatever the truth is" problem
one level up.

Tests: 17 new in `tests/unit/test_static_census.py`, including the ELF
header arithmetic at both widths and both endiannesses, built from
hand-written headers rather than from a checked-in binary — the point is
the arithmetic, and a fixtured binary would make it a test about one
machine's `/bin`.

Suite: 1335 → 1352.

## Verification Log

Done 2026-08-18. The `examples/01` figures are a real traced build (0
processes, which is the defect the census explains); the `e_type`
correction came from running the first implementation against
`examples/06`'s real staged toolchain, not from review.
