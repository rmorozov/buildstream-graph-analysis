# UX-23: tag native-build traces with their owning element, and detect redundant cross-element operations

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-11` (done - supplies the real per-process trace this builds on)

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

## Fix Implemented

Both pieces built exactly as designed above, plus one real correctness bug found only by implementing element-tagging for real:

1. **Element attribution**: `tools/native_trace/bwrap_shim.py`'s new `extract_element_name(opts)` parses the real `--dir buildstream/<project>/<element>.bst` option BuildStream's own generated bwrap argv always includes, and `build_shim_argv` injects it as one more `--setenv BST_TRACE_ELEMENT <name>` alongside the existing `LD_PRELOAD`/`BST_TRACE_LOG` injections. `hook.c` reads it at load time and appends `element=<name>` (or the literal `unknown` when unset, for backward compatibility with a pre-`UX-23` capture or standalone single-element use) to every trace line, between `ts=` and `cmd=`.
2. **A real correctness bug found while wiring this up, not by unit tests alone**: `pair_events` (UX-11's own original design) paired START/END events by pid alone - correct for a *single* element's own `--unshare-pid` namespace, but **unsound once a trace spans multiple elements**, since every element gets its own independent PID namespace and the same small pid number (the low numbers a fresh namespace always starts from) recurs across every element's own sandbox, referring to a *different* real process each time. Fixed by re-keying the whole FIFO-pairing algorithm on `(element, pid)` instead of `pid` alone - a real fix, not just an addition, and one that stayed latent in `UX-11`'s own testing precisely because it only ever traced one element at a time.
3. **Redundant-operation detection**: `normalize_cmd_signature` (a deliberately narrow, heuristic normalization - strips the real, confirmed sources of spurious per-element uniqueness this design actually observed: per-element absolute build paths, gcc/binutils temp filenames, CMake's own randomly-suffixed try-compile scratch directories) plus `detect_redundant_operations`, which groups matched, element-attributed records by normalized signature and flags any signature spanning 2+ *distinct* real elements, sorted by real total duration (most costly first). `unknown`-element and still-`open` records are excluded entirely - never claim cross-element redundancy for a process this tool couldn't actually attribute.
4. Both `summarize()`'s report (`by_element`, `redundant_operations`) and `_format_text`'s human-readable output were extended to surface both new pieces.

Tests: 15 new (`tests/unit/test_bwrap_shim.py` +5 for `extract_element_name`/its injection; `tests/unit/test_native_build_tracer.py` +10 for element-tagged parsing, the cross-element pairing correctness fix, `normalize_cmd_signature`, and `detect_redundant_operations`).

## Out of Scope

- Any implementation - this is a design brainstorm, filed per this task's own scope.
- Automatically fixing/caching detected redundant operations (e.g. a shared pre-built toolchain-probe cache injected into every element's sandbox) - a real, much bigger design question (would need to reason about correctness: is the redundant operation's result actually invariant across elements, e.g. does every element share the exact same compiler/flags?) that should only be tackled once detection itself is real and has found genuine, costly redundancy in a real project - not attempted here.
- Normalizing/hashing command signatures robustly across arbitrary real-world command lines (path stripping, flag-order-insensitivity, etc.) - real, nontrivial text-normalization work of its own; the exact normalization strategy needs its own design pass once this task is picked up.

## Acceptance Test

1. Element-tagged raw trace: re-running the same real `bst build all.bst` capture against `examples/05-cmake-cpp-toolchain` produces trace lines each carrying a real, correct owning-element field, verified against the real known topology (core/lib-a..d/app).
2. Redundant-operation detector: run against the same real capture, correctly flags the real `CMakeCXXCompilerABI.cpp` probe as occurring in all 6 elements (matching this doc's own already-confirmed real finding), with real per-occurrence timing.
3. Full suite green.

## Verification Log

Filed 2026-08-16 as a design brainstorm - the redundant-operation finding was real from the start (a real, fresh, fully-cleared `bst build all.bst` capture against `examples/05-cmake-cpp-toolchain`), but the mechanism itself was design-only.

Implemented for real the same day. 15 new tests, full suite green: 628 passed (up from 611), same 7 pre-existing environment-only failures as `main`. `make lint` clean.

Real end-to-end re-verification against `examples/05-cmake-cpp-toolchain`'s `all.bst` (all 6 elements, `bst artifact delete` on every element first for a fully fresh capture):

```
$ python3 -m tools.bst_native_build_tracer run --raw-log ux23_raw.log \
    examples/05-cmake-cpp-toolchain ux23_report.json -- bst --no-colors build all.bst
```

`process_count: 528`, correctly attributed by element (`by_element: {'core.bst': 98, 'lib-d.bst': 88, 'lib-a.bst': 88, 'lib-c.bst': 88, 'lib-b.bst': 88, 'app.bst': 78}`) - the real, known 6-element topology, exactly. **37 redundant-operation findings, every single one correctly spanning all 6 real elements** (`['app.bst', 'core.bst', 'lib-a.bst', 'lib-b.bst', 'lib-c.bst', 'lib-d.bst']`), including the exact `CMakeCXXCompilerABI.cpp` probe family this task's own Motivation first found manually - now detected automatically, with real per-finding timing (e.g. `12x across 6 elements, 0.030s total` for `cmake -E cmake_progress_start`). Both Acceptance Test items satisfied with real evidence, not synthetic fixtures alone.
