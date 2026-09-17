# UX-881: an operator ships their own wrapper directory for a custom-prefix toolchain

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-880 | **Found by:** round 126 + the user (toolchains built in-sandbox with custom prefixes — the compiler is invoked by absolute path, which PATH-shadowing cannot reach; and the user already runs their own clang-shim pattern) | **Serves:** R2 (a project whose compilers live at custom prefixes still gets the jobserver's effect) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

`JOBSERVER_WRAPPERS_DIR` is derived from `__file__` and hardcoded
(`tools/bst_native_build_tracer.py:1255-1256`); the bind-mount and
PATH-prepend (`_wrapper_mount`, `bwrap_shim.py:546-561`) can only shadow a
tool that the recipe invokes **by bare name** off `PATH`. The user's real
case is the opposite: a cross gcc-13 and a modern LLVM built in-sandbox
with **custom prefixes**, invoked by absolute path (`/usr/sysroot/bin/…`)
or via `toolchain.cmake`'s `CMAKE_C_COMPILER`. UX-880's reference shim
therefore cannot reach them, and the user cannot edit the bga-shipped
wrapper directory to add their own shim. They already maintain a
clang-shim ("a shell script that looks like clang and forwards to real
clang") — bga should let them point it at that.

## Required Fix

A `bga capture run --wrapper-dir <path>` flag (and/or a config key) that
**replaces or augments** the default `JOBSERVER_WRAPPERS_DIR`, threaded
through the existing `BST_TRACE_WRAPPER_DIR` env the shim already reads
(`bwrap_shim.py:1402`). The operator's directory must satisfy bga's
**published wrapper contract** (UX-880's `_common.sh` entry points:
`bga_run_wrapped <flag_style> "$@"`, the auth-strip, the token-return
trap) — the contract is documented, and a `bga capture run
--print-wrapper-contract` (or a doc section) states it so an operator's
shim can match. Augment-vs-replace: a replace loses the shipped
`ninja`/`ld.lld`/… shims, so the default is **augment** (the operator's
directory is prepended, the shipped one still bound), with `--wrapper-dir
--replace` for a fully custom set.

Surfaces: `bga/cli.py` (the flag), `tools/bst_native_build_tracer.py`
(`JOBSERVER_WRAPPERS_DIR` → env, honour the override), `bwrap_shim.py`
(`_wrapper_mount` binds two dirs when augmenting), a new
`docs/guides/wrapper-contract.md` (the contract), `docs/guides/cli.md`.

## Decomposition

surfaces: `bga/cli.py` · `tools/bst_native_build_tracer.py` · `bwrap_shim.py` (`_wrapper_mount` two-dir) · `docs/guides/wrapper-contract.md` (new) · `docs/guides/cli.md`
guards: `test_an_operator_wrapper_dir_is_mounted.py` (new): `--wrapper-dir` sets the env; `_wrapper_mount` binds both the operator dir (first on PATH) and the shipped dir under augment; `--replace` binds only the operator dir; the contract doc's entry-point names match `_common.sh`
gap: bga cannot validate that a foreign shim actually honours the contract at runtime — a lint-style `bga capture run --check-wrapper-dir` that greps for the entry points is a possible follow-up
track: bounded `implementer`; serial after UX-880 (the contract UX-880 publishes is what this mounts)
gate: a later round (filed this round, not built)

## Out of Scope

UX-880's reference shim and `flto` style (this only makes the directory
swappable). Runtime validation of a foreign shim. The `public:` surface
(UX-882).

## Acceptance Test

`tests/unit/`: `build_shim_argv` with the operator's `--wrapper-dir`
env set emits a bind-mount of that directory prepended to `PATH` ahead of
the shipped one (augment), and only that directory under `--replace`.
Mutation: ignore the override env (always mount the shipped dir) — the
"operator dir first on PATH" assertion reddens.

## Outcome

_(filed round 126, not built — deferred to a later round)_
