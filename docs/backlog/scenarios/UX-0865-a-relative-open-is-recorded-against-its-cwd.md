# UX-865: a relative open is recorded against its cwd

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-57 | **Found by:** round 120, the user (a 16-core, 32 GB host, `--builders 16 --jobserver auto`) | **Serves:** R2 (a header reached through a relative include path still counts as read) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

The hook (`tools/native_trace/hook.c`) records absolute opens only
and drops relative ones, since it does not know the opener's cwd; the
analysis then intersects exact path strings with `bst artifact
list-contents`. A compiler handed `-I../staged/include` opens
`../staged/include/foo.h` and the read is lost, so the dependency reads
unused. The hook is inside the process: `getcwd` is one call, once per
process.

## Required Fix

`tools/native_trace/hook.c`: a relative path is joined to the
process's cwd (read once at the first relative open, refreshed on
`chdir`/`fchdir` interposed the same way) and recorded absolute;
`OPENS` gains a `relative=<n>` count; `bga/report`'s caveat under
"never read" names the remaining spelling gap (a path reached under
another alias is not matched).

## Decomposition

Input classes: absolute, relative from the initial cwd, relative
after `chdir`, `openat` on a directory fd; the journey it extends is
`UX-46`'s never-read dependencies on a real include path.

## Out of Scope

Symlink resolution (the alias gap stays a caveat); `mmap`; `openat`
with a directory fd other than `AT_FDCWD`, counted, not resolved.

## Acceptance Test

`tests/unit/test_declared_vs_used.py` gains: a fake element opening
`../include/foo.h` from cwd `/build/x` matches the staged
`/build/include/foo.h`; mutation: drop the join - red. The hook's own
test opens a relative path and reads it back absolute.

## Outcome

**Gap measured:** `git show ede1ce6f:tools/native_trace/hook.c` line 174
guarded `record_open` with `path[0] != '/'` and returned - every
relative open was dropped, no cwd was ever read. `git show
ede1ce6f:tools/native_trace/hook.c | grep -c getcwd`: 0. The verifier's
own held gap: `record_openat`'s `dirfd != AT_FDCWD` guard had no test -
gutting it to join every dirfd-relative open against the cwd left all
801 tests green.

**Close measured:** `record_open` joins a relative path against a
per-thread `getcwd()` cache, collapses `.`/`..` lexically
(`normalize_abs_path`), and records it absolute; `chdir`/`fchdir`
invalidate it. `OPENS` gained `relative=<n>` and `dirfd=<n>` (`openat`
on a non-`AT_FDCWD` fd, counted not resolved). Verifier's four holds
closed: (1) a real-dirfd `openat` test added - asserts `dirfd=1`, no
`<cwd>/foo.h` line, `relative` unmoved. (2) every silent join failure
(`getcwd` ENOENT, too-long, too-deep) now increments `g_open_dropped`,
so the header carries it and `compute_declared_vs_used` already marks
that element uncovered; a deleted-cwd (`chdir` then `rmdir` the same
path) test reproduces the ENOENT case reliably - `dropped == 1`, no
crash. (3) `g_cwd`/`g_have_cwd` replaced by a `_Atomic unsigned`
generation bumped by `chdir`/`fchdir`, read/compared against a
`__thread` cache re-read only when stale - allocation-free, no shared
mutable buffer. A `chdir` racing an `open` is inherently racy at the
kernel too (no instant at which two threads agree on "the cwd"); this
only guarantees each thread reads a cwd current at *some* instant,
never a torn buffer - untested directly, reasoned from the code, since
a reliable interleaving test would be flaky by construction. (4)
`fchdir`'s own invalidation test added (mirrors the `chdir` one).
`python3 -m pytest -q tests/unit/test_a_relative_open_is_joined_to_its_cwd.py
tests/unit/test_declared_vs_used.py tests/unit/test_open_window_flush.py
tests/unit/test_the_register_is_terse.py
tests/unit/test_a_commit_body_is_eight_lines.py`: 804 passed in 8.04s.
Hook compiles warning-free with `-Wall -Wextra` and the build's own
`cc -shared -fPIC -O2 -o hook.so hook.c -ldl`. `ruff check`: all checks
passed. `dev_sizes.py --check`: sizes ok, nothing grew past the
reference.

**Deviation:** the Acceptance Test's first clause asked for a
`test_declared_vs_used.py` case opening `../include/foo.h` from cwd
`/build/x`; the case passes an already-joined `/build/include/foo.h`
instead. The join itself is proven at the hook level (the C-level
tests, mutated); the Python case proves only that a joined path
matches - `compute_declared_vs_used` never joins anything, so a
"drop the join" mutation there has no code to remove.

**Mutation table:**

| Guard | Mutation | Reddened | Count |
|---|---|---|---|
| `record_open`'s relative-path join (hook.c) | restored the old drop (`if (0) { join-block }`) | both original cases | 2 failed of 5 |
| `chdir`'s cache invalidation (hook.c) | removed the bump from `chdir` | `test_a_second_chdir_joins_against_the_new_cwd` only | 1 failed of 5 |
| `parse_open_lines`'s `relative=` carrying (tracer.py) | forced the parsed raw value to `None` before the by-pid max | both original cases' `relative` asserts | 2 failed of 5 |
| `record_openat`'s dirfd guard (hook.c) | gutted to `record_open(path)` unconditionally | `test_openat_on_a_real_dirfd_is_counted_not_joined` only | 1 failed of 5 |
| `fchdir`'s cache invalidation (hook.c) | removed the bump from `fchdir` | `test_fchdir_also_joins_against_the_new_cwd` only | 1 failed of 5 |
| `getcwd`-failure drop counting (hook.c) | removed `g_open_dropped++` on `cwd == NULL` | `test_a_deleted_cwd_is_dropped_not_crashed` only | 1 failed of 5 |

Each reverted from the pre-mutation copy and re-run green (5 of 5,
against the 5-case hook test file - the full run above is 804).
