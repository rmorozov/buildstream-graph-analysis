# Audit round 7: the second real `freedesktop-sdk` capture

Run [`32044281643`](https://github.com/rmorozov/buildstream-graph-analysis/actions/runs/32044281643),
`bga` at `7f447a9`, `freedesktop-sdk` at `953683fb`, BuildStream 2.7.0,
4-core Azure runner, 16 GB, `--builders 4 --max-jobs 4`, target
`components/libxml2.bst`. Published to `captures/fdsdk-latest` as
`df20544`.

**The traced build succeeded outright** (`traced_build_exit=0`). Round 6's
traced build failed and needed a plain retry, so this is the first real
capture where both planes describe the same successful run.

## Scoreboard against round 6

| | round 6 | round 7 |
|---|---|---|
| traced build | **failed**, needed a plain retry | **exit 0** |
| paths recorded | 65,101 | **83,925** (+29%) |
| paths **dropped** | **149,053** (70%) | **0** |
| `max_concurrency` (4-core runner) | **5,268** | **60** |
| processes with a real element name | 740 / 127,630 (0.6%) | **19,024 / 127,629 (14.9%)** |
| `declared_vs_used` | **entirely empty** | 9 unused candidates, 4 used |
| peak RSS per element | not captured | **measured**, with coverage |
| `critical_path_coverage` | 0.818 | **1.00** |
| confidence | 0.82 | **1.00** |
| violations | 1 (hard gate) | **0** |

## What landed cleanly

**`UX-57` — dropped paths are gone.** Zero, against 149,053. The flush
mechanism did real work rather than sitting idle: **90,775 windows** were
written across the build, and recorded paths went *up* 29% because
elements that previously hit the ceiling now record their whole read set.
`cmake-stage1.bst` alone recorded 29,656 paths across 4,789 windows —
under the old fixed budget it would have been truncated at roughly 6,000
and then excluded from analysis entirely.

**`UX-55` — the incremental scenario is judged correctly.** `queue_summary`
is captured (`build: processed 25, skipped 65`), `run_mode` reads
`incremental`, the two cached critical-path elements
(`bootstrap/symlinks.bst`, `components/perl.bst`) are named as cached
rather than as coverage gaps, no hard gate fails, and the report leads
with the scenario before the numbers.

**`UX-61` — concurrency is plausible.** 5,268 → 60. Still above the core
count, which is expected and now stated: it counts processes *alive*, most
of them blocked wrappers, not cores in use.

**`UX-63` — peak memory is real, and immediately actionable.**

```
components/_private/cmake-stage1.bst   1902.0 MB  measured 10057/11974
components/doxygen.bst                 1491.6 MB  measured  913/1139
```

Four concurrent builds of `cmake-stage1`'s shape is ~7.6 GB against this
runner's 16 GB. That is exactly the input `UX-21`'s memory guard has been
asking operators to estimate, now measured — and the first number this
project has produced that would change a `--builders` decision on memory
grounds rather than CPU.

**`UX-46` — declared-vs-used works on a real project for the first time.**
9 unused candidates and 4 used, where round 6 returned an entirely empty
block. It was gated on element names being real, which is `UX-56`.

## `UX-58` settled: the argv contains no element identity

This is the decisive artefact, from a project that really does override
`build-root`, and the answer is conclusive.

```
[ 11] --dir     buildstream-build/flit_core
[ 13] --chdir   buildstream-build/flit_core
[370] PWD      /buildstream-build/flit_core
```

Across all 25 sandboxes the `--dir` last segment is:

| value | count | is it an element? |
|---|---|---|
| `buildstream-build` | 21 | no |
| `flit_core` | 1 | **no** — no such element exists |
| `expat` | 1 | no — coincidentally resembles `components/expat.bst` |
| *(absent)* | 2 | no |

The two non-collapsed values are **source subdirectory names**, not
element names. `flit_core` matches no declared element at all; `expat`
merely looks like one. That is worth recording as a hazard in itself: a
tag that is sometimes coincidentally right is more dangerous than one
that is uniformly wrong, because it survives a spot check.

Combined with round 6's finding that the shim's ancestry
(`buildbox-run` → the `bst` main process) carries nothing either, the
lookup approach is closed off with real evidence rather than argument.

## `UX-56`: the mechanism works, and does not yet reach far enough

The correlation ran and did real work — **19,024 processes relabelled**
across 6 correctly-identified elements — but resolved only 6 of 25
sandboxes:

```
certain 6, deduced 0, ambiguous 18, conflicting 1, unmatched 0
```

`unmatched: 0` is the important half of that: every sandbox landed inside
at least one BUILD span, so the clock alignment that failed on the
1.4-second `examples/07` reproduction works fine at real scale, exactly as
predicted. The method's precondition holds.

What does not work is the **discrimination**. With `--builders 4`, four
BUILD spans overlap continuously, so most sandboxes are contained in
several and `deduced: 0` says the elimination never cascaded — there were
too few single-candidate cases to start a chain.

`bga correlate` correctly refuses the join rather than reporting
per-element figures that are not per-element.

### The fix is identified, and it is the sandbox's *end*

The correlation currently matches on the invocation's **start time only**,
because the shim `execv`s and cannot record an end. But the end is already
in the capture: every process carries `inv=`, so a sandbox's window is
`[min start_ts, max end_ts]` over its own processes. With the shim's
wall-clock start as the anchor for the hook's `CLOCK_MONOTONIC` stamps,
each sandbox gets a real *interval* instead of an instant.

Requiring the whole interval inside a BUILD span should collapse the
ambiguity sharply, because the 25 elements' build durations differ by
orders of magnitude — `cmake-stage1` ran for many minutes while several
others took seconds. Filed as `UX-64`.

The single `conflicting` sandbox is filed with it: two sandboxes were
forced onto one element, which means the one-sandbox-per-element premise
does not hold universally on a real project and the model needs to say so.

## Round 7's process note

Round 6's lesson was *read what the repository already runs*. This round's
near-miss was the same shape and was caught in time: the capture workflow
did not pass `--invocation-log`, so `UX-56`'s correlation would have
silently not run and round 7 would have returned another fully-collapsed
capture. Checking what the workflow actually invokes — before spending an
hour of runner time — is now the pre-flight step, not an afterthought.

The `push`-on-`claude/**` trigger plus `cancel-in-progress` also means
every push touching the tracer starts a capture and cancels the previous
one. One run was 30 minutes in, on the *old* workflow file, when the
dispatch cancelled it; that was the right outcome, but it is worth knowing
the branch spends runner time on every tracer commit.
