# UX-1328: `bga doctor` warns every project whose toolchain arrives through a junction to run bga's own example scripts

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_doctor.py::TestTheCensusChecksAreTwoDifferentThings`

## Motivation

On carbonOS build-meta, whose toolchain arrives through `junctions/bootstrap.bst`:

```text
  [warn] staged-sources: this project's own sources stage no executable at all - a sandbox with no shell cannot run install-commands
           -> examples/stage_runtimes.sh (busybox) or examples/stage_cpp_toolchain.sh (a real gcc/cmake sysroot), ...
```

`check_staged_sources` (`tools/bga_doctor.py:607-660`) counts only the top project's local
sources; the remedy names scripts in bga's repository, not the user's.

## Decomposition

Input classes: a project staging a shell itself; one whose toolchain comes from a junction; one
whose toolchain comes from a remote source or artifact; a bga example (the scripts are the right
remedy there).

## Required Fix

The warning fires only when nothing in the project or its local junctions stages an executable
and the project declares no junction or remote source; otherwise the check reports what it could
not see as info. The `examples/stage_*.sh` remedy is named only inside a bga example project.

## Out of Scope

Asking `bst` what the junctions stage.

## Acceptance Test

`bga doctor` on carbonOS prints no staged-sources warning; on an example project without its
staged toolchain it still does; a guard holds both. Reading taken in this container.

## Outcome

**The gap measured.** `bga doctor /root/walk/carbon` before (walk): `[warn] staged-sources: ... stage no
executable at all` with a remedy naming `examples/stage_runtimes.sh`.

**The close measured.** After, same command from this worktree:
`[ok] staged-sources: this project's own sources stage no executable, and a toolchain may arrive via
junctions/bootstrap.bst, junctions/bst-plugins-experimental.bst, junctions/bst-plugins.bst; some sources are
not local - not checked here`. `pytest -n 1 -q tests/unit/test_doctor.py` -> 43 passed, 8 skipped.
Bare project outside `examples/` still warns, with a remedy that names no bga script.

**Mutation table.**

| Mutation | Reddened | Count |
|---|---|---|
| `_is_a_bga_example` always true | bare-project remedy test | 1 failed |
| `_is_a_bga_example` always false | in-example remedy test | 1 failed |
| junction kind never matched | junction test | 1 failed |
| non-local source never matched | remote-source test | 1 failed |
| `if unseen:` never taken | junction + remote tests | 2 failed |
