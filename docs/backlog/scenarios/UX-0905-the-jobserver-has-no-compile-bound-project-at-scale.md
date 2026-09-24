# UX-905: the jobserver has no compile-bound project at the scale it is meant for

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-848 (the compile-bound example), UX-857 (`11-serial-giant`) | **Found by:** the 2026-09-20 rollout thread — the owner's own LLVM element is the target case and is blocked behind a ninja integration problem on their project, so the evaluation needs a project this repository can run | **Serves:** R5 and R4 (the mode's value, measured at a scale that can show it), R2 | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

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
