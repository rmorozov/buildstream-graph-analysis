# UX-09: `--builders` and native `max-jobs` compete for the same CPU cores

**Priority:** High | **Status:** 🟢 Done (documented + demonstrated for real) | **Depends on:** none

## Motivation

The user's own hypothesis, going into `examples/05-cmake-cpp-toolchain` (a second, more realistic round of UX-05's optimization walkthrough - real C/C++ compiled through CMake + GNU Make, not `sleep N`): BuildStream's own scheduling concurrency (`--builders`) and each native build system's *own* internal parallelism (`make -jN`, propagated per-element) both consume the same physical CPU cores, with no coordination between them - meaning "optimal build configuration" is a genuine multi-factor optimization problem, not a single knob. Asked to brainstorm whether this is erroneous, and to prove it with facts.

**Verdict: confirmed, not erroneous - with real evidence on both the source-code and empirical sides.**

## Evidence: the mechanism is real

Checked directly against the real installed BuildStream 2.7.0 + `buildstream-plugins` 2.7.0 source, not documentation:

1. `buildstream_plugins/elements/cmake.yaml`: `environment: JOBS: -j%{max-jobs}`, used as `make: cmake --build %{build-dir} -- ${JOBS}`. `make.yaml`: `environment: MAKEFLAGS: -j%{max-jobs}`. Every `cmake`/`make`/`autotools` element independently launches its own parallel compile job, sized by `%{max-jobs}` - entirely separate from `--builders`, which only limits how many *elements* run concurrently.
2. `buildstream/data/userconfig.yaml`: `builders: 4` (default). `buildstream/_context.py`: `effective_build_max_jobs` defaults to `self.platform.get_cpu_count(8)` - i.e. `min(host_cores, 8)`. Out of the box, zero tuning, on an 8+ core machine that's `4 builders × 8 jobs = 32` potential concurrent compiler processes.
3. `buildstream/_context.py:739`: `local_jobs=self.sched_builders * self.effective_build_max_jobs` - BuildStream's own source computing this exact product (to size CASD's job budget), proving the team knows it matters - but that arithmetic is never applied to the actual compiler processes themselves, only to CASD.
4. Grepped the entire installed `buildstream` + `buildstream_plugins` tree for `jobserver` - zero matches. GNU Make's own jobserver token-passing protocol (invented specifically to coordinate *recursive* sub-makes) has no analogue across BuildStream sandboxes - each element's `make -jN` claims its jobs completely blind to how many sibling elements are compiling at the same moment.
5. BuildStream's real remote-execution sandbox path is real (`sandbox/_sandboxremote.py`, `_sandboxreapi.py`) - when active, compute happens on a remote worker pool whose size/scheduling is invisible to the local client; only the CAS is observable/tunable locally. `bga` extracts everything from local BuildStream logs, so in that mode it has nothing to observe about the real bottleneck at all.

## Evidence: the effect is real and measurable, not just theoretical

Built `examples/05-cmake-cpp-toolchain`: a full, real gcc/g++/cmake/make/binutils sandbox (`examples/stage_cpp_toolchain.sh`, staged from the host's own installed toolchain - see that script's own header for the real trial-and-error this took), five real static-library modules with generated, genuinely CPU-heavy C++ source (`generate_sources.py` - calibrated by direct measurement: ~1.5-2s of real `g++ -O2` compile time per generated file, not `sleep`), one 4-way fan-out (`core.bst` → `lib-a..d.bst`), one linking executable (`app.bst`).

Real wall-clock time (`time bst --builders B --max-jobs J build all.bst`, cache cleared between each run, this host has 4 real cores) across six configurations:

| builders × max-jobs | real wall-clock |
|---|---|
| 1 × 1 (fully serial) | 14.2s |
| 1 × 4 | 8.4s |
| 4 × 1 | 8.7s |
| **4 × 4 (BuildStream's own defaults)** | **6.5s (best)** |
| 4 × 16 (heavy intra-element oversubscription) | 6.4s (~flat - diminishing returns, each lib only has 2 files) |
| 8 × 8 (heavy oversubscription on both axes) | 7.2s (**worse** than 4×4) |

Three real, distinct effects, all confirmed on one machine, one project, same source:
- **Both knobs matter independently**: 1×1 → 4×4 is a 2.2x real speedup.
- **Oversubscription genuinely costs real time, not just theoretically**: 8×8 (up to 64-way concurrency on 4 cores) is ~11% *slower* than 4×4, not just "not faster" - real evidence naive "turn everything up" is wrong.
- **Diminishing returns are real too**: 4×16 barely differs from 4×4, because each `lib-*.bst` here only has 2 source files - `max-jobs` beyond the real per-element file count buys nothing.

## Implication for `bga`

`bga`'s current model (`tools/bst_extract_run.py`'s own docstring, confirmed) treats `resource_capacities.PROCESS = builders` as *the* capacity constraint and assumes each concurrently-building element consumes exactly 1 unit of it for `LB`/`efficiency_score` purposes. That's accurate for how BuildStream *dispatches elements*, but not for real CPU contention once `max-jobs` fans out inside each one - `bga` has no visibility at all into what happens inside a "Running commands" span (BuildStream logs exactly one START/SUCCESS pair per element's build phase, regardless of how many `make -jN` sub-processes ran inside it). So "optimal configuration" is a real `(builders, max-jobs, host cores)` joint problem, and today `bga` only has instrumented visibility into one axis (`builders`) and zero visibility into the other two.

This is the direct motivation for `UX-11` (a real, separate tool to observe native-build-system behavior *inside* a single element) - filed as its own backlog item since it's substantial, independent work, not something to bolt onto the existing analyzer.

## Out of Scope (this task)

- Actually building `UX-11`'s intra-sandbox profiler - filed separately.
- Fixing `bga`'s `LB`/capacity model to account for `max-jobs` - would need real design work (what's the right model for "an element that itself fans out to N processes"?) rather than a quick patch; not attempted here.

## Verification Log

Done for real, 2026-08-15/16. Real toolchain built and verified end-to-end (bwrap smoke test: compile+link+run a real C++ program; `cmake -G "Unix Makefiles"` configure+build+run). Real BuildStream project (`examples/05-cmake-cpp-toolchain`) built for real across the 6 configurations in the table above, each independently timed with `time`, cache cleared between runs. Source citations for all 5 evidence points independently re-read from the real installed package files (not from memory/docs). Full suite green (`make lint`, `pytest`) - see the round's PR.
