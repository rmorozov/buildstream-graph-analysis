# UX-37: Plane 2's redundant-operation findings report summed process time across elements that ran concurrently, and rank by it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-23 (done - this is a scoring/reporting fix to the detector it added), UX-26 (the same class of fix, already applied to Plane 1's batch report)

## Motivation

`UX-23` shipped `detect_redundant_operations`: real operations repeated independently inside multiple elements' own sandboxes. It works - a real run against `examples/05-cmake-cpp-toolchain` found 37 findings, every one correctly spanning all 6 cmake elements. The output, real, from that run:

```
  6x across 6 elements (['app.bst','core.bst','lib-a.bst','lib-b.bst','lib-c.bst','lib-d.bst']), 0.289s total:
    /usr/bin/ld -plugin /usr/libexec/gcc/x86_64-linux-gnu/13/liblto_plugin.so -plugin-opt=/usr/libexec/g
  6x across 6 elements (...), 0.246s total:
    /usr/libexec/gcc/x86_64-linux-gnu/13/cc1plus -quiet -imultiarch x86_64-linux-gnu -D_GNU_SOURCE CMake
  ...
  6x across 6 elements (...), 0.001s total:
    /usr/bin/uname -r
```

Three problems, in descending order of how much they cost the reader:

1. **`0.289s total` is summed process lifetime, not recoverable wall-clock.** Those six `ld` invocations ran inside six elements that BuildStream dispatched *concurrently*. Eliminating five of six saves close to nothing on the wall clock. The number that would justify acting - "if this were computed once and shared, the build would be N seconds shorter" - is not computed, and the number that is shown reads like it. This is exactly the category error `UX-26` fixed on Plane 1, where batch groups with zero real predicted savings were moved out of the text report; the same discipline has not reached Plane 2.
2. **The list is unfiltered and unranked by usefulness.** 37 findings, sorted by that same misleading total, down to `uname -r` at `0.001s`. A finding worth 1ms is noise regardless of how it is measured.
3. **The commands are truncated to ~100 characters**, which for `cc1plus`/`ld` invocations cuts off before anything distinguishing. Two structurally different findings can render identically.

The underlying detection is right and the finding it was built to demonstrate - CMake's compiler-ABI probe re-running once per element - is real and worth fixing. It is the scoring that cannot support a decision.

## Required Fix

1. Report a wall-clock-relevant figure, not a sum. At minimum, compute the redundant work's own critical contribution: for each group, the time by which the *earliest-finishing* elements could not have been shortened, versus the total. A cheap defensible version: report both `total process time` and `time on the longest single element`, and say which is which. The honest version simulates removal against the same `ReplayScheduler` Plane 1 already uses for `UX-20`'s batch simulation - larger, and worth considering since the machinery exists.
2. Drop or fold away findings below a real threshold, with an explicit count line rather than a silent drop - `UX-26`'s `(N further group(s) had no measurable combined effect, omitted)` is the house pattern.
3. Widen or intelligently elide the command rendering so two findings are distinguishable (keep the binary and the distinguishing arguments; elide the middle).
4. Group structurally-identical findings. The `examples/05` output contains many near-duplicate `cmake -E cmake_echo_color`/`cmake -E cmake_progress_start` entries that are one finding, not eight.

## Out of Scope

- The detection itself and the element tagging (`UX-23`), both correct.
- Actually sharing the redundant work (BuildStream-side caching/hoisting of a common configure step) - that is a build-design action for the user, not a tool feature.

## Acceptance Test

1. A real `examples/05-cmake-cpp-toolchain` trace no longer presents concurrent-element process-time sums as if they were recoverable wall-clock.
2. Sub-threshold findings (`uname -r` at 0.001s) are omitted from the text report with an explicit count.
3. Two structurally different `cc1plus` findings render distinguishably.
4. The CMake compiler-ABI probe finding - the one `UX-23` was built to catch - is still reported and is ranked highly. Full suite green.

## Verification Log

Filed 2026-08-16. The findings block is pasted from a real `tools/bst_native_build_tracer.py run` against a real `bst --builders 4 --max-jobs 4 build all.bst` of `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host) - 528 processes traced, 37 redundant-operation findings, reproducing `UX-23`'s own reported result.
