# UX-102: the configure tax is measured twice and totaled never

**Priority:** Medium | **Status:** 🟡 In Progress — both planes ship and agree on a real dual capture; the fdsdk half waits on a capture | **Depends on:** UX-91 (Plane 3 phases), UX-45 (Plane 2 CPU per process)

Direction 3, item 3 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Every element that runs `cmake`/`configure` re-answers questions its
siblings already answered — compiler identity, ABI probes, header
checks. The tool measures this twice and concludes nothing:

- **Plane 3** parses each element's self-reported `Configuring` phase
  (round 11: 0.3-0.6s per cmake element on `examples/06`).
- **Plane 2** traces the probe processes themselves and already flags
  them as cross-element redundancy (the 9× `CMakeCXXCompilerId`
  compiles, the `cmake -B_builddir` configure runs, `m4`/autoconf
  probes on fdsdk).

Neither view sums to the number a build owner acts on: *"N% of this
project's element time is configure, and these elements pay the most"*.
On autotools-heavy projects (fdsdk's bootstrap is full of them), small
elements are routinely majority-configure — the classic case where the
remedies are known (config caches, merged elements, generated-config
reuse) and the missing piece is knowing the size of the prize.

## Required Fix

1. **Plane 3:** total and per-element configure share, same rendering
   pattern as UX-99's toll (they are siblings: toll is BuildStream's
   overhead, configure is the native build system's).
2. **Plane 2, where present:** classify traced processes into
   configure-phase vs build-phase (parentage under the configure
   command's process tree — the invocation records already carry the
   command) and publish per-element configure CPU. Where both planes
   cover the same run, print both numbers side by side; disagreement
   beyond the known 1s-resolution floor is itself a finding (UX-53's
   lesson: a quantity computed twice is a free test).
3. One project-wide finding with id, listing the top payers and the
   measured prize. Remedies stay one hedged sentence — the tool names
   the prize, not the patch.

## Out of Scope

- Implementing any caching/merging remedy.
- Distro-specific knowledge of which probes are cacheable.

## Acceptance Test

On the round-11 dual capture of `examples/06`: the per-element
configure share appears from both planes for the nine cmake elements,
the two figures agree within the documented resolution floor, and the
project-wide line totals them. On fdsdk (logs + native report from one
capture): the finding renders, autotools elements rank above cmake
ones, and the top payer is named with both measurements.

---

## Fix Implemented

Two measurements and a join, each in the plane that owns the evidence.

**Plane 3 — `configure_tax` in `tools/bst_cache_logs.py`.** cmake prints
`-- Configuring done (0.8s)`; this totals those lines per element and
project-wide. The limit is the whole reason this task needed a second
plane, and it is in the payload rather than only here: **only tools that
report their own timing are counted.** autotools' `configure` prints no
total and neither does meson, so on an autotools-heavy project — the
case the task was filed about — this returns a **floor of zero** for
exactly the elements most likely to be majority-configure.

**Plane 2 — `classify_configure_phase` in
`tools/bst_native_build_tracer.py`.** Every traced process descending
from a build system's configure entry point, by **parentage, not by
binary name**. That choice is what makes it work at all: an autotools
configure is hundreds of `sed`, `grep` and `cc conftest.c` processes,
and not one is distinguishable from build work by its own command line
— only by what started it. One pattern per entry point (`./configure`,
`config.status`, the autotools generators, `meson setup`, and `cmake`
*without* `--build`/`--install`/`-E`), and the process tree does the
rest.

Three limits, all of which make it an **under**-count, all published:
a static configure root is invisible to `LD_PRELOAD` and takes its
subtree with it; a process with no traced parent counts as build work
(defaulting the other way would inflate the number being argued for);
and `getrusage` reports nothing for a process killed by a signal, so
coverage is stated per element. Parentage resolves within a sandbox,
because pids are namespaced per sandbox and collide freely across them —
the same defect `pair_events` documents.

**The join — `bga cache-logs --native-report PLANE2.json`.** Both
figures per element, side by side, **never summed**: Plane 3's is the
tool's self-reported *wall* time, Plane 2's is kernel *CPU* time. And
one derived fact worth more than either column, `self_report_missing`:
an element with a large traced configure subtree and no self-report is
an autotools or meson element, which is precisely where the prize is
largest and the self-report blindest.

### Measured, on one real dual-plane capture of `examples/06`

Both planes from one `bga capture run --wrapped-log`, nine cmake
elements:

```text
Configure tax (Plane 3, self-reported): 3.7s of 32.0s element time (11.6%),
reported by 9 of 9 build log(s)
  Both planes, per element (wall vs CPU - shown, never summed):
    element                       Plane 3 wall  Plane 2 CPU  coverage
    core.bst                             0.70s        0.65s       81%
    codegen.bst                          0.70s        0.58s       81%
    lib-c.bst                            0.30s        0.32s       81%
    lib-f.bst                            0.50s        0.31s       81%
    lib-a.bst                            0.30s        0.30s       81%
```

```text
[medium] configure-tax: Configuring cost 3.7s self-reported, 3.4 CPU s traced
across this log tree (11.6% of element time) - paid most by codegen.bst,
core.bst, lib-f.bst, app.bst. Elements that configure independently re-answer
the same questions; config caches, merged elements or reusing a generated
config are the usual remedies, and which applies is a fact about the project
rather than about this measurement
```

**The two planes agree, and that is the result.** Across all nine
elements the Plane 2 / Plane 3 ratio is 0.62 to 1.05, with seven of nine
between 0.91 and 1.05 — two independent measurements, one from cmake's
own stopwatch and one from kernel `getrusage` over a process tree
reconstructed from `LD_PRELOAD` records, landing within a few percent of
each other. Neither was tuned to the other.

The one outlier is worth keeping rather than explaining away:
`lib-f.bst` reports 0.50s wall against 0.31s CPU, ratio 0.62. Wall
*should* exceed CPU during configure — it is a serial run of small
probes doing file I/O — so the surprising figures are the seven near
1.00, not this one. What that means is that on this project configure is
almost entirely CPU-bound probing, and `lib-f` happened to wait on
something. Recorded because a reader comparing the columns will see it.

### Not yet discharged

The acceptance's fdsdk half — *"autotools elements rank above cmake
ones, and the top payer is named with both measurements"* — needs a
capture carrying both the element-logs tarball and the native report.
One is running. It is also the only place `self_report_missing` can fire
against real data: every element in `examples/06` is cmake, so all nine
self-report and the count is 0. The mechanism has a unit test; the
population it was built for has not been seen yet.

Tests: 6 new in `test_cache_logs.py`, 6 in `test_native_build_tracer.py`.
Suite: 1262 → 1274.
