# UX-1205: a real capture of fake sleeping binaries under the LD_PRELOAD hook

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-158 walk and verification (2026-10-01) | **Serves:** R1 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_captured_workload_matches_its_plan.py`

## Motivation

Page: the round-158 walk and verification of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`) and its `--workload binaries` variant at `43397b70`, Chromium 1440x900 and 390x844.

Owner follow-up of `UX-1182`'s route (b), unanswered: `UX-1182` generates the binaries workload synthetically (112 elements, top-8 200-500 binaries); no capture has run fake sleeping binaries under the LD_PRELOAD hook. It needs a BuildStream host and cannot gate CI (runs158.md DECISION).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

A captured run of fake sleeping binaries under the hook, on a BuildStream host, whose page matches the synthetic workload's shape.

## Out of Scope

CI gating; the synthetic generator (`UX-1182`).

## Acceptance Test

A `bst`-marked test drives the capture and compares calls per element to the plan; a guard in a new `test_a_captured_workload_matches_its_plan.py`, skipped off a BuildStream host. Mutation: restore the defect, and the guard reds.

## Decision

Owner (Ruslan, 2026-10-01 05:48): "Ride bst-tests". The capture runs in CI's `bst-tests` job and gates; this overrides Out of Scope's "CI gating".

Architect (round 159, group B):

**It can run, in CI, without Ruslan's host.** The `bst-tests` job (.github/workflows/ci.yml:1274-1403) installs bst, bwrap and gcc, runs examples/stage_cpp_toolchain.sh, and runs `pytest -m bst`. It already captures Plane 2 under the hook: test_dual_plane_capture.py builds examples/05's core.bst through run_traced_build. Round 158's "cannot run in CI" (UX-1182 Decision, Rejected (b)) is wrong. The job gates: it fails on any SKIPPED and on a pinned "53 passed".

```text
Route:     a `bst`-marked test writes, at test time, a project from UX-1182's own plan at test size: one element of 200 distinct binaries and two of 3-10, 1-3 calls each, sleeps of 1-5 ms. Each fake binary is a copy of the staged sysroot's dynamic `sleep` under its planned name. The test builds the project with run_traced_build in bst-tests and compares Plane 2's exec count per element per binary to the plan, exactly.
Rejected:  host-only - a test skipped everywhere CI looks; full plan size (8 x 200-500 x 1-3) - about 3,000 execs per PR; a committed examples/17 - its elements derive from the plan (UX-996); bga_gen_project's static busybox runtime - LD_PRELOAD does not load into a static binary.
Files:     tools/gen_synthetic_scale_run.py (`workload_plan` extracted from `_workload_records`, which reads it); tools/bga_gen_project.py (`write_workload_project`); tests/unit/test_a_captured_workload_matches_its_plan.py; ci.yml bst-tests pin 53 -> 54.
Guard:     per planned element, Plane 2's records per binary name equal the plan's calls; the heavy element shows at least 200 distinct binaries.
Mutation:  the writer skips each binary's last call; a static binary copied instead of sleep.
```

Two departures, both measured:

- The staged sysroot has no `sleep` (`stage_cpp_toolchain.sh:54` stages env, sh, uname, sort, cat). The binaries copy the host's `sleep`, which is dynamic and links the host libc the sysroot's runtime axis already stages; the writer refuses an ELF with no `PT_INTERP`.
- `workload_plan(rng, building, heavy, spans, calls)` returns the raw per-call draws in `_workload_records`' original order, so the generator is a refactor, not a change: `gen-synthetic --store --seed 1 --runs 2 --workload binaries --layers 8 --width 14`, both runs' `plane2.log` sha256 `d52e6a7c…` / `39bbfb12…` before and after.

## Outcome

**The gap, measured** at `27f21d10`: `git grep -l fakebin 27f21d10 -- tests/unit` names one file, `test_the_synthetic_workload_runs_hundreds_of_binaries.py`, which reads the synthetic records and carries no `bst` mark; the tier pinned 53. No capture had ever exec'd the plan's binaries under the hook.

**The close, measured** in this container, which has no bst (`PYTEST_XDIST= python3 -m pytest tests/unit/test_a_captured_workload_matches_its_plan.py -q -rs`):

```text
....s
SKIPPED [1] ...:99: bst/bwrap/cc not all found on PATH - see docs/spec/ingestion-pipeline.md
4 passed, 1 skipped
```

`pytest -m bst --collect-only` collects 54, the new pin. The real capture's evidence is the PR's `bst-tests` run, which fails on any SKIPPED and on a count other than 54: that job, not this container, is where the bst half passes or reds.

| mutation | reddened | run printed |
|---|---|---|
| `workload_commands` emits `range(count - 1)`: each binary's last call skipped | `test_the_written_project_execs_each_planned_call` (and, in bst-tests, the capture) | 1 failed, 3 passed, 1 skipped |
| `is_dynamic` check off: a static binary accepted | `test_a_static_binary_is_refused` | 1 failed, 3 passed, 1 skipped |
| `_workload_records` draws its plan with no heavy set | `test_the_synthetic_records_are_the_plans_calls` | 1 failed, 3 passed, 1 skipped |
| `workload_plan` ignores the heavy span | `test_the_plan_has_the_test_size_shape` | 1 failed, 3 passed, 1 skipped |
| reverted from the backup copy | none | 4 passed, 1 skipped |

The bst half's own mutations (a skipped call, a static sleep giving 0 records) are unmeasured here: no bst.

Re-based in the same commit: `test_a_generated_project_builds.py`'s bst-gated file census 20 -> 21 and CAS-writing 18 -> 19 (this file builds through `_bst_env.bst_env`); the `bst/bwrap/cc` skip reason's measured count 6 -> 7 in `tests/conftest.py`.
