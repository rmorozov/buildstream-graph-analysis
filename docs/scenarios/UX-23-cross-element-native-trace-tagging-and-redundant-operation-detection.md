# UX-23: tag native-build traces with their owning element, and detect redundant cross-element operations

**Priority:** Medium | **Status:** 🔴 Not Started (design brainstorm only) | **Depends on:** `UX-11` (done - supplies the real per-process trace this builds on)

## Motivation

`docs/architecture.md`'s own "Where the two planes connect" section named a real, not-yet-built opportunity: Plane 1 (whole-project) can tell you which elements are expensive; Plane 2 (`UX-11`'s intra-element tracer) can tell you what one element's own native build system spent its time on - but running Plane 2 across *multiple* elements of the same project could reveal that they're each independently, redundantly doing the same real sub-work. This task is that brainstorm, performed for real rather than left as a hypothetical.

**Confirmed real, not speculative** - `tools.bst_native_build_tracer` wraps the *whole* `bst build` invocation, so a multi-element build already produces traced processes from every element's own sandbox in one raw log; the only thing missing is knowing *which* element each process belongs to. Ran a real, fully-fresh (`bst artifact delete` on every element first) `bst build all.bst` against `examples/05-cmake-cpp-toolchain` (6 real cmake elements: `core`, `lib-a..d`, `app`) under the tracer:

```
$ python3 -m tools.bst_native_build_tracer run --raw-log all_raw2.log \
    examples/05-cmake-cpp-toolchain all_report2.json -- bst --no-colors build all.bst
```

Grepping the raw trace for CMake's own compiler-ABI-detection probe (`CMakeCXXCompilerABI.cpp`/`cmTC_*` - a real, standard CMake step that fingerprints the compiler once per fresh build directory) found **90 real trace lines across 3 distinct time clusters** (sizes 15/60/15 - one solo element, four concurrent elements, one solo element again): exactly the real topology of `examples/05` (`core` alone → the 4-way `lib-a..d` fan-out → `app` alone). **Each of the 6 cmake elements ran its own, fully independent copy of the exact same compiler-capability probe** - the real cost of BuildStream's own sandbox isolation (no cross-element cache sharing is possible by design, each element gets its own fresh `_builddir`), made directly visible for the first time by this trace data. For this toy example the real per-probe cost is small (~75-340ms per cluster), but the *pattern* - identical, real, redundant work re-run once per element - is exactly the class of finding a much larger real C/C++ project's own `configure`/toolchain-detection/codegen steps would make far more costly.

## What's missing to detect this generally

1. **Element attribution.** The raw trace currently records `pid`/`ppid`/`ts`/`cmd` only - no notion of which BuildStream element a given process ran inside. This is a real, concrete, small addition: `tools/native_trace/bwrap_shim.py`'s `split_bwrap_args` already sees the element's own real path in BuildStream's generated argv (`--dir buildstream/<project-name>/<element>.bst`, confirmed present in every real captured invocation this whole `UX-11` arc has examined) - parsing the element name out of that and injecting it as one more `--setenv BST_TRACE_ELEMENT <name>` (the same injection pattern `BST_TRACE_LOG`/`LD_PRELOAD` already use) gives `hook.c` everything it needs to tag every trace line with its real owning element.
2. **Redundant-operation detection.** Once traces are element-tagged, group all traced processes across every element by a *normalized* command signature (strip absolute build-dir-specific paths/temp filenames - e.g. `/tmp/ccXXXXXX.s`, `_builddir`-relative paths - down to the real invocation shape: binary + stable flags + logical source file class) and flag any signature appearing under 2+ *different* elements as a real, concrete redundant-operation candidate, with real per-occurrence timing so the user can judge whether it's worth caring about (a 100ms probe repeated 6 times is very different from a 30s codegen step repeated 6 times).

## Out of Scope

- Any implementation - this is a design brainstorm, filed per this task's own scope.
- Automatically fixing/caching detected redundant operations (e.g. a shared pre-built toolchain-probe cache injected into every element's sandbox) - a real, much bigger design question (would need to reason about correctness: is the redundant operation's result actually invariant across elements, e.g. does every element share the exact same compiler/flags?) that should only be tackled once detection itself is real and has found genuine, costly redundancy in a real project - not attempted here.
- Normalizing/hashing command signatures robustly across arbitrary real-world command lines (path stripping, flag-order-insensitivity, etc.) - real, nontrivial text-normalization work of its own; the exact normalization strategy needs its own design pass once this task is picked up.

## Acceptance Test

1. Element-tagged raw trace: re-running the same real `bst build all.bst` capture against `examples/05-cmake-cpp-toolchain` produces trace lines each carrying a real, correct owning-element field, verified against the real known topology (core/lib-a..d/app).
2. Redundant-operation detector: run against the same real capture, correctly flags the real `CMakeCXXCompilerABI.cpp` probe as occurring in all 6 elements (matching this doc's own already-confirmed real finding), with real per-occurrence timing.
3. Full suite green.

## Verification Log

Filed 2026-08-16. Not implemented - the redundant-operation finding above is real (a real, fresh, fully-cleared `bst build all.bst` capture against `examples/05-cmake-cpp-toolchain`, not a hypothetical), but the element-tagging/detection mechanism itself is design-only.
