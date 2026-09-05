# UX-37: Plane 2's redundant-operation findings report summed process time across elements that ran concurrently, and rank by it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-23 (done - this is a scoring/reporting fix to the detector it added), UX-26 (the same class of fix, already applied to Plane 1's batch report) | **Topic:** capture | **Area:** tools

## Motivation

`UX-23` shipped `detect_redundant_operations`: real operations repeated independently inside multiple elements' own sandboxes. It works - a real run against `examples/05-cmake-cpp-toolchain` found 37 findings, every one correctly spanning all 6 cmake elements. The output, real, from that run:

```text
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

## Fix Implemented

Items 1-3, plus a fourth problem the fix surfaced. Item 4 (grouping structurally-identical findings) turned out to be largely handled by the same change and is not implemented separately - see below.

**1. A wall-clock-relevant figure.** Each finding now carries `max_element_duration_s` (what the single worst-affected element paid for this operation) and `worst_element`, alongside the existing `total_duration_s`, which stays because it is the honest "total machine time spent on this" number. Ranking switched to the wall-clock figure. Both are labelled in the report for exactly what they are: *"up to 0.542s recoverable wall-clock (worst element: app.bst); 1.406s total machine time"* - "up to", because sharing the work still costs whatever the shared version costs.

The full `ReplayScheduler` simulation this doc floated as "the honest version" was not attempted: Plane 2 has no shared horizon with Plane 1's replay model (`docs/design/architecture.md` is explicit about that), so wiring one to the other is a design change, not a scoring fix.

**2. Filtering.** Findings below `_REDUNDANCY_MIN_SECONDS` (0.05s) of recoverable wall-clock are omitted from the text report and kept in the JSON, with an explicit `(N further finding(s) below 0.05s ... omitted)` line - `UX-26`'s house pattern, no silent truncation.

**3. Command rendering.** `_elide_cmd` keeps the binary and leading arguments *and* the tail, eliding the middle. For a real `cc1plus` invocation the tail is where the actual input/output file is, which is precisely what the old fixed-prefix truncation cut off.

**4. The problem the fix surfaced.** Ranking by recoverable wall-clock immediately put `make -f Makefile -j4` and `cmake --build ...` in every top slot - each element's own build driver, whose signature is identical across elements *by construction* while doing entirely different work in each, and whose duration is that element's whole compile phase. Those are now excluded (`_is_element_build_driver`, matching through the wrappers real cmake projects use: `cmake -E env VERBOSE=1 /usr/bin/make ...`, `env DESTDIR=... cmake --build ... --target install`). The *configure* step is deliberately still considered - it really does repeat the same work in every element, and is the class of finding `UX-23` was built for.

That exclusion also does most of what item 4 asked: the near-duplicate `cmake -E cmake_echo_color`/`cmake_progress_start` entries that made the list look repetitive were mostly build-driver children, and the surviving list is 20 findings with 7 above threshold, down from 37 unfiltered.

Tests: 9 new (`tests/unit/test_redundancy_scoring.py`) - the wall-clock-vs-sum distinction, worst element named, ranking by the right figure, build drivers excluded and recognized through their wrappers, configure still counted, single-element repetition still not redundancy, and both elision cases. One existing `UX-23` fixture used a synthetic `cmake --build ...` command for what is really a `c++ -o .../CMakeCXXCompilerABI.cpp.o` probe; corrected to the real shape, which is what the test was always about.

## Verification Log

Filed 2026-08-16. Implemented the same day. The findings block is pasted from a real `tools/bst_native_build_tracer.py run` against a real `bst --builders 4 --max-jobs 4 build all.bst` of `examples/05-cmake-cpp-toolchain` (BuildStream 2.7.0, real `bwrap` sandbox, 4-core host) - 528 processes traced, 37 redundant-operation findings, reproducing `UX-23`'s own reported result.

Real end-to-end re-verification against a real 822-process capture of `examples/06-macro-micro-optimization` (the same class of trace as this doc's `examples/05` Motivation):

```text
Redundant cross-element operations (20 found, 7 above 0.05s):
  9x across 9 elements (...) - up to 1.311s recoverable wall-clock (worst element: app.bst); 4.880s total machine time
    cmake -B_builddir -H. -GUnix Makefiles -DCMAKE_VERBOSE_MAKEFILE=ON -DCMAKE_INSTALL_PREFIX:PATH=/usr ...
  9x across 9 elements (...) - up to 0.542s recoverable wall-clock (worst element: app.bst); 1.406s total machine time
    /usr/bin/c++ CMakeCXXCompilerId.cpp
  9x across 9 elements (...) - up to 0.284s recoverable wall-clock (worst element: app.bst); 0.567s total machine time
    /usr/libexec/gcc/x86_64-linux-gnu/13/cc1plus -quiet -imultiarch x86_64-linux-gnu -D_GNU_SO ... -o /tmp/ccKkFtNZ.s
  ...
```

Acceptance Test items 1-4 all confirmed with real data: no sum is presented as recoverable wall-clock, the sub-threshold findings (`uname -r` at 0.001s among them) are counted and omitted rather than listed, the elided `cc1plus` line now ends in the distinguishing `-o /tmp/...` rather than being cut off mid-boilerplate, and the CMake compiler-probe findings `UX-23` was built to catch are still reported and now rank second and third rather than being buried. Full suite green (731 passed, up from 722), `make lint` clean.
