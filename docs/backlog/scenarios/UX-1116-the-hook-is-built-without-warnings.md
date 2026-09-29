# UX-1116: the LD_PRELOAD hook is built with no warnings and never runs under a sanitizer

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose build runs with the hook loaded into every process | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement | **Reading:** container

**Guard:** none — named test_the_hook_builds_clean_and_sanitized.py, absent from tests/

## Motivation

`tools/bst_native_build_tracer.py:174` builds `hook.c` with
`cc -shared -fPIC -O2 ... -ldl`: no `-Wall`, no `-Werror`. The hook runs
inside every process of a user's build, so a memory error in it corrupts the
build it measures. Today the source is clean — `gcc -Wall -Wextra
-fsyntax-only` gives 0 warnings on `hook.c` and `spine.c`, `-Wpedantic`
adds 6 — so the flags cost nothing now and hold the line after. No job
runs the hook under ASan or UBSan.

## Decomposition

Input classes: the hook and the spine source under `-Werror`; the hook under ASan/UBSan over a process tree that forks, execs and opens files.
Journey: `capture` with the native tracer loaded.

## Required Fix

The build adds `-Wall -Wextra`; a test compiles both C files with
`-Werror`, and a medium-tier test builds the hook with
`-fsanitize=address,undefined`, runs a small process tree under it (the
fixture `test_open_window_flush.py` already drives) and requires a clean
exit and no sanitizer report.

## Out of Scope

clang-tidy or cppcheck.

## Acceptance Test

`tests/unit/test_the_hook_builds_clean_and_sanitized.py`. Mutations: add
an unused variable to `hook.c` (the `-Werror` build reddens); add a one-byte
heap overflow on a path the fixture exercises (the sanitizer run
reddens).
