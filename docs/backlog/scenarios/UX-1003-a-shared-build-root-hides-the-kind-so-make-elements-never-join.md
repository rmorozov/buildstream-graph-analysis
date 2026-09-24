# UX-1003: a shared build root hides the element's kind, so fdsdk's make elements never join

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-859, UX-884 | **Found by:** `UX-905`'s fdsdk pair (off 35957674792, auto 35970752554, 2026-09-24) - 21 of 25 auto-arm sandboxes read `unknown_kind` | **Serves:** R2, R5 (an auto arm on a real project changes the sandboxes it names) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

freedesktop-sdk sets `build-root: /buildstream-build`, so `--dir` names
no element and the kind lookup reads `None` for every sandbox
(`jobserver_decisions`, auto arm):

```text
decision joined policy unknown_kind: 21
decision joined policy ninja_client: 4
```

The four are the cmake/meson sandboxes carrying `JOBS` (`UX-859`). The
seven autotools sandboxes (`export NOCONFIGURE=1; if [ -x configure ]`)
carry BuildStream's own `MAKEFLAGS=-j4` and get nothing, so the pair
compares two builds that differ in four sandboxes. Per-element peaks are
equal in both arms bar `cmake-stage1` (12 off, 8 auto); the walls,
2807s and 2872s, are one sample each.

## Decomposition

surfaces: `tools/native_trace/bwrap_shim.py`'s `kind_job_env` and the kind lookup
guards: a sandbox with `--dir buildstream-build` and `MAKEFLAGS=-jN` reads policy `make`; one with neither stays `unknown_kind`
gap: a recipe-set `MAKEFLAGS=-jN` as a promise like `JOBS`, versus recovering the name another way (the invocation id, `UX-56`); the first is local, the second is the general fix
track: session's own
gate: `UX-884`, settled 2026-09-24 - a make client switches the inherited read fd to non-blocking, so its LTO links cannot deadlock on it

## Required Fix

Treat a sandbox whose own argv sets `MAKEFLAGS` with a `-jN` as a make
recipe when its kind is unknown, the way `UX-859` treats `JOBS`, after
`UX-884` settles what that element's LTO links receive.

## Out of Scope

Relabelling Plane 2's attribution (`UX-56`), which is post hoc.

## Acceptance Test

The fdsdk auto arm's `jobserver_decisions` read `make` for the seven
autotools sandboxes, and the build completes.

## Outcome

Gap measured: the fdsdk auto arm (run 35970752554) read
`unknown_kind: 21, ninja_client: 4`; the seven autotools sandboxes
carry `MAKEFLAGS=-j4` and no `JOBS`, under `--dir buildstream-build`.

Close: `recipe_promise` reads BuildStream's own `--setenv`s - `JOBS`
first, then a `MAKEFLAGS` with a `-jN` - and `kind_job_env` reads
`"MAKEFLAGS"` as policy `make`, on both the injection and the recorded
decision. The field reading is owed by the next fdsdk auto arm.

| mutation | reddened | count |
|---|---|---|
| no `MAKEFLAGS` branch in `kind_job_env` | the direct case and the real gate | 2 |
| any `MAKEFLAGS` counts, `-j` or not | the `-k` case | 1 |
| `JOBS` no longer wins over `MAKEFLAGS` | the both-set case | 1 |
| the recorded decision ignores `MAKEFLAGS` | the real gate | 1 |

Deviation: the policy is `make`, not a new name, since the recipe is a
make recipe; the register gains no row.
