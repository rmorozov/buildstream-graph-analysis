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

---

## Planning notes, written before the round

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping: this is what round 7 was aimed at, recorded before it ran, and it belongs with the round rather than with the design argument.

## What the next audit round should probe

The last round audited **what the tool says**. The obvious next targets
are the two things it still cannot say, and the two places its own claims
have never been tested:

1. **Declared-vs-used dependencies.** The over-declared `codegen.bst`
   build-dep in `examples/06` was the one problem in that project that no
   `bga` signal found - it was found by knowing the project. Plane 2
   already traces every process inside a `--dir`-tagged sandbox, so
   "which of this element's declared build deps did its sandbox never
   read?" is answerable in principle and would close the last macro-level
   gap. `UX-27`'s sketch 3, deliberately deferred.
2. **A real CPU measurement.** Every efficiency number in the tool is
   built on slot *occupancy*, and the honest caveat attached to
   `occupancy_ratio`, to the `UX-36` bucket labels, and to `UX-37`'s
   scoring is the same one: occupancy is not CPU time, and inflates under
   contention. `getrusage` in Plane 2's hook destructor would give real
   per-process CPU time and collapse three separate caveats into one
   measurement.
3. **Scale.** Every finding in the last round came from projects of 8-13
   elements on one 4-core host. `docs/backlog/tasks/P1-16`/`P1-21` did real
   performance work on large graphs, but no audit has walked a
   *thousand*-element project end to end and asked whether the report is
   still readable, whether the critical-path rendering `UX-33` added is
   still the right shape at that size, or whether `bga sweep`'s knee is
   still meaningful. Nor has anything been captured on a many-core host,
   where `UX-28`'s re-based threshold makes materially different calls
   than the old one did.
4. **Remote execution.** `UX-09` noted it and nothing has revisited it:
   with a remote-execution sandbox the compute happens on a worker pool
   whose size and scheduling are invisible to the local client, so
   `builders` - the denominator of `occupancy_ratio` and the basis of
   `LB` - stops meaning what the tool assumes. Whether `bga` should
   detect that mode and refuse to certify, or model it, is an open
   product question, not a bug.
5. **The CI story end to end.** `UX-39` shipped the gate; nobody has run
   a real pipeline against it for a week and found out what it feels like
   to own. The two things most likely to be wrong are the derived 5.0pp
   default (one project, one runner) and the absence of multi-run
   baselining, which `UX-39` scoped out explicitly and which a single
   noisy runner will eventually force.

A good next round would pick (1) or (2) as its centre - both are real
capability, not polish - and use a project a full order of magnitude
larger than `examples/06` as the vehicle, which would incidentally
exercise (3).

## What blocks another real-sample round: nothing, and one habit

Asked directly before round 7 was planned, and worth recording because
the answer is not "get a capture" any more:

- **The capture is on demand.** `.github/workflows/real-project-capture.yml`
  warms, cuts and captures a real `freedesktop-sdk` build and publishes
  it to `captures/fdsdk-latest`, which is fetchable from here. The
  workflow-artifact route is not (the egress policy refuses
  `*.blob.core.windows.net`), which is why the branch exists.
- **One artifact is missing, and it is not a budget problem.** `UX-56`
  guessed that the raw trace being dropped above 40MB is why round 6 had
  no bwrap argv to settle the element-tag question with. It is not: the
  shim never records the argv at all (`UX-58`). That is a few lines, and
  it unblocks `UX-56`, which in turn unblocks declared-vs-used on real
  projects - which returned entirely empty on the real capture for the
  same reason.

The habit is the more useful finding. Round 6 spent **two CI iterations**
rediscovering that Ubuntu 24.04's
`kernel.apparmor_restrict_unprivileged_userns` stops bwrap bringing up
loopback - a failure this repository's own `.github/workflows/ci.yml`
already carried a named step for, with the root cause, the upstream
issue references and the exact `sysctl` fix in a comment. The capture
workflow was written from scratch beside a file that had solved its
hardest environmental problem months earlier.

That is the same shape as `UX-53` (the fixture with the right shape was
already checked in) and `UX-41`/`UX-52` (the rule was already written
down in the code that ignored it). Three rounds running, the scarce
resource has not been evidence. **Before building capture
infrastructure, read what the repository already runs.**

### Six deferrals that were never filed

A sweep of every `## Out of Scope` section across 121 task docs, checking
each against the backlog, found six items that were deferred with a
reason and then never became scope: `UX-58` (argv), `UX-59` (no noise
model for the pre-commit scenario, deferred verbatim by `UX-39` as
"probably necessary"), `UX-60` (FETCH in efficiency signals, deferred
identically by `UX-50` and `UX-53`), `UX-61` (`max_concurrency` of 5,268
on four cores), `UX-62` (per-span terminal status), and `UX-63` (measured
per-task memory, whose stated blocker shipped two rounds ago).

The process mostly works - `UX-12`'s per-element `max-jobs` deferral
became `UX-22` and `UX-31`, `UX-36`'s CPU-accounting deferral became
`UX-45`, and `UX-03`'s "wire the gate into this repo's own CI" is live in
`ci.yml`. What the six have in common is that each was deferred by a task
that *shipped successfully*: nothing failed afterwards to make anyone
look again. A deferral inside a green task is invisible.

## Ready for the seventh round

The backlog is **not** empty for the first time in three rounds, and
that is the honest state: round 6 filed `UX-55` (open) and left `UX-56`'s
real fix open behind a guard. Both need another real capture to settle,
not more thinking. The order I would pick:

0. **`UX-55` first, before anything else.** It is the one finding that
   blocks the product's stated purpose rather than a number's accuracy:
   on an incremental build — which is every CI build — a cached element
   reads as a lost measurement, the coverage hard gate fails, confidence
   drops, and the regression gate fails open. Everything else in this
   list is improvement; this one is the difference between the CI story
   working and not.
0b. **`UX-56`'s real fix**, which needs one thing round 6 could not
   keep: a real captured bwrap argv. The raw trace exceeded the tarball
   budget and was dropped, so the next capture should keep a *sample* of
   it (the first N invocations) rather than all or nothing.
0c. **The hook's path budget**, now measured at a **70% drop rate** on a
   real build. No longer a design question, just a number to raise — and
   worth raising before the next Plane 2 measurement, since a truncated
   read set is exactly what `UX-46` refuses to draw conclusions from.

Then, from the previous round's list:

1. ~~**The seam between the two planes.**~~ **Settled and built** as
   `UX-51`: `bga correlate` joins the planes on element UID. The product
   question - one merged capture, or two with an explicit join - was
   decided by measuring three things rather than arguing them: one
   capture already yields both artifacts (`UX-24`), the join key matched
   9 of 9 elements with zero mismatches on a real dual capture, and the
   horizons provably cannot be merged. So the contract between the planes
   is one string, and each stays independently replaceable. The caveats
   that made this look intractable were never in the way: `UX-27`'s
   `occupancy_ratio` and `UX-36`'s buckets still correctly say "slot
   occupancy, not CPU", because a join does not need them reconciled.
2. ~~**A real capture at scale.**~~ **Done** in round 6, and it paid for
   itself three times over. `.github/workflows/real-project-capture.yml`
   produces one on demand — 2,801.9s of real `freedesktop-sdk` build,
   127,630 traced processes — and publishes it to a branch, so a capture
   is now a fetchable object rather than a thing that has to be arranged.
   The open question it *answered*: the hook's fixed 8192-slot / 256 KiB
   per-process path budget, which round 5 called "chosen without
   evidence", drops **70% of observed opens** at this scale. The `dropped`
   counter existing is what made that a measurement rather than a guess.
   What remains is not "get a real capture" but **use it as a regression
   fixture**: the run directory is small (5.6 KB of trace over a
   126-element graph) and is the only artifact here containing a
   partially-cached build, several element kinds and runtime edges at
   once.
3. ~~**A project whose elements genuinely consume each other.**~~
   **Done** as `examples/07-declared-vs-used-dependencies`: `user.bst`
   and `unrelated.bst` declare identical dependencies and differ only in
   whether their source includes the header, and `UX-46` separates them
   correctly (1 of 5 staged files opened, versus 0 of 5). The
   true-negative evidence no longer rests on `toolchain.bst` alone.
4. **Remote execution** and **the CI story end to end** (items 4 and 5
   from the previous round) remain untouched and remain real.

### What four rounds of doing this taught, as method

None of these is about a particular defect, and each cost real time to
learn:

- **Byte-identical output is not proof of correctness.** `UX-42`'s
  rewrite matched all five real fixtures exactly, and an oracle test
  against a naive transcription of the original then found two genuine
  bugs. Where a change claims to preserve semantics, write the oracle.
- **A filed acceptance criterion is a hypothesis, not a specification.**
  Five of mine were wrong across the first two rounds - `UX-48`'s
  "majority of idle", two of `UX-43`'s predicted choke points, and two of
  `UX-46`'s expectations about which dependencies `examples/06` really
  uses. In every case the measurement was right and the criterion was
  written before the measurement existed. Each is corrected in place in
  its own doc, with the reasoning, rather than quietly dropped.
- **A quantity computed twice is a free test** (round 3). `UX-50` needed
  no large graph, no long build and no hypothesis about where to look -
  only the observation that two published fields claim to be the same
  number. The sweep is now standing, and runs 40/40 across five runs.
- **Fixture shape matters as much as fixture size** (round 3). The
  synthetic 1202-element fixture *structurally could not* exhibit
  `UX-50`, because it emits one task per element while a real capture has
  two. Round 2's lesson was that small projects hide defects; round 3's
  is the converse, and both fixtures are needed.
- **Before designing across a seam, measure what already crosses it**
  (round 4). The plane join looked like an architecture question and was
  one join away: the key already existed, the dual capture already
  existed, and both had been built for unrelated reasons.
- **A caveat you write about your own work is only useful if something
  later reads it** (round 4). `UX-46` recorded that its own true-negative
  evidence was thin; `examples/07` exists because that sentence was read
  two rounds later.

## Suggested order (historical - all of these shipped)

Grouped by what unblocks what, not by size. Kept as written, because the
sequencing reasoning is reusable; every item named below is now done.

**First — turn on what already exists.** `UX-33` (name the critical path
and the choke points), `UX-34` (drop structural noise from the
what-to-fix list), `UX-29` (auto-extract `native_max_jobs`), `UX-28` (fix
the oversubscription threshold), `UX-35` (make the hints capacity-aware).
Each is small, each is independent, and together they change what a local
user sees from "a number I cannot act on" to "a named element I can go
edit". `UX-30` (the sweep knee point) belongs here too — it is small and
it currently gives an actively wrong answer.

**Second — settle the metric.** `UX-27`. Everything in 2c depends on it,
and shipping a CI gate on top of the current `efficiency_score` would
ratify a metric that points the wrong way. `UX-36` (say that the
occupancy block is occupancy) is a prerequisite in practice, since the
occupancy ratio is the leading candidate and its meaning has to be
correct where users read it.

**Third — the CI gate.** `UX-40` first (a gate that fails open on most
real runs cannot be evaluated), then `UX-39`, then 2b's per-element diff.

**Fourth — the micro level.** `UX-32` (per-element achieved parallelism)
is the highest-value Plane 2 work and stands alone. `UX-31` (capture
`notparallel`, the real per-element control) is its cheap Plane 1
counterpart. `UX-37` (redundancy findings scored in wall-clock, filtered,
readable) and `UX-38` (the tracer's artifact-confusion trap) are polish on
the same tool.
