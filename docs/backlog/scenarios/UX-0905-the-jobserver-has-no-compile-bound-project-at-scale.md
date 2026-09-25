# UX-905: the jobserver has no compile-bound project at the scale it is meant for

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** UX-848 (the compile-bound example), UX-857 (`11-serial-giant`) | **Found by:** the 2026-09-20 rollout thread — the owner's own LLVM element is the target case and is blocked behind a ninja integration problem on their project, so the evaluation needs a project this repository can run | **Serves:** R5 and R4 (the mode's value, measured at a scale that can show it), R2 | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

Direction 20's bar is that the mode is supported when a compile-bound
capture's **wall clock** moves. The projects that have judged it are
small: `examples/10-jobserver` is four elements on four cores and read
slower at every stage; `examples/11-serial-giant` is one long element
under `max-jobs: 2` and read `auto` at −10.6%; a scaled field pair read
−13.4%. All three are minutes of build, and the case the mode exists for
is the opposite shape — one enormous compile-bound element (an LLVM, a
cross toolchain) that owns the machine for forty minutes and takes
BuildStream's default `max-jobs` while the rest of the agent idles.

The owner has that element and cannot reach it for now. So the
evaluation needs a project this repository can run itself, and there are
three candidates, in rising cost: `freedesktop-sdk`, which CI already
captures weekly and whose `captures/*` refs are published; another
public BuildStream project that builds LLVM or a cross-compilation
toolchain; or a staged example of this repository's own, built the way
`05`-`12` stage their sysroot.

## Required Fix

Choose one and run the mode against it, with the wall clock as the
verdict and the envelope as the explanation. The choice is the work:
`freedesktop-sdk` is available today and its shape is known (an
incremental capture is dominated by a handful of long elements, which is
the right shape) but an hour per arm makes repeats expensive; a
purpose-built example is cheap to repeat and has to be argued not to be
a synthetic that flatters the mode.

Whatever is chosen, the reading is a pair of arms on one quiet box, with
repeats, and it lands in the mode's own record beside the three readings
above rather than replacing them.

## Decomposition

surfaces: `examples/` (if an example is chosen), `.github/workflows/real-project-capture.yml` (if `freedesktop-sdk` is), Direction 20's status block, and the jobserver's reading record
guards: the CI job that runs the chosen arms, and the guard that the mode's status block cites a reading whose capture exists
gap: no public BuildStream project that builds LLVM is known to this repository — finding one is step 0, and its absence is what makes the choice judgement
track: session's own
gate: after `UX-895`, whose overhead number the arms have to be read against
quiet box: not GitHub's runners - one fdsdk recipe, three auto arms and two off, spent 8383 to 11592 CPU seconds on the same work, and the concurrent pair landed on an EPYC 7763 (off, 11592) and a 9V74 (auto, 8383) (runs 35994560797, 35994562807, round 141)

## Out of Scope

Changing the mode's default, which Direction 20 gates on this reading.
The owner's own project, which is blocked on their side.

## Acceptance Test

Two arms on the chosen project, repeats stated, pasted with the host
class and the date: wall clock, the jobserver block's two shares, and
peak memory per arm. The record names which of Direction 20's three
stages was running. A second run of the same recipe reproduces the
arms — not the numbers, which are a machine's, but the procedure.

## Outcome

Partial. Chose `examples/11-serial-giant` (UX-1009's aarch64 staging),
run on CodSpeed's Graviton macro runner (16 real Cortex-A72 cores, 31 GB,
Ubuntu 22.04, `bst` 2.8.1, 2026-09-25) rather than `freedesktop-sdk` — a
real-core host reachable now, at the project this repository already
stages. Recorded in Direction 20's own status block
(`docs/design/directions.md`), beside the three prior readings:

```text
pairs off  | wall 139.91s cpu 752s giant-peak 8;  139.20s 752s 8;  138.71s 749s 8
pairs auto | wall 113.28s cpu 845s giant-peak 16; 112.19s 841s 16; 112.20s 840s 16
```

(`bst`'s own `max-jobs` default = min(cpus, 8) = 8; 3 interleaved
repeats; CPU = host-wide `/proc/stat` busy-seconds delta; peak = the
capture's Plane 2 `peak_work_concurrency`; run 36086044196.) `off`
averaged 139.27 s wall (spread 0.9 %), `auto` 112.56 s (spread 1.0 %):
`auto` IMPROVED -19.2 %, explained by the giant's peak concurrency
moving 8 to 16 against the calibrated effective-core curve (`UX-1009`'s
calibration: width 8 → 29.30 s, width 16 → 22.24 s, effective 5.98 of
16); host CPU seconds +12 % (751 to 842), the expected cost of running
more concurrently on a CPU-bound compile.

Not met: the Acceptance Test also asks for peak memory per arm, which
this capture never measured, and "the guard that the mode's status
block cites a reading whose capture exists" (Decomposition) does not
exist yet — no test asserts the status block's readings against a real
capture ref, so this reading is prose only, unguarded. Status stays In
Progress rather than closing.
