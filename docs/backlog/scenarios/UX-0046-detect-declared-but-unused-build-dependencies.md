# UX-46: no signal finds a declared-but-unused build dependency, and the cheap way of finding one does not work

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-11 (the Plane 2 hook), UX-23 (element tagging, which is what makes a per-element answer possible at all)

## Motivation

`examples/06-macro-micro-optimization` was built with three deliberate defects. `bga` finds two of them. The third - an over-declared build dependency - it does not find, and cannot: `docs/design/directions.md` names it as the round's own item (1), *"the one problem in that project that no `bga` signal found - it was found by knowing the project"*.

`elements/lib-b.bst` declares four build dependencies:

```yaml
depends:
- filename: lib-a.bst      # nothing in lib-b's sources uses lib-a's output
  type: build
- filename: core.bst
  type: build
- filename: codegen.bst    # nothing but lib-f uses codegen.bst
  type: build
- filename: toolchain.bst
  type: build
```

This is the single highest-value macro finding a build-optimization tool can produce, because removing such an edge is free: no source changes, no build-command changes, and the schedule immediately widens. It is also the defect a human is least likely to spot, since a redundant edge causes no failure and no warning - it only costs time, silently, forever.

**Round 2 tested the cheap way of detecting it and it does not work.** The hypothesis was that Plane 2 already records every process's full `/proc/self/cmdline`, so a declared dependency whose staged path never appears in any of the element's traced command lines is unused. Against a real 822-process wrapped capture of `examples/06`, that hypothesis is refuted. Grouping every absolute path in every traced command line by owning element gives, for **every one of the nine elements**, the same set:

```
/bin/sh  /usr/bin/{c++,cmake,make,ar,ld,ranlib,uname}
/usr/libexec/gcc/x86_64-linux-gnu/13/{cc1plus,collect2,liblto_plugin.so}
/usr/lib/gcc/x86_64-linux-gnu/13/{crtbeginS.o,crtendS.o,...}
/tmp/cc*.s  /tmp/cc*.o
/buildstream/macro-micro-optimization-example/<this element>.bst/...
```

Toolchain paths, temporaries, and the element's *own* source directory. Nothing else. The link lines confirm the reason - dependency artifacts are referenced by bare `-l` and default search paths, never by anything element-attributable:

```
-L/usr/lib/x86_64-linux-gnu  -L/usr/lib/gcc/x86_64-linux-gnu/13  -lstdc++ -lm -lgcc -lc
```

BuildStream stages every build dependency into one shared sandbox root. By the time a compiler runs, `codegen.bst`'s headers and `lib-a.bst`'s archive are indistinguishable from the base sysroot - they are all just `/usr`. **A command line cannot tell you which element a path came from, because the path does not carry that information.** Recording this here so the next attempt does not re-derive it: the cmdline shortcut is closed, and the cost of this task is the cost of the real mechanism.

## Required Fix

Detect which files an element's sandbox actually **opened**, then map those files back to the elements that staged them.

1. **Intercept file access in the hook.** `tools/native_trace/hook.c` is already an `LD_PRELOAD` library in every traced process; adding interposers for `open`/`openat`/`stat` (and the `at`-suffixed and `64` variants) is the standard mechanism and is what every "which files did this build read" tool does. This is a materially bigger change than the lifecycle hooks: it runs on a genuinely hot path (a single `cmake` configure opens thousands of files), so it needs buffering rather than the current open/`dprintf`/close per event, and it must stay inert and non-fatal when `BST_TRACE_LOG` is unset, exactly as today.
2. **Build the staged-path → element map.** This is the half that does not exist yet and is the real design question. `bst show`-derived data knows which elements are staged; what is needed is which *files* each contributed, which BuildStream knows from the artifact contents. Investigate whether artifact manifests can be read directly before considering anything that re-stages elements individually to diff them - that would be correct but would cost a full build per element.
3. **Report the unused set conservatively.** A dependency whose files were never opened is a *candidate* for removal, never an automatic verdict: runtime deps, deps needed only by a configure-time probe that got cached, and deps whose contribution is a directory's mere existence are all real. The output should name the declared dep, the element, and the evidence ("0 of 47 files staged by `codegen.bst` were opened during `lib-b.bst`'s build"), and leave the decision to the user - the same posture `UX-26`/`UX-34` take toward omitted candidates.
4. **State coverage honestly.** Statically-linked processes are invisible to `LD_PRELOAD` (`UX-11`'s Risk 2), so "never opened" is really "never opened by a process we could see". An element built entirely by a static binary would report every dependency as unused, which is the dangerous failure mode here and must be detected and refused rather than reported.

## Out of Scope

- Actually editing `.bst` files to remove the dependency. Reporting is the deliverable; rewriting a user's project is a different product decision.
- `UX-45` (real CPU time in the same hook). Independent, in the same file, and much cheaper - it should not be blocked behind this.
- Runtime (`type: runtime`) dependencies, which by definition are not read during the build and for which this method says nothing at all.

## Acceptance Test

1. A wrapped build of `examples/06-macro-micro-optimization` reports `codegen.bst` as unused by `lib-a`..`lib-e` - and **not** by `lib-f`, which genuinely consumes it. The false-positive half of that is the real test.
2. The same run does not report `core.bst` or `toolchain.bst` as unused by anything, since every element genuinely compiles against them.
3. `examples/06-macro-micro-optimization/optimized`, which has the redundant edges already removed, reports no unused dependencies.
4. An element whose processes are all invisible to the hook is reported as *uncovered*, not as having all dependencies unused. Full suite green.

## Fix Implemented

Both halves, plus the conservatism the task asked for.

**1. File-open interception.** `hook.c` interposes `open`/`open64`/`openat`/`openat64` and records unique absolute paths, flushed as one `OPENS` record per process at exit. It is **opt-in** (`--trace-opens` / `BST_TRACE_OPENS`) because, unlike the lifecycle hooks, it runs on a genuinely hot path. Every failure path degrades to "record nothing" and lets the real call through: `dlsym` is resolved lazily and a `NULL` means pass-through, a thread-local guard keeps the hook's own bookkeeping writes out of the record, and paths are deduplicated in a fixed hash set with a bounded arena so memory cannot grow with the build.

**2. The staged-path → element map, which turned out to already exist.** The task called this "the half that does not exist yet"; `bst artifact list-contents` supplies it directly, from BuildStream's own artifact metadata, with no re-staging and no per-element rebuild. That removes the expensive fallback this doc worried about.

**3 & 4. Refusal over guessing.** An element with no observed opens is reported `uncovered`, not "used nothing" - an element built entirely by statically-linked processes looks identical, and reporting all its dependencies as unused would be catastrophic. An element whose hook dropped paths is likewise `uncovered`, since a truncated read set is exactly what turns a used dependency into a false unused. Dependencies whose artifact contents cannot be read are `skipped` with a reason.

### The real result

A real `--trace-opens` build of `examples/06-macro-micro-optimization` (BuildStream 2.7.0, real `bwrap`, 822 processes, 114 `OPENS` records, **zero** dropped paths):

```
Declared build dependencies never read: 24 candidate(s) across 7 element(s); 9 edge(s) confirmed used
  app.bst      never read: core.bst, lib-a.bst, lib-b.bst, lib-c.bst, lib-d.bst, lib-e.bst, lib-f.bst
  lib-a.bst    never read: codegen.bst, core.bst
  lib-b.bst    never read: codegen.bst, core.bst, lib-a.bst
  ...
  lib-f.bst    never read: codegen.bst, core.bst, lib-e.bst
```

**`toolchain.bst` is the only dependency any element actually reads** - 51 of its 8369 staged files, and 68 for `app.bst`. That it comes back *used*, on every element, is the control that shows the detector is not simply reporting everything as unused.

### Two of this doc's own acceptance criteria were wrong

Criterion 1 expected `codegen.bst` to be unused by `lib-a`..`lib-e` but **used** by `lib-f`, and criterion 2 expected `core.bst` never to be reported unused. Both came from the example project's own comments. The measurement contradicts both, and the measurement is right:

- `lib-f`'s sources `#include` only `lib-f.hpp`, `<array>`, `<cstddef>` and `<utility>`. Nothing in the project includes `codegen.hpp`.
- Every lib includes its own header **from its own source directory** (`#include "lib-a.hpp"`), not from the staged `/usr/include`. `core.hpp` is referenced only inside `core` itself.
- `app`'s `CMakeLists.txt` is `add_executable(app ${SOURCES})` with no `target_link_libraries`, so it links none of the libraries it declares.

So in `examples/06`, the **entire** cross-element build-dependency structure is decorative - which is what that project always claimed about two specific edges ("removing them changes no source file and no build command") and is now measured to be true of all 24. The element comments have been corrected: they asserted that `lib-f` consumed `codegen.bst`, which it never did.

Criterion 3 (the `optimized/` variant reporting no unused dependencies) is wrong for the same reason and for the same project: its remaining edges are decorative too.

**What this costs, and what it does not.** The example cannot demonstrate the "declared, and genuinely used, between two project elements" case, so the true-negative evidence rests on `toolchain.bst` - a real cross-element dependency that is correctly reported as used by all nine elements. That is genuine discrimination, but a project whose elements actually consume each other's headers would be a stronger fixture, and is the recommended follow-up rather than something quietly assumed here.

### Follow-up done: both directions now tested (2026-08-17)

`examples/07-declared-vs-used-dependencies` was built for exactly the gap named above. `user.bst` and `unrelated.bst` declare **identical** dependencies (`base.bst` + `toolchain.bst`) and differ in one respect only: `user.cpp` does `#include <base.hpp>`, resolving to `base.bst`'s staged header, and `unrelated.cpp` includes nothing from it.

Real `--trace-opens` build of that project:

```
Declared build dependencies never read: 1 candidate(s) across 1 element(s); 4 edge(s) confirmed used
  unrelated.bst              never read: base.bst  (5 staged file(s))

  user.bst      -> base.bst   1/5 staged files opened   <- correctly NOT flagged
  unrelated.bst -> base.bst   0 of 5 files opened       <- correctly flagged
```

`user.bst` opens exactly one of `base.bst`'s five staged files - `/usr/include/base.hpp`, the one it includes. An over-eager detector would flag both elements; an inert one would flag neither. This is the discrimination the `examples/06` evidence could not show, and it closes the caveat above.

### A design error caught by real data

The first implementation derived "direct" dependencies by subtracting transitive closures out of `bst show --deps build`. On real data it dropped three of `lib-b.bst`'s four declared dependencies: `codegen` and `core` are *also* inside `lib-a`'s closure, so subtraction classified them as indirect. **The dependency being redundant is precisely the thing being detected**, so inferring directness from the closure hides the finding. Declared dependencies are now read from the element files themselves, which is also what "declared" has to mean if a recommendation is going to be acted on by editing one.

Tests: 11 new (`tests/unit/test_declared_vs_used.py`), concentrated on the dangerous failure modes - an uncovered element must not have all its dependencies reported unused, a truncated read set must refuse, an unreadable artifact must be skipped, and a truncated `OPENS` block must not swallow the next element's record. Full suite 863 passed, `make lint` clean.

## Verification Log

Filed 2026-08-16 (round 2). `lib-b.bst`'s declared dependencies are quoted from the file in this repo. The per-element path sets and the link flags are from a real wrapped capture (`bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization`, BuildStream 2.7.0, real `bwrap` sandbox, 822 START lines), extracted by grouping every absolute-path token of every traced command line by its `element=` tag - not sampled and not summarized from the tracer's own report. The refutation is the load-bearing part of this filing: the hypothesis it kills was mine, formed earlier in the same session from reading the hook rather than from the data, and the measurement is what closed it. No fix work has been attempted.
