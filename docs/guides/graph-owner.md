# From a capture to a structural decision

> **R3's journey** — the graph owner, who owns the project's dependency
> shape ([the role model](../design/roles.md)).

The graph owner's question is not "which element is slow" but "what does
the graph make impossible, and which edge do I cut". The answer comes in
four steps: what the graph alone says, what the floors certify, what a
change rebuilds and saves, and what several variants cost together.

Every output below is a real run of the committed fixture
`tests/fixtures/macro_micro/run`: 11 elements, 46.1s, one `notparallel`
element at the head of a chain (`tests/fixtures/macro_micro/README.md`).
It needs no BuildStream; with your own capture, `@last` replaces the path
([`real-project.md`](real-project.md) takes the capture itself).

## 1. What the graph alone says

Two findings read the graph and no duration: how many dependency levels
it has, and how many elements the widest holds. That pair is the ceiling
on concurrency no builder count lifts (`graph-width`, `UX-478`).

```console
$ bga analyze tests/fixtures/macro_micro/run --format text
[... elided: the report above the width line ...]
  10 dependency levels; the widest holds 2 of 11 elements
[... elided: the report below the width line ...]
```

10 levels, widest 2: this build has no width to spend. Then the
diagnosis, which is the first thing `Key Findings` prints:

```console
$ bga analyze tests/fixtures/macro_micro/run --format text
[... elided: the title and run header ...]
Key Findings:
  This build is chain-bound, not scheduler-bound: the critical path is 100.0% of the time tasks were running, at or above the 90.0% chain-bound line, so the way to a shorter build is a shorter chain.
[... elided: the findings below the diagnosis, and the rest of the report ...]
```

Chain-bound means more builders buy nothing; the way to a shorter build
is a shorter chain. `bga graph` prints the chain and each element's
share of it; the head of the path:

```console
$ bga graph tests/fixtures/macro_micro/run
[... elided: the report header ...]
Critical Path Length: 10 elements
  Path (chain order, with each element's real measured duration):
    toolchain.bst                               0.00s (  0.0% of path) [structural: import, no build commands to speed up]
    core.bst                                   19.05s ( 44.1% of path)
[... elided: the rest of the path and the sections below it ...]
```

`core.bst` is 44.1% of a 10-element path and, in the same output, the
one element running its build system at 1 job while the rest run at 4
(`Parallelism-Pinned Elements`, `UX-31`).

## 2. What the floors certify

```console
$ bga floors tests/fixtures/macro_micro/run
[... elided: the report header ...]
Certified Floors:
  T∞ (observed critical path): 43.2 s
  LB (resource lower bound):   43.2 s
  Certified Headroom:          0 ms
[... elided: the replay makespan, scores and notes below ...]
```

The chain is the floor: 43.2 s of a 46.1 s build, and the scheduler has
0 ms to give back. Re-tuning the scheduler is the wrong lever; the graph
or the element is the right one (`bga sweep` shows the capacity curve
when the reader wants to confirm).

## 3. What a change rebuilds, and what it saves

Blast radius is the rebuild a change to one element forces, from the
graph alone with `--no-cost`, and with the measured work without it:

```console
$ bga blast core.bst tests/fixtures/macro_micro/run
Blast radius: core.bst
  Resolved as an element
[... elided: a blank line ...]
  Sourced directly by 1 element: core.bst
  Rebuilds 9 elements (8 that build, 1 that assemble) of 11 in this build
    8 cmake, 1 stack
  Cost: 43.2 s of build work, measured for 9 of 9
[... elided: a blank line ...]
  Work is the sum of those elements' own durations, not wall clock.
```

Touching `core.bst` rebuilds 9 of 11 elements. `bga whatif` prices the
other direction, an element made instant, and says when two fixes
interact:

```console
$ bga whatif tests/fixtures/macro_micro/run --element core.bst --element codegen.bst
What if these were fixed: core.bst, codegen.bst
  Makespan 43.200s -> 24.150s (saves 19.050s)
  Their individual savings add up to 12.050s, which is not what they are worth together (19.050s) - what one fix is worth depends on the others.
  A structural projection over this run's measured durations: "fixed" means the element becomes instant and nothing else about the build changes. An upper bound on what the selection can be worth, not a forecast - a re-capture is still the ground truth.
```

`core.bst` alone saves 12.05 s because `codegen.bst` (7.0 s, beside the
chain) becomes the bound; fixed together they save 19.05 s. The decision
is a pair, not an element. The projection is an upper bound: re-capture
to confirm.

`codegen.bst` is this project's second element, not a general one. On
your own run, take the first element from the `Key Findings` path list,
then name the off-path element that `Key Findings` lists under "off the
critical path" with the longest duration: once the first is instant, it
is what the chain becomes. Re-run `bga whatif @last --element A` against
`--element A --element B` and keep the pair only if the second number
exceeds the first.

## 4. Several variants: `bga junction-cost`

N builds of one project under different variants, priced against one
junctioned invocation. Two elements are one only when their cache keys
are identical. The pair below is not two variants: `with_timeline` is a
second capture of the same `macro_micro` build (same run id, same 11
cache keys, plus a Chrome trace and `sources.json`), so every key is
shared and the saving is the largest the command can print; real
variants share fewer. Each run line ends `(not declared)`: that is the
run's build type, which you declare when extracting
(`bga extract ... --build-type night --variant arch=aarch64`) so that
runs of different types are refused rather than joined (`UX-898`).
On your own runs, name the N store runs: `bga junction-cost @prev @last`
(or any two or more stamp prefixes or run directories).

```console
$ bga junction-cost tests/fixtures/macro_micro/run tests/fixtures/with_timeline/run
N separate invocations against one junctioned build: 2 runs
  054a6c451c526eae4c3d22bc7eac00aba96b45a1eb3bcb42d653aba83f6f1aec: (not declared), 11/11 keyed
[... elided: the second run, the same line ...]
  Shared: 11 elements shared by cache key; building each once saves 50.200s of work.
  Pipeline paid once instead of N times saves 1.441s [pipeline_once]
  Total saving 51.641s (upper bound)
  Floors: separate 43.200s, 43.200s; union 43.200s [unlimited_capacity]
  One invocation costs at least 44.641s, plus junction staging (not measured) [junction_staging]
[... elided: the four assumptions each figure cites, and the closing caveat ...]
```

The floor does not move (union 43.2 s); the saving is the repeated work.
It can exceed the 46.1 s build because it is a sum of element durations,
not wall clock (`Work is the sum of those elements' own durations`, as
`bga blast` prints): the 11 elements sum to 50.2 s (the 43.2 s chain plus
`codegen.bst`'s 7.0 s beside it), and one copy of that work is saved,
plus 1.441 s of pipeline.
Against a different project the same command prints `No element is
shared` and a saving of `0.000s`. Junction staging is not measured, so
the figure is a bound, not a forecast. The payload is
[`junction-cost/v1`](json-contracts.md#n-variant-builds-or-one-junctioned-invocation-ux-904).

## 5. Is the cache getting worse: `bga cache-trend`

A series, oldest first. Four runs give a verdict (three trailing plus the
one judged); with three or fewer it prints the rows and "No verdict".
Real use is over the store: `bga cache-trend @prev @last` prints two rows
and no verdict, and four or more stamp prefixes or run directories
(`bga snapshot --list` names them) give one. The fixture below is one run
named four times, so the band is flat:

```console
$ bga cache-trend tests/fixtures/a_build_that_pulls/run tests/fixtures/a_build_that_pulls/run tests/fixtures/a_build_that_pulls/run tests/fixtures/a_build_that_pulls/run
[... elided: the title banner ...]
run                             hit  built  cached     xfer  /artifact      rate   churn
a_build_that_pulls/run          75%      1       3     3.0s      1.00s   41.7M/s       -
[... elided: three rows identical but for the churn, 0+4r ...]
[... elided: the churn legend ...]
Every trended metric on the newest run sits inside the band its trailing window describes.
[... elided: a note on transfer seconds, and the closing banner ...]
```

Do not read the churn cell here: `0+4r` beside `built 1` is an artefact
of naming one run four times, and the pair of columns contradicts itself
(filed as a bookkeeping line, round 168). On a real series `+Nr` counts
elements that rebuilt with the same cache key twice: work the cache should
have served. A newest run outside its band raises
`cache-trend-regression`. Runs whose recorded `subject` (project and
targets) differ are refused with exit 6; runs recording none are not
(`bga/cache_trend.py`, `build_trend`).

## The decision

On this project: `core.bst` is the chain's head, 44.1% of the path, pinned
to one job, and the rebuild of 9 of 11 elements. The graph says shorten
the chain; the floors say the scheduler cannot; blast and what-if say
`core.bst` first, `codegen.bst` second.
