# UX-1116: the LD_PRELOAD hook is built with no warnings and never runs under a sanitizer

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** anyone whose build runs with the hook loaded into every process | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical | **Reading:** container

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

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     `-Wall -Wextra` in `compile_hook` and `compile_spine` (tools/bst_native_build_tracer.py:173-174). New medium test: (a) `-Wall -Wextra -Werror -O2 -c -o /dev/null` on hook.c and spine.c (0 warnings today); (b) hook.c built `-fsanitize=address,undefined -O1 -g -fno-omit-frame-pointer -DOPEN_SLOTS=16 -DOPEN_ARENA_BYTES=256`, run under `LD_PRELOAD=<cc -print-file-name=libasan.so>:<hook.so>` with `ASAN_OPTIONS=detect_leaks=0:exitcode=86`, `UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1`, over a python3 opener (60 files, copied from test_open_window_flush.py) plus `sh -c 'cat /etc/hostname; ls /'`; rc 0, no "Sanitizer" in stderr, START lines from more than one pid
Rejected:  importing from another test file (tests do not import tests); clang/MSan (gcc is what CI has)
Files:     tools/bst_native_build_tracer.py, tests/unit/test_the_hook_builds_clean_and_sanitized.py, tests/conftest.py (KNOWN_SKIP_REASONS: "no sanitizer runtime (libasan) for the C compiler")
Guard:     that file; skips when `-print-file-name=libasan.so` returns a bare name
Mutation:  `int x;` unused in hook.c reddens (a); `g_open_arena[OPEN_ARENA_BYTES] = 0;` after the memcpy at hook.c:349 reddens (b) - measured rc 86, global-buffer-overflow (the arena is static, not heap, unlike the row's text)
Class:     product
```

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

## Outcome

Gap measured: `gcc -Wall -Wextra -Werror -O2 -c -o /dev/null` on `hook.c`
and `spine.c` exits 0 at `438740ac`; `compile_hook`/`compile_spine` passed
no `-W` flag; no test ran the hook under a sanitizer.

Close measured: `python3 -m pytest tests/unit/test_the_hook_builds_clean_and_sanitized.py -q -n0`
-> 3 passed in 0.96s (libasan at `/usr/lib/gcc/x86_64-linux-gnu/13/libasan.so`).
Both compile calls now carry `-Wall -Wextra`.

| mutation | red | printed |
|---|---|---|
| `int x;` inside `write_trace_line` (a global `int x;` did not warn) | `test_the_source_compiles_without_a_warning[hook]` | 1 failed, 2 passed |
| `g_open_arena[OPEN_ARENA_BYTES] = 0;` after the memcpy | the ASan run (rc 1, AddressSanitizer report) and, via `-Warray-bounds`, the `-Werror` hook build | 2 failed, 1 passed |

Deviation: the Decision's mutation (b) measured rc 86; here python3 under
ASan printed rc 1 with a report - still red. The arena mutation also trips
`-Wall`, so (b) is not isolated by that mutation alone; the ASan test
reddens on its own return code and "Sanitizer" grep.
