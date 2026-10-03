# UX-1325: `bga cache-logs PROJECT` reads only the top project's logs and says nothing about the junctioned projects beside them

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R3 | **Topic:** analysis | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_cache_logs_reads_every_junctioned_project.py`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. BuildStream writes logs per project (`~/.cache/buildstream/logs/acme-os`, `acme-platform`, `acme-base`).

```text
$ bga cache-logs .
Read 11 log(s), 5 of them builds, from acme-os
  apps/browser.bst ... pkgs/zlib.bst ... apps/editor.bst ... apps/shell.bst
```

4 of 13 building elements; nothing names the two skipped projects. On carbonOS those would be
`carbonOS-bootstrap` and `freedesktop-sdk`.

## Decomposition

Input classes: a project with no junction (today); local junctions (project name in the checkout's
`project.conf`); nested junctions; a remote junction whose name is only known to `bst`; a junction
whose project has no logs yet. Surfaces: `bga cache-logs PROJECT_DIR`, `--list`, `--project`.

## Required Fix

Given a project directory, cache-logs resolves the project names of every junction it can read
(local checkouts' `project.conf`, recursively) and reads those log trees too, element names
carrying their junction prefix; a junction whose project name it cannot resolve is named in one
line with `--project` as the way to add it.

## Out of Scope

Resolving remote junctions' names without `bst`.

## Acceptance Test

On the stand-in, `bga cache-logs .` reads all three projects and reports 13 building elements
with junction-qualified names; a guard over a three-project log tree fixture asserts it. Reading
taken in this container.

## Outcome

### The gap, measured

```text
$ bga cache-logs /root/walk/jproj      # at 44afd957, this container
Read 15 log(s), 9 of them builds, from acme-os
  apps/browser.bst ... pkgs/zlib.bst ... apps/editor.bst ... apps/shell.bst
```

4 of the 13 building elements; no line named `acme-platform` or `acme-base`.

### The close, measured

```text
$ bga cache-logs /root/walk/jproj
Read 41 log(s), 20 of them builds, from acme-base (via junctions/platform.bst:junctions/base.bst), acme-os, acme-platform (via junctions/platform.bst)
distinct building elements in the records read (stacks excluded): 13
  apps/{browser,editor,shell}.bst  pkgs/zlib.bst
  junctions/platform.bst:pkgs/{dbus,mesa,systemd,zlib}.bst
  junctions/platform.bst:junctions/base.bst:pkgs/{gcc-libs,glib,openssl,zlib}.bst
  junctions/platform.bst:junctions/base.bst:toolchain.bst
$ bga cache-logs /root/walk/carbon
  junctions/bootstrap.bst: a git junction with no local checkout to name its project - read its logs with --project NAME (`--list` names them)
  (and one such line each for bst-plugins-experimental.bst (git), bst-plugins.bst (tar))
$ pytest -n 1 -q tests/unit/test_cache_logs_reads_every_junctioned_project.py tests/unit/test_cache_logs.py
54 passed, 1 skipped
```

The phase table lists 12: `toolchain.bst` is an import whose build took 0 s, and
`phase_breakdown` has always left out zero-duration builds. The log count went from 38 to 41
during the session because other tracks were building.

### Mutation table

| mutation (`tools/bst_cache_logs.py`) | reddened | run |
|---|---|---|
| nested junction not recursed into | prefixes, qualified elements, header | 3 failed, 1 passed |
| element names left as the log wrote them | qualified elements (the standalone `gcc.bst` log) | 1 failed, 3 passed |
| `main` skips the junction walk | qualified elements, header | 2 failed, 2 passed |
| unresolved junction not printed | header | 1 failed, 3 passed |
| `--project` walks junctions too | `--project` reads one project | 1 failed, 3 passed |

Reverted from the copy: 4 passed.

### Deviation from the Required Fix

The phase table shows 12 of 13 building elements: `toolchain.bst` import builds in 0 s and `phase_breakdown` skips zero-duration. The "seen" dedupe clause is unguarded (no diamond fixture). (`abe0daea`)
