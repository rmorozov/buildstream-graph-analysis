# UX-1360: a never-read build edge counts executed binaries and probes as reads

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** the freedesktop-sdk field test (2026-10-30), capture `captures/fdsdk-cold-latest` (run 36850726112) | **Serves:** R2, R3 | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_dependency_whose_binary_ran_is_not_unused.py`

## Motivation

Correlate printed "`bootstrap/build/gcc-stage1.bst` opened no file staged by `bootstrap/build/binutils-stage1.bst` - worth checking whether the edge is needed" (0 of 180 files). The element's own build log reads `checking what linker to use... /cross/x86_64-unknown-linux-gnu/bin/ld`, a binutils-stage1 file, and it ran `as` 4,196 times. A cross toolchain is reached by `execve` and `stat`/`access` probes, not `open`. `compute_declared_vs_used`'s own docstring names a false "unused" as the dangerous failure.

## Decomposition

Input classes: the fdsdk cold capture (`git fetch --depth 1 origin captures/fdsdk-cold-latest`, untar `capture.tar.gz`; freedesktop-sdk @`953683fb`, `components/libxml2.bst`, 126 elements, cold, 4 logical / 2 physical cores.); the `golden` fixtures.

## Required Fix

An `execve` of, or a `stat`/`access`/`faccessat` on, a path a dependency staged counts as a read; when the hook did not record execs or probes for an element, its edges are `uncovered`, not candidates.

## Out of Scope

The spine; static binaries (UX-11).

## Acceptance Test

A fixture element that only executes a dependency's binary is not a candidate; on the fdsdk capture, gcc-stage1 <- binutils-stage1 is not printed. Mutation: count opens only; the guard reds. The page's element card for gcc-stage1 lists no unused dependency, read by the walker on this capture.

## Decision

- What the hook recorded: START/END carry `cmd=` (`/proc/self/cmdline`, argv only, no exe path); OPENS carries `open`/`openat` paths. No exec path, no `stat`/`access`/`faccessat` probe.
- `tools/native_trace/hook.c`: with `BST_TRACE_OPENS` set, the constructor records `readlink("/proc/self/exe")` into the read set, so a binary a process runs is a read of whatever staged it. Eight lines, no new interposer.
- Probes are not added: a `stat` interposer is ~14 glibc symbols (`stat`/`__xstat`/`fstatat`/`statx`/… and their 64 forms) on make's hottest path, and the fdsdk trace already outgrew publishing. Instead `compute_declared_vs_used` skips (`skipped[]`, reason `uncovered: …`) a dependency that staged files under `bin`/`sbin`/`libexec` none of which was opened or run, never a candidate. Library- and header-only dependencies are still judged.
- No new key: `skipped[]` already carries `element`, `dependency`, `reason`. Correlate and the page read `unused_candidates`, so an edge the producer refuses reaches neither.
- Guard: the real hook, compiled, runs a copy of `cat` staged under the dependency's `bin/` on a file of the element's own. Mutation: count opens only (drop the exe record); and drop the executable refusal.

## Outcome (2026-10-30)

**Gap measured** (fdsdk capture, today's `native-report.json` / `corr.json`):

```text
declared_vs_used: unused_candidates 6, used 20, skipped 0
bootstrap/build/gcc-stage1.bst <- bootstrap/build/binutils-stage1.bst  "0 of 180 files staged ... were opened"
components/bison.bst <- components/m4.bst  "0 of 321 files staged ... were opened"
corr.json bootstrap/build/gcc-stage1.bst: unused_dependencies ["bootstrap/build/binutils-stage1.bst"], declared-not-used advice
```

**Close measured** (`python3 -m pytest -q -p no:xdist tests/unit/test_a_dependency_whose_binary_ran_is_not_unused.py`):

```text
real hook, element runs <tmp>/cross/bin/cat on its own source: used == [(gcc-stage1.bst, binutils-stage1.bst)], unused_candidates == [], join row unused_dependencies empty
opens-only read set, dep staging bin/ld and bin/as: unused_candidates == [zlib.bst]; skipped reason "uncovered: binutils-stage1.bst stages 2 executable(s), none opened or run ..."
2 passed
```

The fdsdk reading waits on a re-capture: its native trace was not published and `bst artifact list-contents` was not kept, so `compute_declared_vs_used` cannot be rerun there; `bga correlate` on the old report still prints the edge, which a capture taken with this hook does not produce for an element that ran `ld`/`as`.

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| hook: `record_open(exe);` → `(void)exe;` (count opens only) | `test_running_a_dependencys_binary_reads_it` | 1 failed, 1 passed |
| tracer: `elif executables := _staged_executables(staged):` → `elif executables := 0:` | `test_an_executable_nobody_opened_or_ran_is_not_judged` | 1 failed, 1 passed |
