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
