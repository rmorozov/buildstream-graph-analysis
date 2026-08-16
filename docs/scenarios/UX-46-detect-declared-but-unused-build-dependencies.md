# UX-46: no signal finds a declared-but-unused build dependency, and the cheap way of finding one does not work

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-11 (the Plane 2 hook), UX-23 (element tagging, which is what makes a per-element answer possible at all)

## Motivation

`examples/06-macro-micro-optimization` was built with three deliberate defects. `bga` finds two of them. The third - an over-declared build dependency - it does not find, and cannot: `docs/design-directions.md` names it as the round's own item (1), *"the one problem in that project that no `bga` signal found - it was found by knowing the project"*.

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

## Verification Log

Filed 2026-08-16 (round 2). `lib-b.bst`'s declared dependencies are quoted from the file in this repo. The per-element path sets and the link flags are from a real wrapped capture (`bst --builders 4 --max-jobs 4 build all.bst` of `examples/06-macro-micro-optimization`, BuildStream 2.7.0, real `bwrap` sandbox, 822 START lines), extracted by grouping every absolute-path token of every traced command line by its `element=` tag - not sampled and not summarized from the tracer's own report. The refutation is the load-bearing part of this filing: the hypothesis it kills was mine, formed earlier in the same session from reading the hook rather than from the data, and the measurement is what closed it. No fix work has been attempted.
