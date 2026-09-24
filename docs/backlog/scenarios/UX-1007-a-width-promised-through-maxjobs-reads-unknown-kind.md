# UX-1007: a width promised through MAXJOBS or MAX_JOBS reads unknown_kind

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-859, UX-1003 | **Found by:** the census of four BuildStream projects (fdsdk, gnome-build-meta, carbonOS, libreml; ~2,450 elements, 2026-09-24) | **Serves:** R2, R5 (an auto arm on a real project changes the sandboxes it names) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`recipe_promise` reads `JOBS` and a `MAKEFLAGS` carrying `-jN`. Real
projects promise width through other names, and those sandboxes read
`unknown_kind` and never join:

```text
fdsdk      elements/components/rust.bst:25,105   MAXJOBS; python3 x.py build -j${MAXJOBS}
gnome      mozjs                                 ./mach build -j${MAXJOBS}
           gst-plugin-gtk4                       MAX_JOBS
carbonOS   rust/all.bst, nss.bst                 MAXJOBS
fdsdk      linux, locales, linux-firmware, nss   MAXJOBS
fdsdk      project.conf                          GOMAXPROCS, CARGO_BUILD_JOBS = %{max-jobs}, every element
```

`GOMAXPROCS` and `CARGO_BUILD_JOBS` are set project-wide, so their
presence alone says nothing about the recipe.

## Decomposition

surfaces: `recipe_promise` and `kind_job_env` in `tools/native_trace/bwrap_shim.py`
guards: a sandbox carrying `MAXJOBS` or `MAX_JOBS` joins with a named policy; one carrying only project-wide `GOMAXPROCS`/`CARGO_BUILD_JOBS` stays as it reads today
gap: which policy a `MAXJOBS` driver gets - `x.py` and `mach` run cargo and make below them, and what their compilers receive is `UX-1006`'s question again
track: session's own
gate: its own

## Required Fix

Read `MAXJOBS` and `MAX_JOBS` as a width promise beside `JOBS`, with the
policy the gap settles; keep project-wide variables out of the promise.

## Out of Scope

A consumer that promises no width at all (`UX-1008`).

## Acceptance Test

A shim test whose sandbox carries `MAXJOBS=4` and no kind reads a joined
policy, and the mutation dropping `MAXJOBS` from `recipe_promise` reddens it.
