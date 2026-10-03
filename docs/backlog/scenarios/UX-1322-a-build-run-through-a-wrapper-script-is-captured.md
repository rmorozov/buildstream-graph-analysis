# UX-1322: `bga snapshot -- ./build.sh` ends in a Python traceback; a project built through a wrapper cannot be captured

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_build_run_through_a_wrapper_script_is_captured.py`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga snapshot -- ./build.sh groups/all.bst
Compiling the trace hook...
Census: 1 of 6 element(s) assessed, ...
Traceback (most recent call last):
  ...
  File ".../bga/_tools/bst_run_wrapped.py", line 275, in run_wrapped
ValueError: command must start with 'bst', got: ['./build.sh', 'groups/all.bst']
$ bga snapshot --list
  20261003T135316Z       668B  (no run directory - the build produced no elements)
```

The refusal comes after the hook compile and census, and the husk's label is false: no build ran.
Real projects build this way (carbonOS: `just build` -> `tools/build` -> `bst --on-error continue build`).

## Decomposition

Input classes: `bst ...` (today); a script that execs `bst` once; a script that runs `bst` twice
(show then build); a `make`/`just` target; a command that never runs `bst`. Surfaces:
`bga snapshot`, `bga capture run`, `bga wrap`.

## Required Fix

A command not starting with `bst` runs with a `bst` shim first on its `PATH` that execs the real
`bst` and records the wrapped log of the `build` invocation (first line the real argv, as
`bst_run_wrapped` writes today). A command that ran no `bst build` is refused by name after it
exits, and the snapshot is not left as a husk claiming the build produced no elements. Any
refusal before the build happens before the hook compile.

## Out of Scope

Several `bst build` invocations in one command captured as one run (the first is recorded, the
rest named).

## Acceptance Test

On the stand-in, `bga snapshot -- ./build.sh groups/all.bst` produces a run with both planes;
a guard runs a wrapper command against a fake `bst` and asserts the recorded first line, and
asserts no traceback for a command that runs no `bst`. Reading taken in this container.

## Outcome

**Gap measured.** The Motivation's reading (walk, `19f1fd73`): `ValueError` out of `run_wrapped`
after the hook compile and census, and a 668 B husk listed as "the build produced no elements".

**Close measured.** `/root/walk/jproj` copied to `/tmp/ux1322-jproj` (`.bga` removed), `build.sh`
= `echo ...; exec bst --on-error continue build "$@"`, fresh `XDG_CACHE_HOME`, bst 2.8.1:

```text
$ bga snapshot -- ./build.sh groups/all.bst          # exit 0
build.sh: running bst --on-error continue build groups/all.bst
    Build Queue: processed 16, skipped 0, failed 0
Run directory: /tmp/ux1322-jproj/.bga/runs/20261003T144815Z/run
Processes traced: 2382 (2382 matched, 0 no observed exit)
Critical Path Length: 4 elements
$ head -1 .bga/runs/20261003T144815Z/build.log
[wrapper][2026-10-03 14:48:15,759] INFO: Executing command: bst --on-error continue build groups/all.bst
$ bga snapshot -- ./nobst.sh                          # exit 2
Error: `./nobst.sh` exited 0 without running `bst build`, so there was no build to capture. ...
Nothing was kept: /tmp/ux1322-jproj/.bga/runs/20261003T144919Z was removed.
$ bga snapshot --list
1 snapshot in /tmp/ux1322-jproj:
```

`bga wrap . out.log -- ./build.sh groups/all.bst`: same first line; `-- ./nobst.sh`: the same
refusal, exit 2, no log. A wrapper with `--jobserver` is refused before the hook compiles (its
pre-build `bst show` reads need the inner argv). The guard: 8 passed.

| mutation | reddened | count |
|---|---|---|
| shim records the real binary's path, not `bst` | first-line test, second-build test | 2 failed |
| shim records any subcommand, not only `build` | first-line test, second-build test | 2 failed |
| `run_wrapper_command` does not raise `NoBstBuild` | no-bst refusal test | 1 failed |
| snapshot keeps the directory on no `bst build` | no-husk test | 1 failed |
| `_path_without` keeps the shim's own directory | shim-never-finds-itself test (`-k`) | 1 failed |
| tracer's wrapper `--jobserver` refusal removed | refused-before-compile test | 1 failed |
| tracer's post-build swap to the recorded argv removed | readers-get-the-inner-argv test | 1 failed |
| `measure-again` hint ignores `capture-context.txt`'s wrapper | closing-hint test | 1 failed |

The closing `measure-again` hint repeats the wrapper the snapshot ran (`bga snapshot -- ./build.sh
groups/all.bst`), read from `capture-context.txt`; a `bst` command keeps `bst build TARGETS`.

### Deviation from the Required Fix

Wrapper plus `--jobserver` is refused; a wrapper that builds nothing exits 2; an absolute-path `bst` is a refusal. The post-build inner-argv swap was unguarded in the track and guarded in the fixup. `quality_baseline` S603/S606 entries were forced. `test_the_verification_log_is_true` also fails at base 44afd957. (`71c8dfae`)
