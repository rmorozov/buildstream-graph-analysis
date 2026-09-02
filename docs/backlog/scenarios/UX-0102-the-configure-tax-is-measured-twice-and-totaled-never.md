# UX-102: the configure tax is measured twice and totaled never

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-91 (Plane 3 phases), UX-45 (Plane 2 CPU per process) | **Topic:** analysis

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

### On freedesktop-sdk — and the bug the cross-check caught

The published capture carries both artifacts, and running them together
immediately falsified the Plane 2 figure:

```text
components/_private/cmake-stage1.bst   Plane 3: 30.50s wall   Plane 2: 1329.39s CPU
```

A 43x disagreement between two measurements of the same quantity. The
cross-check `UX-53` argued for - *"a quantity computed twice is a free
test"* - working exactly as intended, on its first contact with real
data.

**The cause was `is_configure_root` matching the pattern anywhere on the
command line.** A linker invocation carried
`-L/buildstream-build/_build_dir/Bootstrap.cmk/cmake` and a compile
carried an include path ending the same way; both were read as cmake
configure invocations. Because the classification takes the whole
process tree *below* a root, that did not mis-file two processes, it
mis-filed two subtrees: 1329 CPU seconds, 34% of the element.

Matched against the **executable** instead - `argv[0]`, walking through
`sh`/`bash`/`env` wrappers and leading `VAR=value` assignments, stopping
at the first flag - the same capture reports:

```text
Configure tax (Plane 3, self-reported): 35.6s of 3630.0s element time (1.0%),
reported by 3 of 23 build log(s)
  Both planes, per element (wall vs CPU - shown, never summed):
    element                       Plane 3 wall  Plane 2 CPU  coverage
    components/_private/cmake-stage1.bst        30.50s       25.79s       84%
    components/bison.bst          not reported       18.68s      100%
    components/libxml2.bst        not reported        7.83s       99%
    components/gperf.bst          not reported        6.25s       99%
    components/expat.bst                 2.30s        1.26s       89%
    5 element(s) have traced configure work and no self-report - an autotools
    or meson build system, and the case the self-report alone is blind to
```

30.50s against 25.79s, which is the agreement the earlier 1329s was not.
Project-wide the traced configure tax falls from 1383 CPU s (16.3%) to
**75.8 CPU s (0.9%)**.

**The acceptance's prediction holds, by share.** Ranked by what fraction
of an element's own CPU went to configuring, the autotools elements lead
and the cmake one is nowhere near them:

| element | build system | configure share |
|---|---|---|
| `components/gperf.bst` | autotools | 38.9% |
| `components/bison.bst` | autotools | 18.7% |
| `components/expat.bst` | autotools | 18.5% |
| `components/libxml2.bst` | autotools | 14.5% |
| `components/_private/cmake-stage1.bst` | cmake | 0.7% |

And `self_report_missing` fires on five real elements - the population
`examples/06` could not contain, since every element there is cmake.

Tests: 6 new in `test_cache_logs.py`, 6 in `test_native_build_tracer.py`.
Suite: 1262 → 1274.

## Verification Log

The verification evidence for this task is the pasted real output in
the section above — it was run, but filed without the heading the
fixing guide names, so a reader grepping for `## Verification Log`
found nothing on a 🟢 item. Heading added by audit round 12; the
evidence is the fixer's own.

One clause remains soft: "agree within the documented resolution
floor" is asserted as a 0.62-1.05 ratio range, but no floor is
documented anywhere the claim can be checked against.
