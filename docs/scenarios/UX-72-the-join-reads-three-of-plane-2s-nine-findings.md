# UX-72: the join reads three of Plane 2's findings and drops the rest, so "what to do next" is eight copies of the weakest one

**Priority:** High | **Depends on:** `UX-63`, `UX-68`, `UX-69` (all done — all three produce findings nothing consumes)

## Motivation

`bga correlate` is the command the workflow ends on: its heading is
literally `What to do next (ranked by Plane 1 impact)`. Here is all of it,
on round 9's real capture, with the repeated body elided:

```
components/_private/cmake-stage1.bst:
  - opened no file staged by 1 declared build dependency (...) - this is evidence, not a verdict
components/bison.bst:            - opened no file staged by 2 declared build dependencies (...)
components/doxygen.bst:          - opened no file staged by 1 declared build dependency (...)
components/openssl.bst:          - opened no file staged by 1 declared build dependency (...)
components/python3.bst:          - opened no file staged by 2 declared build dependencies (...)
components/expat.bst:            - opened no file staged by 1 declared build dependency (...)
components/gperf.bst:            - opened no file staged by 1 declared build dependency (...)
components/libxml2.bst:          - opened no file staged by 1 declared build dependency (...)
```

Eight elements. Eight rows. **One kind of finding**, and by the tool's
own words the least conclusive one it produces — `UX-68` established that
a runtime-only dependency is indistinguishable from an unused one from
here, which is why the sentence ends "this is evidence, not a verdict".

Meanwhile `native-report.json` from that same capture carries, per
element, measurements that are neither hedged nor repetitive:

| finding | task | in the JSON | read by `correlate` |
|---|---|---|---|
| `binary_cost` — where an element's CPU actually goes | `UX-69` | 11 elements | **no** |
| `peak_memory` — largest single process's RSS | `UX-63` | 11 elements | **no** |
| `redundant_operations` — same command across elements | `UX-23` | 599 findings | **no** |
| `aggregating_dependencies` | `UX-68` | present | **no consumer at all** |
| `per_element_parallelism` | `UX-32` | 11 elements | yes |
| `cpu_time.per_element` | `UX-45` | 11 elements | yes |
| `declared_vs_used.unused_candidates` | `UX-46` | present | yes |

`_plane2_view` reads three keys. The report the user is told to end on
therefore cannot say any of this, although every number is sitting in the
file it just opened:

- `cc1plus` is **81.3%** of `cmake-stage1`'s measured CPU across 885
  processes — the element that is 43.5% of the whole critical path is a
  C++ template compilation problem, which is a *different day's work*
  from "check a dependency edge".
- `dwz` is a **single** process holding 138.6s of wall time inside one
  element — an unparallelisable tail no `-j` value can help.
- `cmake-stage1` peaks at **1902 MB** in one process, so four concurrent
  builders need ~7.6 GB on a 16 GB runner.

Each of those is specific, unhedged, and points at one action. None
reaches the join.

## This is the reporting half of the same gap `UX-65` fixed for Plane 1

`UX-65`'s finding was that the tool *already computed* where the time
went and simply never put it where a reader looks first. This is the
identical shape one layer down: Plane 2's producers were fixed round after
round (`UX-45`, `UX-63`, `UX-68`, `UX-69`) and each new finding landed in
the JSON, in the tracer's own text report — and nowhere in the joined
view, because `_plane2_view` was written before any of them existed and
nothing ever went back to widen it.

`aggregating_dependencies` is the sharpest case: `UX-68` added it three
rounds ago, and it is currently rendered by nothing and read by nothing.
The user's own framing when that task was filed was "filter our report for
such cases and **have a full report where they stay**" — the filtering
shipped, the full report did not.

## Required Fix

1. **Widen `_plane2_view`** to carry `binary_cost`, `peak_memory` and the
   element's share of `redundant_operations` alongside what it already
   reads. The join key is unchanged; this is additive.
2. **Recommend from them.** The dominant binary of a heavy element, a
   single-process serialization point, and a peak RSS that multiplied by
   `builders` exceeds the host's memory are three concrete
   recommendations the join can already justify from measured data.
3. **Rank the evidence classes.** A measured 81.3%-of-CPU binary and an
   explicitly hedged dependency candidate should not print as two
   identically-weighted bullets. Strongest evidence first, and the hedged
   class last or behind a flag.
4. **Give `aggregating_dependencies` a home.** Either a `--full` /
   `--include-aggregating` switch on the reports, or a one-line summary
   ("N further dependency pairs excluded as aggregating — see JSON"), so
   the filtered-out population is visible rather than merely absent.
5. **Do not add a fourth ranking.** `UX-76` is about the report already
   carrying three overlapping orderings; this task must fold into the
   existing one, not open another.

## Out of Scope

- The redundancy findings themselves, which are separately wrong on real
  data — see `UX-73`. Wire the key, but wire it after that is fixed, or
  the join will inherit its false positives.
- Merging the planes. The contract stays one string, the element UID.

## Acceptance Test

1. On round 9's capture, `bga correlate` names `cc1plus` as the dominant
   cost of `cmake-stage1.bst`, and `dwz` as a single-process
   serialization point, in the "what to do next" block.
2. It reports `cmake-stage1.bst`'s 1902 MB peak against the run's
   `builders` value and the host's memory.
3. No element's row consists solely of the hedged declared-vs-used
   sentence when a stronger measured finding exists for it.
4. The count of dependency pairs excluded as aggregating appears
   somewhere a human reads, not only in the JSON.

## Verification Log

Filed 2026-08-18 (round 10 preparation). The eight-row output is `bga
correlate capture/run capture/native-report.json` at `74c94e3` against
the capture published as `5eda28a` (run `32064333551`). The key
inventory is `json.load(native-report.json).keys()` on that same file
(82 MB, 127,627 process records); the `cc1plus` / `dwz` / 1902 MB figures
are from `UX-69` and `UX-63`'s own verification logs on this capture.
