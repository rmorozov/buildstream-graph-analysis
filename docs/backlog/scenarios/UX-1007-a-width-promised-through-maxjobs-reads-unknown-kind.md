# UX-1007: a width promised through MAXJOBS or MAX_JOBS reads unknown_kind

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-859, UX-1003 | **Found by:** the census of four BuildStream projects (fdsdk, gnome-build-meta, carbonOS, libreml; ~2,450 elements, 2026-09-24) | **Serves:** R2, R5 (an auto arm on a real project changes the sandboxes it names) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_maxjobs_promise_joins_the_pool.py`

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

## Decision

```text
Route:    `recipe_promise` returns `"MAXJOBS"` when the sandbox carries a `--setenv MAXJOBS`/`MAX_JOBS` bare integer; `kind_job_env` gives it a new policy, `maxjobs_env`: inject the `MAKEFLAGS` auth and leave `MAXJOBS` untouched, so `x.py`/`mach` pass `-j${MAXJOBS}` to cargo/make, which join as clients (UX-1006's fifo auth covers gcc). `parse_element_max_jobs` reads `MAXJOBS` as a bare integer too, so `MAXJOBS=1` is `pinned`.
Rejected: emptying `MAXJOBS` as `JOBS` is emptied (`-j${MAXJOBS}` becomes `-j`: unbounded for make, a failure for x.py) · raising `MAXJOBS` to the pool size (widens non-clients with no token behind it) · counting `GOMAXPROCS`/`CARGO_BUILD_JOBS` as a promise (project-wide in fdsdk's project.conf).
Files:    tools/native_trace/bwrap_shim.py (`_JOB_SETENV_VARS`, `kind_job_env`, `recipe_promise`); tests/unit/test_a_maxjobs_promise_joins_the_pool.py
Guard:    that file: MAXJOBS=4 with no kind gets `maxjobs_env` and the auth; MAX_JOBS the same; only GOMAXPROCS+CARGO_BUILD_JOBS still reads `unknown_kind`; MAXJOBS=1 is `pinned`.
Mutation: drop MAXJOBS from `recipe_promise` (claim 1 reds); make GOMAXPROCS a promise (claim 3 reds).
Class:    product
```

## Out of Scope

A consumer that promises no width at all (`UX-1008`).

## Acceptance Test

A shim test whose sandbox carries `MAXJOBS=4` and no kind reads a joined
policy, and the mutation dropping `MAXJOBS` from `recipe_promise` reddens it.

## Outcome

Gap measured: before, `recipe_promise` of a `MAXJOBS=4` sandbox with no kind
was `None` and the real gate recorded `unknown_kind` (no injection).

Close measured (`python3 -m pytest -n 2` on the new guard, the register guard,
`test_bwrap_shim.py` and the UX-1003 file: 84 passed). A register row for
`maxjobs_env` is in `docs/design/continuous-build-improvement.md` 7a.

| Mutation | Reddened | Run printed |
|---|---|---|
| `_MAXJOBS_VARS = ()` (drop MAXJOBS from `recipe_promise`) | claim 1, both params | 2 failed, 2 passed |
| `_MAXJOBS_VARS` gains `GOMAXPROCS` | claim 2 (unknown_kind) | 1 failed, 3 passed |
| `_BARE_INT_VARS = ("JOBS",)` | claim 3 (pinned) | 1 failed, 3 passed |
