# Walkthrough: macro-then-micro optimization of a real project

> **A note on the commands below.** These sessions predate the `bga <alias>`
> entry points (`UX-77`), so they were originally run as
> `python3 -m tools.<module>`. <!-- docs-style: allow-direct-module -->
> The commands are shown in current form: an
> alias is a thin dispatcher onto the very same module, so the output
> quoted here is what these commands produce.


A second, deliberately harder companion to [`optimization-walkthrough.md`](optimization-walkthrough.md).
That one walks `examples/04-critical-path-optimization` (a `sleep N` proxy
graph) through two iterations and lands a 48.1% improvement, with `bga`
correctly guiding every step. **This one is the case where the tool does
not guide you**, and it exists so that failure is written down with real
numbers instead of remembered as an impression.

Everything below is a real, pasted run against
`examples/06-macro-micro-optimization` on a 4-core / 16GB Linux host,
BuildStream 2.7.0, `bst --builders 4 --max-jobs 4 build all.bst`.

## The project, and what is wrong with it

`examples/06-macro-micro-optimization` builds eleven real elements
(`toolchain` import + nine real CMake/C++ modules + an `all` stack) and is
mis-optimized in three independent, one-line ways - see its own
`project.conf` for the full text:

1. **Macro / graph shape** — `lib-a..lib-f` are declared as a six-deep
   dependency *chain* rather than a six-wide fan-out off `core.bst`.
2. **Macro / over-declared dependency** — every `lib-*.bst` build-depends
   on `codegen.bst`, and nothing consumes it. (This walkthrough
   originally said "only `lib-f.bst` consumes it", repeating the example
   project's own comment. `UX-46` later *measured* it: `lib-f` opens none
   of `codegen.bst`'s staged files either, and in fact every cross-element
   build dependency in this project is decorative. The comment was wrong
   and has been corrected in the element files too.)
3. **Micro / inside one element** — `core.bst` carries
   `variables: notparallel: True`, so its eight ~1s translation units
   compile strictly one at a time.

`optimized/` fixes all three and changes nothing else — every source file
is generated into both variants by the same script and is byte-identical.

## Iteration 0 — what `bga analyze` says about the broken build

```
$ bga analyze -d /tmp/run-06-baseline
Total Duration: 39.6s

Key Findings:
  Confidence: 0.92 (high)
  Biggest Opportunity: 7.7% of wall-clock time is UNTRACKED HEAD (3.05s)
  Elements Most Worth Optimizing First (by blast radius):
    1. toolchain.bst (10 downstream elements) [structural: import, may not reflect real compute work]
    2. codegen.bst (8 downstream elements)
    3. core.bst (8 downstream elements)
  Efficiency Score: 1.00 (very efficient - remaining gains are mostly in reducing Critical Path's own work, not scheduling)

Certified Floors:
  T∞ (observed critical path): 36.25s
  LB (resource lower bound):   36.25s
  Certified Headroom:          0.00s

Attribution Breakdown:
  Execution On Chain Us        36.25s ( 91.6%)
  Dependency Wait Us            0.00s (  0.0%)
  Resource Wait Us              0.00s (  0.0%)
  ...
Critical Path Length: 10 elements

CPU Utilisation:
  Effective CPUs: 4.0
  Useful                  40.25s
  Idle No Tasks          118.03s

Structural Analysis:
  Elements: 11, Edges: 34, Max Depth: 9
  Bottlenecks Identified: 5
  Top Improvement Opportunities (best-case speedup 1.05x if all 2.00s of improvable time were eliminated):
    - toolchain.bst: sensitivity 1.00 (100.0% impact)
    - all.bst: sensitivity 1.00 (100.0% impact)
```

Read that as a user who does not already know the answer:

- **`Efficiency Score: 1.00 (very efficient)`** and **`Certified Headroom: 0.00s`**
  on a build that is about to get 30% faster from three one-line edits.
- **`Biggest Opportunity`** is BuildStream's own 3s startup — 7.7% of the
  run — while three of four cores sit idle for the other 92%.
- **`Top Improvement Opportunities`** ranks a `stack` element and an
  `import` element first, at sensitivity 1.00.
- **`Critical Path Length: 10 elements`** and then no path, because
  `bga/report/text.py` only prints the path when it is `<= 5` elements
  long. The ten-element artificial chain — the entire problem — is
  computed, is in the JSON, and is withheld from the text report.
- **`Bottlenecks Identified: 5`** and then no names. The JSON has
  `choke_points: ["lib-a.bst", ..., "lib-e.bst"]`, which is exactly the
  chain.
- **`Useful 40.25s / Idle No Tasks 118.03s`** under a heading that says
  *CPU Utilisation* is the one number that does point at the problem, and
  nothing in the report connects it to the score above it.

The only two facts a user can act on here are printed as raw JSON keys or
not printed at all. Filed as
[`UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md),
[`UX-33`](../backlog/scenarios/UX-0033-text-report-withholds-critical-path-and-choke-point-names.md),
[`UX-34`](../backlog/scenarios/UX-0034-structural-elements-dominate-improvement-opportunities.md),
[`UX-36`](../backlog/scenarios/UX-0036-cpu-utilisation-block-reports-occupancy-not-cpu.md).

## Iteration 1 — fix the graph and the one-line micro problem anyway

```
$ bga compare /tmp/run-06-baseline /tmp/run-06-optimized
Verdict: IMPROVED  (total duration -12.07s, -30.5%, 39.57s -> 27.50s)

Certified Floors:
  Total Duration           39.57s ->     27.50s   (-12.07s)
  T∞ (observed)            36.25s ->     20.35s   (-15.90s)
  LB                       36.25s ->     20.35s   (-15.90s)
  Certified Headroom        0.00s ->      4.05s   (+4.05s)
  Efficiency Score           1.00 ->       0.83   (-0.17)
```

The verdict is right, and it is right for the only reason available to
it: wall-clock got smaller. Both of the tool's *own* efficiency metrics
moved the wrong way — the score fell 1.00 → 0.83 and headroom rose
0.00s → 4.05s — because both certify against the graph the run actually
had. A graph serialized into a chain has a critical path equal to its own
total work, so `LB == T∞ == T_C` and the scheduler is, tautologically,
perfect. This is the tool's central design gap, not a rendering bug:
`efficiency_score` answers *"did the scheduler pack this graph well"*,
never *"is this graph worth packing"*. See
[`UX-27`](../backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md).

## Iteration 2 — going below the element, with Plane 2

Nothing in Plane 1 can see problem 3 at all: BuildStream's log records one
START/SUCCESS pair for `core.bst` either way. Plane 2 can, and the raw
capture says so in one line:

```
$ bga capture run --raw-log /tmp/06.rawlog \
    examples/06-macro-micro-optimization /tmp/06-native.json \
    -- bst --builders 4 --max-jobs 4 build all.bst
Processes traced: 822 (663 matched, 159 no observed exit)
Max observed concurrency: 20
Wall span: 39.060s
By element:
  core.bst    113
  codegen.bst  93
  lib-a.bst    88
  ...
```

`core.bst` did more work than anything else. That is all the report says.
The trace itself, however, contains the literal answer:

```
$ python3 - <<'EOF'   # ad-hoc, not something bga can do today
core.bst    -> make -j1
codegen.bst -> make -j4
lib-a.bst   -> make -j4   (and so on for every other element)
EOF
```

and the same conclusion is derivable from process overlap, per element:

```
              baseline                                  optimized/
  core.bst    peak=1  span=13.05s  compile_cpu=11.05s   peak=4  span= 6.03s
  lib-a.bst   peak=3  span= 1.88s                       peak=3  span= 6.67s
  codegen.bst peak=4  span= 2.55s                       peak=4  span= 4.19s
```

(`peak` = maximum concurrently-live `cc1plus` processes owned by that
element.) One element achieving a peak of 1 while its siblings reach 3-4
*is* the micro-level finding, it needs no new instrumentation, and the
tracer neither computes nor reports it — its only concurrency number is a
single global `Max observed concurrency: 20`, which counts idle `make`
and `sh` wrappers and so is inflated well past the four real cores. Filed
as [`UX-32`](../backlog/scenarios/UX-0032-plane-2-has-no-per-element-achieved-parallelism.md).

Two adjacent gaps surfaced in the same session. `bga` does have a
per-element parallelism check (`UX-22`'s `serialization_point_risks`), and
on this run it reports `[]`, because it reads `public: bst: max-jobs`,
which BuildStream 2.7.0 never consults when computing `-jN` — the real
mechanism, `variables: notparallel: True`, is the one this project
actually used and the one that produced `make -j1`
([`UX-31`](../backlog/scenarios/UX-0031-notparallel-is-the-real-per-element-parallelism-control.md)).
And feeding the *raw log* is mandatory: `bst_native_build_tracer report`
takes a raw trace log, so handing it the JSON report that `run` just
wrote prints `Processes traced: 0` and exits 0
([`UX-38`](../backlog/scenarios/UX-0038-tracer-report-accepts-the-wrong-artifact-silently.md)).

## Iteration 3 — the capacity question the tool declines to answer

After iterations 1-2 the same host is running `--builders 4 --max-jobs 4`
= up to 16 concurrent compilers on 4 cores. Plane 2 measures the cost
directly: `core.bst`'s eight translation units cost 11.05s of process
lifetime when they had the machine to themselves and 20.00s once five
siblings compiled alongside them — same source, same compiler, +81%.

`bga` has a check for exactly this (`UX-12`/`UX-16`) and it reported
`violations: []`, because `native_max_jobs` was `null` in the extracted
run context: `bst_extract_run` only recorded it if the operator passed
`--native-max-jobs` by hand, even though line 1 of the wrapped log it
just parsed reads
`Executing command: bst --builders 4 --max-jobs 4 build all.bst`
([`UX-29`](../backlog/scenarios/UX-0029-native-max-jobs-is-never-auto-extracted.md),
since fixed — the value is now recovered automatically).

Supplying it by hand and re-extracting also produced no violation, and
chasing *that* down turned out to be the more interesting result. It is
**not** evidence that 4×4 on 4 cores is harmful — `UX-09`'s own real
6-configuration table measured exactly that configuration as the
*fastest* of the six on this same host, and the run above is 30.5%
faster than the serialized one despite the higher per-element cost. The
+81% is what beneficial parallelism costs per element, not a defect.

The real defect the chase surfaced is in the threshold's *shape* rather
than its silence here: the bar was BuildStream's own unconfigured default
(`4 × min(cores, 8)`), which stops growing at 8 cores while the host does
not — so the ratio at which the check fired was 4× the cores on this
machine and 0.5× on a 64-core one, and above 8 cores it flagged
configurations sitting *below* one process per core
([`UX-28`](../backlog/scenarios/UX-0028-oversubscription-threshold-is-self-referential.md),
since fixed and re-based onto the real core count, plus a sharper
`builders > cores` dispatch check). Worth recording as a process note:
the first framing of this finding was wrong, and it only came apart when
the fix was checked against `UX-09`'s existing measurements instead of
against the intuition that produced it.

Meanwhile the report's own next-step hint for this run says:

```
  Biggest Opportunity: 32.7% of wall-clock time is RESOURCE WAIT (9.00s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N
       with a higher N, or `bga sweep` to find the real knee point
```

Raising `--builders` on a host already running 4 compilers per core is the
opposite of the fix ([`UX-35`](../backlog/scenarios/UX-0035-attribution-hints-are-capacity-blind.md)).
Taking the hint's other suggestion does not help either: `bga sweep` stops
at the first capacity whose marginal gain is under 5%, so on
`examples/05-cmake-cpp-toolchain` it reports `Knee point: capacity 2`
while its own printed table shows capacity 4 is a further 35.1% faster
([`UX-30`](../backlog/scenarios/UX-0030-sweep-knee-point-stops-at-the-first-flat-step.md)).

For completeness, the capacity change was measured rather than assumed:
`--builders 2 --max-jobs 2` on the optimized project took 28.69s against
27.50s at 4×4. On this project, at this size, sandbox staging dominates
and the contention fix is a wash — which is a perfectly good answer, and
one the user had to get by running the experiment themselves.

## What the cycle actually cost

| Iteration | Wall-clock | Found by |
|---|---|---|
| 0 baseline | 39.57s | — |
| 1 macro + micro fixes | 27.50s (−30.5%) | reading `choke_points` out of the JSON, and knowing the project |
| 2 `core.bst` parallelism | (included above) | an ad-hoc script over Plane 2's JSON |
| 3 capacity retune | 28.69s (rejected) | running the experiment by hand |

Three real problems, three real fixes, 30.5% faster. `bga`'s headline
efficiency number moved from 1.00 to 0.83 across that, and every finding
that led to a fix came out of a JSON field or an ad-hoc script rather than
out of the report. The backlog items above are what would close that gap;
[`docs/design/directions.md`](../design/directions.md) is the argument for
which of them are load-bearing and which are polish.

## What has closed since this was written

This walkthrough is kept as it was recorded - it is a transcript, and
rewriting it would destroy its value as evidence of what the tool felt
like at the time. Four of the gaps it complains about have since been
fixed, and reading it today the differences are:

- **"reading `choke_points` out of the JSON, and knowing the project"** —
  `UX-43` redefined a choke point as an element nothing can overlap with,
  so the baseline now names the whole `lib-a`..`lib-f` chain in the text
  report and `optimized/` names none of it. The old degree heuristic
  reported the same count for both.
- **"an ad-hoc script over Plane 2's JSON"** for `core.bst`'s
  parallelism — `UX-45` added real per-process CPU time, so the tracer
  itself now prints `core.bst  0.87 cores busy` beside its siblings'
  ~1.7. The question "is this element compute-bound or waiting?" no
  longer needs a script.
- **The over-declared dependency, which nothing found** — `UX-46` makes
  it a reported finding, and in doing so proved the project's own
  description of it wrong (see item 2 above).
- **`sensitivity.top_opportunities` pointing at the wrong elements** —
  `UX-44` found that "slack" was the placeholder `duration × 0.5`, which
  made the ranking a strictly *inverted* duration sort. The report now
  names `core.bst` first, at up to 10.00s off the finish, which
  independently reproduces the ~10s this walkthrough measured by hand.

And the seam itself is closed: `UX-51` added `bga correlate`, which joins
the two planes on element UID. Run against a real dual capture of this
same project it produces, in one line, the finding this walkthrough needed
three artifacts and an ad-hoc script to reach:

```
  core.bst:
    - holds 25% of the critical path but runs at only 0.85 cores busy - it is waiting,
      not computing, and its native build asked for -j1: remove `notparallel` / raise
      its job count before touching its sources
```

What is still true is that this remains two *captures* joined explicitly,
not one merged pipeline - deliberately, since the two horizons cannot be
reconciled (see `docs/design/architecture.md`) and one `bst build` already emits
both artifacts.

## Verification Log

Written 2026-08-16 from a real, live session: BuildStream 2.7.0 +
`buildstream-plugins` in a venv, real `bwrap` sandboxes, real `gcc 13` /
`cmake 3.28` staged by `examples/stage_cpp_toolchain.sh`, on a 4-core
host. Every command output quoted above was pasted from that session, not
reconstructed. The per-element `make -jN` values and `cc1plus` peaks were
computed from the tracer's own emitted JSON (`processes[]`), which is why
they are quoted as ad-hoc-script output rather than as tool output.
