# UX-1347: the wheel ships no `native_trace/wrappers`, so `--jobserver auto` dies in bwrap

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** Ruslan's field report, `pip install . --force` then `--jobserver auto` (2026-10-08) | **Serves:** R8 | **Topic:** guards | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_every_runtime_file_is_package_data.py`

## Motivation

From an installed wheel, `--jobserver auto` fails at the sandbox:

```text
bwrap: …/bga/_tools/native_trace/wrappers no such file or directory
```

`JOBSERVER_WRAPPERS_DIR` (`tools/bst_native_build_tracer.py:1568`) binds
`native_trace/wrappers/`, a directory with no `__init__.py`, and
`package-data` named only `*.c`/`*.h` for `bga._tools.native_trace`.
CI's packaging job checks `hook.c` alone and `installed-capture` runs
with the jobserver off.

## Required Fix

`package-data` names `wrappers/*` and `wrappers/flto/*`; a guard holds
every tracked non-`.py` file under a listed package to a glob of its
owning package, `tools/dev_run.sh` named as checkout-only. CI's
`installed-capture` takes a second snapshot with `--jobserver auto`.

## Out of Scope

The checkout-only modules the wheel also carries: `nix_*`, `sysroot_manifest`,
`toolchain_params` (absolute `from tools import`), twelve `dev_*`, and
`release-notes`, which reads `docs/backlog/` and reports "0 closed rows".

## Acceptance Test

The built wheel carries all eleven wrapper files, executable bits kept.

## Outcome (2026-10-08) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ pip wheel --no-deps -w w0 . && unzip -l w0/bga-0.6.0-py3-none-any.whl | grep -c wrappers   # on dee5e0fd
0
```

### After

```text
$ pip wheel --no-deps -w w4 . && unzip -l w4/bga-0.6.0-py3-none-any.whl | grep -c wrappers
11
$ pip install w4/*.whl && ls -l venv/.../bga/_tools/native_trace/wrappers/{ninja,flto/gcc}
-rwxr-xr-x ... ninja
-rwxr-xr-x ... flto/gcc
$ pytest -q tests/unit/test_every_runtime_file_is_package_data.py
2 passed
```

### Mutations verified red and reverted (2)

| # | mutation | reddened |
|---|---|---|
| A1 | `pyproject.toml` back to `["*.c", "*.h"]` | `test_every_tracked_runtime_file_is_package_data`, the eleven wrappers listed |
| A2 | `DEV_ONLY` emptied | both tests, `tools/dev_run.sh` listed |

### Deviation

`wrappers/*` alone also ships `flto/` today (4 files, measured), through
setuptools' deprecated pickup of importable directories; the guard
matches per path component, so the subdirectory names its own glob.
