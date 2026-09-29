# `bga analyze` after round 150: what is graph-only, what the trace decides

Ruslan's review of PR #300 asked for a post-fix profile before the next
performance row, and for how much of the remaining analysis is a
function of the graph alone, reusable across captures with an equal
graph fingerprint (`UX-1083`). Measured on `24507594`.

## Fixture and commands

Round 150's 5,002-element store and Plane 2 report
([the snapshot audit](perf-snapshot-view-2026-09-28.md)'s recipe,
`genlog.py` P=80 U=50): `bga gen-synthetic $S/l --store --seed 1
--layers 40 --width 125`, then `plane2.json` (10.2 MB) beside each run.
Host: 4 × Xeon 2.10 GHz, 16 GB, Python 3.11.15; `uptime` load 0.1-1.4.

```text
bga analyze <run>    best of 3   wall 14.07 s   VmHWM 469 MB   (runs 14.60 / 14.31 / 14.07; load 0.57)
cProfile             30.94 s under the profiler (2.2x)
```

VmHWM from the child's own `/proc/self/status`; per stage, exclusive wall
and peak RSS, `/proc/self/clear_refs` `5` reset at every stage boundary.

## cProfile (top 12 of 30 each; seconds under the profiler)

```text
cumulative                                    tottime
15.21 _compute_diagnostics                    4.42 edg.py:259 <genexpr>  (bitset decode, 7.2M calls)
 8.88 compute_blast_radius                    2.32 dict.get (16.2M calls)
 5.38 ReachabilitySets.__getitem__ (5,747)    1.89 _compute_perturbed_critical_path (200)
 4.37 _compute_utilization                    1.68 utilisation <genexpr> (12.3M)
 4.29 _compute_underparallel_idle_us          1.66 utilisation <genexpr> (24.6k)
 3.22 _compute_attribution                    1.60 blast weighted-sum <genexpr> (7.2M)
 3.20 compute_criticality_probability         1.10 _iter_saturation_intervals (600k)
 2.75 compute_critical_path (65 calls)        1.10 compute_critical_path (65)
 2.68 compute_ready_queue_metrics             1.07 _estimate_ready_count (4,926)
 2.51 _compute_perturbed_critical_path        0.96 ReachabilitySets.__getitem__
 2.29 _build_optimization_outlook             0.92 build_element_graph (78 calls)
 1.93 _attach_plane2_capacity                 0.90 builtins.any
```

## Stages, unprofiled (best of 3 stage runs: 12.47 s; exclusive s, RSS MB)

```text
stage                                  class        s     RSS in -> peak
ReachabilitySets decode (5,747 sets)   graph-only  2.88    87 -> 419   inside blast radius
compute_criticality_probability        Plane 1     1.34   419 -> 421
_compute_utilization                   Plane 1     1.13    80 ->  84
_compute_attribution                   Plane 1     1.05    75 ->  80
compute_blast_radius (own)             Plane 1     0.89   the weighted sum over the decoded sets
_attach_plane2_capacity                Plane 2     0.87   439 -> 470   the process peak
compute_ready_queue_metrics            Plane 1     0.87
build_element_graph (78 calls)         graph-only  0.61
compute_critical_path (65 calls)       Plane 1     0.56
structural run_full_analysis           Plane 1     0.39   432 -> 439
build_edg                              graph-only  0.25   425 -> 431
compute_in_out_degree (73 calls)       graph-only  0.20
load / normalize                       mixed / P1  0.07 / 0.08   45 -> 62
import, fingerprint, render            fixed       0.26    37 -> 41
```

## Classification

Read from the code, then confirmed on three runs over one `graph.json`
(`PYTHONHASHSEED=0`, each stage's output digested): A; B = A with every
span's `dur_us` × U(0.7, 1.0), seed 7 (Plane 1 only); C = A with the
other run's Plane 2 report. A re-run of A matched A on every stage. B
changed every Plane 1 stage and no graph-only one; C changed only
`_attach_plane2_capacity`, the fingerprint and the render.
`compute_in_out_degree` saw two distinct graphs in 52 (A) and 73 (B)
calls: each result is graph-only, the call count is the trace's.

```text
class        today (12.47 s)          with UX-1106's prototype (8.57 s)
graph-only   4.00 s  +338 MB           1.41 s  +46 MB
Plane 1      7.06 s  ~+40 MB           6.11 s  ~+40 MB
Plane 2      0.87 s   +31 MB           0.56 s  +31 MB
load (mixed) 0.07 s   +10 MB           0.09 s  +10 MB
fixed/glue   0.47 s    37 MB base      0.39 s   37 MB base
```

The graph-only megabytes are the decoded downstream sets: 332 MB
(87 -> 419) in `compute_blast_radius`, 14.5M entries, then carried to
the end. Blast radius's own result is Plane 1 (a duration sum), so
reuse cannot skip it; only the decode is graph-only, and it need not
happen at all.

## Recommended next task: `UX-1106`

`compute_blast_radius` (`bga/diagnostics/analyzer.py:668`) decodes
every element's downstream bitset into a `frozenset` to sum durations
over it. Summing from the mask (256-entry per-byte tables over the
topological order) gives per-element identical sums. Measured, the
prototype patched into `bga analyze`, output byte-identical in text
and `--format json`:

```text
                         wall best of 3 (runs)          VmHWM
today                    13.94 s (14.75 13.94 14.03)    469 MB
blast radius off bits     8.16 s ( 8.64  8.72  8.16)    165 MB
weighted sum alone       4.10 s +329 MB -> 0.11 s +4 MB (5,002 el, load 1.4)
                         0.15 s  +16 MB -> 0.01 s +1 MB (1,202 el)
```

-5.8 s (41%) and -304 MB (65%): more than the 3.8 s the stage does,
because stages after it run with 330 MB fewer live objects
(`_attach_plane2_capacity` 0.87 -> 0.56 s, `structural` 0.39 -> 0.24 s).

## Reuse across equal graph fingerprints: not the next task

After `UX-1106` the graph-only class is 1.41 s of 8.57 s: the
`resource_blast` decode of 745 sets (0.47 s, +40 MB, `bga/sources.py:388`),
`build_element_graph` rebuilt 78 times (0.59 s) and
`compute_in_out_degree` 73 times (0.21 s) on two distinct graphs,
`build_edg` 0.25 s. The first is the same bitset fix; the next two
a per-graph memo inside one run. What remains for a cross-capture
cache is under 0.3 s, against a new persisted format and a currency
check. The trace-dependent 6.1 s (criticality Monte Carlo 1.3 s,
utilisation 1.2 s, attribution 1.1 s, ready queue 0.7 s, 65 critical
paths 0.6 s) is where the analysis spends its time after `UX-1106`.
