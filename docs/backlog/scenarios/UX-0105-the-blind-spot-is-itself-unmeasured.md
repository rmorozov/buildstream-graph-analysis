# UX-105: the hook's blind spot is itself unmeasured

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — (first step of Direction 4)

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
