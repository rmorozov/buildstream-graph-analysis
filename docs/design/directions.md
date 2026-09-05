# Design directions: `bga` as a local optimization helper, and `bga` as a CI gate

Written 2026-08-16 after a full hands-on audit and a real macro-then-micro
optimization walkthrough
([`case-study-06-macro-micro.md`](../audits/case-study-06-macro-micro.md)). This
is an argument about direction, not a task list — the tasks it argues for
are filed individually as `UX-27`..`UX-40` in
[`scenarios/`](../backlog/scenarios/README.md). Read
[`architecture.md`](architecture.md) first for what the tool is today.

## The one finding everything else follows from

`bga` measures **how well the scheduler packed the graph it was given**.
It does not measure, and today cannot measure, **whether that graph was
worth packing**.

Every certified floor is derived from the run's own observed graph and
observed durations. A build whose six independent libraries have been
accidentally chained one behind another has a critical path equal to its
own total work, so `LB == T∞ == T_C` exactly, headroom is zero, and
`efficiency_score` is 1.00. Real, measured, on a project built for this
audit:

| | wall-clock | `efficiency_score` | `certified_headroom` | dispatch occupancy |
|---|---|---|---|---|
| deliberately mis-optimized | 39.57s | **1.00 "very efficient"** | **0.00s** | 25.4% |
| three one-line fixes | 27.50s (−30.5%) | **0.83** | **4.05s** | 55.9% |

The tool's headline efficiency number is anti-correlated with real
efficiency across the entire class of problem that build-graph
optimization exists to solve. That is not a bug in the arithmetic — the
arithmetic is right, and `docs/spec/specification.md` Parts 14–18 mandate it.
It is a missing layer: nothing sits above the floors asking whether the
graph is the right graph.

This single fact is why the local helper mis-directs users and why the CI
gate cannot be built on the metrics that exist. Both sections below
reduce to it.

## Direction 1: `bga` as a local optimization helper

**Serves:** R1 above all — one person, one machine, the edit-build-compare loop — and R2, whose element cost the loop surfaces ([roles](roles.md)).

**Status:** landed — the `UX-27`..`UX-40` round below closed it, and the report block this section illustrates is printed (see the note under it).

**Who this is.** One person, one machine, an iterative loop: build,
analyze, change something, rebuild, compare. `README.md` already sells
this loop and `UX-05`'s walkthrough shows it working on a `sleep N` proxy
project. It stops working on a real one.

### What already works, and should not be disturbed

The analysis engine is genuinely good and the audit found no correctness
defects in it. Attribution sums to the horizon; the determinism harness
is real; the invariants are enforced; `bga compare`'s verdict was right on
every pair tested; blast-radius ranking is the right primitive; the
two-plane split is the right architecture. `choke_points` correctly
identified the artificial chain. `critical_path` was correct every time.
The problem is almost never that `bga` does not know — it is that it does
not say.

### The shape of the fix: stop making the user read JSON

Of the three real problems in the walkthrough project, **zero** were found
by reading the text report:

- The six-deep chain was found by reading `structural.choke_points` out of
  `-f json`. The text report printed `Bottlenecks Identified: 5` and no
  names, and printed `Critical Path Length: 10 elements` and no path,
  because `bga/report/text.py` suppresses the path above five elements —
  i.e. exactly when a human cannot hold it in their head (`UX-33`).
- The over-declared `codegen.bst` dependency was found by knowing the
  project.
- The `notparallel: True` on the heaviest element was found by an ad-hoc
  script over Plane 2's own JSON (`UX-32`).

Meanwhile the report's own ranked "what to fix first" list led with a
`stack` element and a zero-duration `import` element at sensitivity 1.00
(`UX-34`), and its next-step hint recommended raising `--builders` on a
host already running four compilers per core (`UX-35`).

So the first direction is unglamorous and high-value: **every signal the
tool already computes should reach the text report, named, ranked by
whether a human can act on it, and filtered of things that cannot be
acted on.** `UX-25` established the pattern (name the elements, tag the
structural ones); `UX-33`/`UX-34`/`UX-35` apply it to the three places it
was not applied.

> **Done.** All three shipped. The critical path is printed in full with
> per-link durations, choke points are named, structural elements are
> filtered out of the what-to-fix ranking, and the `RESOURCE WAIT` hint
> is conditioned on a real capacity verdict. The paragraphs above
> describe the state that motivated them, not the current output.

### The second direction: make the micro level a first-class answer

Plane 2 is the tool's most distinctive asset and its report is a census —
counts by binary, counts by element, one global concurrency number. The
question it was built to answer ("is this element's native build system
achieving the parallelism it should?") is answerable from data it already
writes to disk, per element, and is not answered:

```text
              baseline                      optimized/
  core.bst    peak=1  span=13.05s           peak=4  span=6.03s
  lib-a.bst   peak=3  span= 1.88s           peak=3  span=6.67s
```

One element at peak 1 while its siblings reach 3–4 is the whole finding.
Achieved-vs-requested parallelism per element (`UX-32`) is the single
highest-value addition to Plane 2, and it needs no new instrumentation —
the element's own `make -j1` appears verbatim in the captured `cmd`
strings.

> **Done, with one correction.** Achieved-vs-requested turned out to be
> the wrong headline: a `-j1`-pinned element achieves 100% (200% in the
> real trace, since a gcc driver pipelines `cc1plus` into `as`) of what
> it asked for, and being pinned is the problem. The shipped report emits
> `pinned_to_one_job` and `underachieved_requested_jobs` instead. The
> same finding is now *also* available from Plane 1 alone, from a plain
> `bst show` (`UX-31`).

### The third direction: close the macro→micro loop

Today the two planes are separate tools with separate invocations,
separate artifacts, and — apart from `UX-24`'s combined Chrome Trace — no
analytical connection. The optimization cycle a user actually runs is a
loop between them:

> Plane 1 ranks elements by blast radius and critical-path membership →
> the user picks the top one → Plane 2 explains where *that element's*
> time went → the fix is either a graph change (back to Plane 1) or a
> native-build change (stay in Plane 2).

The missing piece is small and mechanical: Plane 1 knows which elements
are worth looking inside; Plane 2 knows what happened inside them.
Nothing carries a recommendation across. A concrete first step is a single
line in Plane 1's output — *"`core.bst` is on the critical path and is
41% of it; run the Plane 2 tracer against it"* — and a Plane 2 mode that
accepts Plane 1's element ranking and reports the top N elements' internal
parallelism first. This is deliberately not a merge of the two horizons,
which `architecture.md` argues against for good reasons.

> **Done, and it landed closer to this section's own sketch than
> expected.** `UX-51`'s `bga correlate` joins the planes on element UID,
> and the sketch above was right that the missing piece was mechanical:
> the join key already existed on both sides and matched 9 of 9 elements
> with zero mismatches. What the sketch under-sold is the *negative*
> result - an element reported as already compute-bound tells a reader to
> stop looking inside it, which is as useful as being sent there. The
> real output on this project's own `core.bst` is one line:
> *"holds 25% of the critical path but runs at only 0.85 cores busy - it
> is waiting, not computing, and its native build asked for -j1"*.

### The fourth direction: the capacity axis should stop being decorative

The walkthrough's third iteration is the honest low point, and also the
place where the audit's own first answer turned out to be wrong. On a
4-core host running `--builders 4 --max-jobs 4`, `bga` reported
`violations: []` — because `native_max_jobs` was `null`, recorded only
when the operator passed a flag, even though line 1 of the log the
extractor just parsed reads `Executing command: bst --builders 4
--max-jobs 4 build all.bst` (`UX-29`).

Supplied by hand, the check still did not fire. The audit initially read
that as a second defect, citing the +81% per-element contention Plane 2
measured. That reading does not hold: `UX-09`'s own real timing table
measured 4×4 on this exact host as the *fastest* of six configurations,
and the run in question was 30.5% faster overall. Higher per-element cost
under concurrency is what beneficial parallelism costs, not evidence of
harm.

The defect that survived re-verification is different and sharper: the
bar was BuildStream's own unconfigured default (`4 × min(cores, 8)`),
which stops growing at 8 cores while the host does not. The ratio at
which the check fired was therefore 4× the cores on a 4-core host and
0.5× on a 64-core one, and above 8 cores it flagged configurations
sitting *below* one process per core — reported as oversubscribed by one
branch while meeting the next branch's own definition of idle capacity
(`UX-28`).

Five shipped features (`UX-12`/`UX-15`/`UX-16`/`UX-17`/`UX-21`) hang off
that field and that threshold. Both are now fixed, which turns a dormant
subsystem on — and the episode is the clearest argument in this document
for the general point: a config-level check reasoning about *potential*
demand cannot settle these questions, because potential demand overstates
real demand whenever an element has less parallel work than it has job
slots. `UX-32`'s measured per-element concurrency is what would.

### What a good local session should look like

Concretely, the report a user should get on the walkthrough's baseline:

```text
Biggest structural problem: 6 elements are serialized that need not be
  lib-a.bst → lib-b.bst → lib-c.bst → lib-d.bst → lib-e.bst → lib-f.bst
  Each depends only on core.bst. Estimated wall-clock if fanned out: 21s (from 39.6s).

Dispatch occupancy: 25.4% of available slot-time used (40.25s of 158.3s).

Elements worth looking inside (Plane 2):
  core.bst - 41% of the critical path, pinned to -j1 by `notparallel`.

Capacity: builders 4 x max-jobs 4 = 16 potential processes on 4 cores.
```

Every number in that block is either already computed today or is
derivable from data already captured. None of it is currently printed.

**It is now — measured round 83, 2026-09-03.** That last sentence is
the round-1 reading and is kept as the argument's starting point; every
line of the block above renders from `bga/report/text.py` today. The
serialization group with its combined saving and the `Serialized (…)`
pairs, `Dispatch Occupancy:`, `Critical Path Length:`, the
`Parallelism-Pinned Elements (UX-31 …)` block that is the "worth
looking inside" shortlist, and the `builders=N x native max-jobs=M = K
potential concurrent processes` sentence are all printed strings in
that module.

## Direction 2: `bga` as a CI tool

**Serves:** R4, whose gate this is, and R6 indirectly — every false positive a loose band waves through is a contributor's re-run ([roles](roles.md)).

**Status:** landed — same round; the gate, the CI comment and the noise band all ship (`UX-39`, `UX-40`, `UX-46`).

Three jobs, in increasing order of how hard they are and how badly the
current design serves them.

### 2a. Gather analytics — nearly done, needs plumbing not design

`bga analyze -f json` is complete, stable, deterministic (`I11`, with a
real N-run harness), and carries provenance and run identity. The CI job
in `.github/workflows/ci.yml` already captures real runs, real Chrome
traces, and full run directories as artifacts, and it already treats a
`bga` failure as data rather than as a build break. This is the part of
the tool that is ready.

What is missing is the boring part: a documented, stable "one row per
run" projection for a time series (run identity, targets, wall-clock,
occupancy ratio, per-category attribution, per-element durations,
confidence and its sub-scores), so a pipeline can append to a store
without re-deriving a schema from the full report. Worth pinning
explicitly as a compatibility surface, because everything in 2b and 2c
consumes it.

One real caveat to document loudly: `run_identity` correctly refuses to
compare unlike things, and `bga compare` warns when two runs do not look
like the same project. In CI, where the project legitimately changes every
commit, "not the same project" is the normal case, and the warning must
not become noise that trains people to ignore it.

### 2b. Highlight problems — blocked on the metric, not on the plumbing

Everything in Direction 1 applies verbatim: a CI comment that says
`Bottlenecks Identified: 5` without naming them is worse than useless,
because nobody will run the JSON query by hand.

The additional CI-specific need is **attribution of a problem to a
change**. "This build is 25% efficient" is a fact about a repository, not
about a pull request. "This pull request added `lib-g.bst`, which is
serialized behind `lib-f.bst` for no declared reason, and cost 4.1s of
critical path" is reviewable. That requires per-element diffing between
two runs — which elements are new, which changed duration, which changed
position relative to the critical path — and `bga compare` today reports
only aggregates (floors, categories, a verdict). This is the single
highest-value CI-specific addition, and it is a natural extension of
`UX-01`'s existing machinery rather than new analysis.

### 2c. Stop regressions — the part that needs a new metric

The requirement, in the build owner's own words: *adding new elements and
making the build slower is fine; adding them in an unoptimized way is
not.* There should be a level of inefficiency the owner considers normal,
and a large regression past it should stop the pipeline.

The current gate cannot express that, and was never meant to.
`--fail-on-regression` compares `total_duration_us` at a 1% threshold.
Measured against real runs (`UX-39`):

- **It fires on noise.** A pure capacity change on an unmodified source
  tree — `+1.19s` on a 28s build, `+4.3%` — exits 4.
- **It cannot allow legitimate growth.** Three new elements make the build
  slower; the gate fails; the only remedy is raising the threshold, which
  blinds it to everything else.
- **The tool's own efficiency numbers point the wrong way**, so gating on
  them instead would be worse than gating on duration: serializing the
  build *raises* `efficiency_score` to 1.00 and *lowers* headroom to zero.

And in practice the gate is frequently not running at all: it fails open
below 0.8 confidence, and real captures land at ~0.69 because BuildStream's
own startup is counted against `attribution_score`. The smaller the
project, the larger startup's share, the more likely the gate is silently
disabled — with nothing printed to say so (`UX-40`).

**The shape of the fix.** A gate on a ratio that is invariant to how much
work the build does. The candidate the audit data supports is work-vs-span:

```text
occupancy_share = Σ task occupancy / (wall_clock × capacity)

  mis-optimized build:  40.25s / (39.57s × 4) = 25.4%
  optimized build:      61.45s / (27.50s × 4) = 55.9%
```

Add three well-parallelized elements and this barely moves. Add three
serialized ones and it drops sharply. That is exactly the discrimination
required, and it needs no data that is not already ingested. Its known
weakness must be stated rather than hidden: the numerator inflates under
contention, because the same work costs more occupancy when elements
overlap — which is why `UX-27` should settle the metric before `UX-39`
ships a gate on top of it, and why the honest long-run version measures
real CPU time from Plane 2 rather than slot occupancy.

Around that metric, three properties matter more than the exact formula:

1. **An absolute floor, not only a delta.** `--min-efficiency 0.45`
   expresses "we accept some inefficiency, we do not accept this much"
   without needing a trustworthy baseline. A delta gate alone ratchets: a
   slow drift of 2% per commit never trips it.
2. **Independent gates with distinct exit codes.** "Slower" and "less
   efficient" are different verdicts and different teams' problems. A
   pipeline should be able to warn on the first and fail on the second.
3. **A defensible threshold, derived rather than guessed.** 1% on
   wall-clock is below the noise floor of any real build. Whatever bar the
   efficiency gate takes should come from repeated captures of an
   unchanged project on the target runner. This is also the honest answer
   to noise generally — a single-baseline comparison will always be
   fragile, and multi-run baselining is the real fix, deliberately scoped
   out of `UX-39` so it does not silently become that task.

> **Done.** `--fail-on-efficiency-regression`/`--min-efficiency` ship on
> `occupancy_share` with their own exit code `5` (`UX-39`), and the
> confidence interaction that kept the gate from running is fixed
> (`UX-40`). All three properties below were implemented as argued; the
> default tolerance was derived from three repeat captures of an
> unchanged project (1.0pp of measured occupancy noise, against 7.4% of
> wall-clock noise on the same three - which is now measured evidence,
> not assertion, that the duration gate's 1% default sits below the noise
> floor). Multi-run baselining remains deliberately out of scope and is
> the most likely thing to force itself next.

### What a good CI comment should look like

```text
Build efficiency: 52% occupancy (baseline 55%, floor 45%)  PASS
Wall-clock: 31.2s (baseline 27.5s, +13.5%)                 WARN - 2 new elements
New elements this change:
  lib-g.bst  2.9s  parallel with lib-a..f          ok
  lib-h.bst  4.1s  serialized behind lib-g.bst     <- 4.1s of new critical path
                   (declares a build dep on lib-g.bst; nothing in its
                    sandbox read lib-g.bst's output)
```

**Built (`UX-115`, 2026-08-19).** `bga compare --format ci-comment`
renders it; [`docs/guides/ci-comment.md`](../guides/ci-comment.md) has the
GitHub Actions wiring. Every part of the sketch above landed, including
the parenthetical: rendered against a real pair of `examples/06` builds,
the never-read column independently reproduced it —

```text
| `lib-h.bst` | 2.0s | yes — new on the path | `core.bst`, `lib-g.bst` |
```

— `lib-h.bst` declares a build dependency on `lib-g.bst` and opened none
of the files it staged.

The route there, for the record: the first two lines needed `UX-27` and
`UX-39`; the element table needed 2b's per-element diff, which `UX-79`
shipped; the parenthetical needed Plane 2's declared-vs-used detection
(`UX-46`).

## Implementation status (updated 2026-08-16, round complete)

**All fourteen items of the `UX-27`..`UX-40` round are done.** What
follows below is the argument that produced them, kept because the
reasoning is still the reasoning - but several of its complaints are now
historical, and are marked where they are.

Four of the round's own filings were corrected during implementation
rather than implemented as written. That is worth more than the fixes
themselves as a signal about how the next round should be run:

- **`UX-28`'s evidence did not support its claim.** It cited an 81%
  per-element contention increase as proof the oversubscription check
  could not fire. The two runs were not comparable and the costlier one
  was 30.5% *faster* overall - beneficial parallelism, not harm. The real
  defect (a bar whose ratio-to-cores collapses as the host grows) was
  different, provable, and only found by checking the fix against
  `UX-09`'s existing measurements instead of against the intuition that
  produced the filing.
- **`UX-32`'s proposed headline metric was backwards.** Achieved-vs-requested
  scores a `-j1`-pinned element at 200% of what it asked for; being pinned
  *is* the problem.
- **`UX-30` and `UX-40` each carried a secondary claim that was already
  implemented** (monotonicity violations are shown; the fail-open does
  warn). Both were pinned by tests rather than "fixed".

The rate is roughly one filing in four. A round of audit findings written
from a single hands-on session should be treated as *hypotheses with
evidence attached*, not as a work list - and the cheapest way to catch
the bad ones is to re-check each against measurements the repo already
has before writing any code.

## Direction 3: what the tool could see next (argued 2026-08-18, round 11)

**Serves:** R2 and R3 — the class of question this opens is *what is inside an element* and *what shape is the graph*, which are their two questions ([roles](roles.md)).

**Status:** partial — items 1-5 landed as `UX-99`..`UX-104`; the cache-effectiveness gate `UX-92` stays ⚪ Blocked, because `UX-514` pinned the capture ref and the cache variation it waited for cannot arrive from the schedule.

With rounds 10-11 the original two directions are substantially built:
the local loop runs end to end from the documented commands, the
marginal gate answers the build owner's growth rule at any project
size, and a baseline history with a weekly cadence exists for the CI
scenario. The question worth arguing now is which *new* class of
finding each future cycle should add. Ranked by (evidence already in
hand) × (how often real builds have the problem):

1. **Sandbox-overhead economics.** BuildStream's per-element logs
   record `Staging dependencies`, `Integrating sandbox`, `Staging
   sources` and `Caching artifact` as timed activities — Plane 3
   already parses the file they live in. On a project staging a
   multi-hundred-MB sysroot into every one of 90 sandboxes, staging is
   a real, per-element, *scheduler-invisible* cost that today lands in
   untracked head or inside the element span, attributed to nothing.
   The findings this enables: "staging is X% of your build",
   "element Y stages 300 MB to run 2s of commands - a composition
   problem", and a measured answer to BuildStream's oldest tuning
   question, whether a project's elements are too fine-grained for
   their overhead. This is the **element granularity advisor**: both
   directions (too many tiny elements → overhead-dominated; too few
   huge ones → poor cache granularity and a long chain) from data
   already on disk.

2. **The developer tax: longitudinal cost ranking.** A single run's
   critical path ranks what made *that build* slow; nothing ranks what
   makes *the project* slow across a month of builds. Plane 3 keeps
   per-element history; UX-92 names invalidation roots per pair. Their
   product is `rebuild frequency × rebuild cost`, summed over a run
   history — which finds the element that costs the team the most
   wall-clock per week, a different and more valuable answer than
   either input. The cache-key churn roots weight this directly: a
   volatile key near the root *is* a high developer tax.

3. **Configure-tax accounting.** Plane 3's phase split plus Plane 2's
   process table both measure the same fact from different sides: on
   this repo's own examples, ~0.3-0.6s of every cmake element is
   configure probes re-answering questions every sibling already
   answered (the 9× repeated `CMakeCXXCompilerId` compiles are already
   a Plane 2 finding). Summed across a real project and its history,
   "N% of your build is configure" is a finding with three known
   remedies (shared config caches, `ccache`, element merging) — and
   the tool can say which elements pay the most.

4. **Remote-cache health as a time series.** Pull/push durations per
   artifact exist in Plane 1's task kinds; the per-run refs now retain
   history. Bytes-per-second per remote over weeks spots a degrading
   cache server before it quietly slows every build in the
   organization — the CI-analytics finding with the highest blast
   radius per implementation hour, and one no single-run report can
   make.

5. **Memory-bound capacity advice.** UX-63's per-task peak memory
   exists; the standing advice "multiply by however many elements
   build concurrently before raising `builders`" is still left as an
   exercise. Computing it — max safe `builders` from the measured RSS
   distribution against host memory, and a gate on additions whose
   memory profile would force `builders` down — closes the last
   decorative half of the capacity axis.

Deliberately *not* on the list: merging the planes' timelines (still
impossible for the reasons `architecture.md` gives), remote execution
(still real, still needing a product decision first), and anything
requiring new instrumentation before the three data sources already in
hand — two planes and the persisted logs — are fully consumed.

**Decomposed into the backlog (2026-08-18):** each item above is now a
filed task carrying its design and an acceptance test against data that
already exists — item 1 as `UX-99` (measure the toll) → `UX-100` (the
granularity advisor), item 2 as `UX-101` (the round's High), item 3 as
`UX-102`, item 4 as `UX-103` (which is also the trend stage `UX-92`
deferred), item 5 as `UX-104`. Prerequisite defects, filed by round 11,
gate where they must: `UX-93` (honest churn labels) before anything
ranks or trends on rebuild causes, `UX-96` (the refs helper) before the
trend consumes history, `UX-83`'s plumbing carries the memory envelope.
The backlog rows and files are the source of truth from here; this
section stays the argument.

## Direction 4: seeing every process — the static-binary blind spot (argued 2026-08-18)

**Serves:** R2, whose element's real cost is exactly what a blind spot hides, and R1, who acts on the ranking that cost feeds ([roles](roles.md)).

**Status:** landed — the spine and the static-binary fallback ship (`UX-105`..`UX-108`).

Plane 2's one deliberate, load-bearing limitation has been there since
`UX-11` chose the mechanism: `LD_PRELOAD` fires when the dynamic linker
loads the hook into a freshly exec'd process, so **a fully static
executable produces no record and no error** — the hook, in its own
words, cannot detect its own absence. Every Plane 2 report carries the
disclaimer. What the disclaimer costs, concretely: a musl-based
toolchain, busybox build steps, or static Rust/Go tooling is invisible
to CPU-per-binary, concurrency, memory and redundancy analysis alike —
and this repository's *own* `examples/01`/`02` manual elements run
static busybox, so their Plane 2 capture is empty today and nothing
says so beyond a generic footnote.

The existing design is worth keeping, not replacing. The shim → argv
rewrite → in-sandbox env transport chain (`bwrap_shim.py`) is validated
against real BuildStream invocations and carries element/invocation
tagging; the hook's open-tracking (`UX-46`) *requires* in-process
interposition and cannot be had any other way at acceptable cost. So
the question is what **complementary** mechanism sees the processes the
linker never touches.

Alternatives, weighed:

| mechanism | sees statics | argv | CPU/RSS | extra privileges | verdict |
|---|---|---|---|---|---|
| `LD_PRELOAD` (today) | no | yes | yes (`getrusage`) | none | keep, for enrichment + opens |
| **ptrace event spine** (fork/exec/exit stops only) | **yes** | **yes** (read at exec-stop, no race) | **yes** (`/proc` at exit-stop) | **none** (tracees are the tracer's own descendants; allowed under Yama `ptrace_scope=1`) | **chosen** |
| BSD process accounting, `acct(2)` | yes | no (15-char comm) | yes | `CAP_SYS_PACCT` | rejected: needs root, loses identity |
| netlink `CN_PROC` events | yes | race via `/proc` | no | `CAP_NET_ADMIN` in the init namespace | rejected: races on exactly the short-lived processes that matter |
| eBPF (`sched_process_exec`/`exit`) | yes | yes | yes | root + kernel config | rejected as baseline: unavailable in the dev containers this project runs in; the data model gains nothing over ptrace events |
| `/proc` polling | partially | race | race | none | rejected: misses sub-poll-interval processes — compilers' `as`/probe processes are exactly that |
| `fanotify` `FAN_OPEN_EXEC` | yes | no | no | `CAP_SYS_ADMIN` | rejected |

The chosen shape: a **static-linked process-spine tracer**, injected by
the *existing* shim exactly the way the hook already is (one more
`--ro-bind`, prepended to the sandboxed command), running inside the
sandbox as the ancestor of the whole element build. It ptrace-follows
fork/clone/exec/exit **events only** — never per-syscall, which is
where strace-class overhead lives — and writes START/END records with
argv, timestamps, exit status, `utime`/`stime` and peak RSS to the same
trace log the hook already writes to, on the same `CLOCK_MONOTONIC`
timeline. The hook stays exactly as is: where a process is dynamic, its
hook record *enriches* the spine record (opens, child rusage); where it
is static, the spine record stands alone and only open-tracking is
honestly absent. Coverage stops being a disclaimer and becomes a
measured number.

The costs, named up front because each is a real risk: the tracer
inherits init duties when BuildStream's `--as-pid-1`/`--unshare-pid`
make it the sandbox's pid 1 (reap orphans, forward signals, propagate
the real command's exit status); a tracer bug can hang a build, so the
posture is fail-open everywhere (on any tracer error: detach all,
record the degradation, the build continues — ptrace auto-detaches if
the tracer dies, which makes crash-safety structural); and the
per-process event cost must be *measured* against a configure-heavy
build before the default flips on, not assumed.

**Decomposed into the backlog (2026-08-18):** `UX-105` (the static
census — make the blind spot itself measured and named, per element,
before building anything; it also produces the ground truth the tracer
is verified against), `UX-106` (the spine tracer), `UX-107` (merge,
dedupe and provenance in the parser and report — coverage as a number),
`UX-108` (validation at real scale: the busybox examples gain their
first Plane 2 records ever, fdsdk confirms no regression and the
overhead budget). The backlog files carry the design details; this
section stays the argument.

## Direction 5: the last inch, and the next axis (argued 2026-08-19, round 12)

**Serves:** R4 — the CI comment's last inch — then R1 and R2 for the axis that follows it ([roles](roles.md)).

**Status:** landed — `UX-112`, `UX-113`, `UX-116`, and the polish round `UX-125`..`UX-127`.

Directions 3 and 4 are implemented. What round 12's verification says
about where the leverage now sits, ranked:

1. **Render the CI story's last inch** (`UX-115`). Every ingredient of
   the design-doc CI comment — the band verdict, both gates, the
   marginal element table, churn with honest labels, findings ids —
   is verified and shipping. Nothing renders them where a reviewer
   looks. A gate that fails as JSON gets its threshold loosened; a
   gate that fails as a named element with its cost gets the element
   fixed. Render-only by design: if this task needs a new number,
   something upstream was missed.

2. **Assemble the founding answer** (`UX-116`). UX-09's original
   question — what should `builders × max-jobs` *be* — now has every
   constraint measured in one capture (scheduling knee, cores-busy,
   memory envelope, pinning). Intersecting them is a paragraph, and it
   retires the report's oldest standing caveat wherever it runs.

3. **Make universal coverage affordable** (`UX-113`, after `UX-112`
   prices it honestly). The spine works and sits opt-in on cost
   grounds; the census knows per element where the hook is blind.
   Joining them (`--trace-spine=auto`) buys statics coverage at
   hook-only cost on the 95% of elements that don't need the spine —
   otherwise Direction 4's blind spot quietly reopens by default.

4. **Remote execution** — the one item untouched since round 1, and
   still deliberately unfiled: with a remote worker pool, `builders`
   stops being the capacity denominator and Plane 2's sandbox is on
   another machine. It needs a product decision (detect-and-refuse vs
   model) before it needs code, and nothing in rounds 2-12 has forced
   that decision. It should be taken up only when a real
   remote-execution user exists to measure against — every mechanism
   this project shipped was validated against a real build, and this
   one cannot be validated against anything else.

5.5. **The polish axis** (added 2026-08-19, round 13): with the MVP
   bar met, the highest-leverage work is shortening the user's path to
   what already works — `bga doctor` for the environment (`UX-125`),
   the one-command loop with a project-local run store (`UX-126`), and
   Plane 3's front door (`UX-127`). Correctness that takes a half-day
   of setup and five invented paths per iteration is correctness most
   users never reach; this axis outranks new capability until those
   three land.

5. **Fleet aggregation** — the developer tax (`UX-101`) is one
   machine's history; a team's tax lives across laptops and runners.
   Cross-machine aggregation is a data-plumbing direction (ship run
   directories somewhere; the analysis exists) and should wait for the
   single-machine tax to prove its worth in use, which the WEAK
   EVIDENCE hedge currently reflects.

## Direction 6: the source axis — blast analysis by shared resource (argued 2026-08-20, round 18)

**Serves:** R2, who owns the repository a change lands in, and R3, who owns what that change rebuilds ([roles](roles.md)).

**Status:** landed — the decomposition below closed (`UX-171`..`UX-174`).

Filed from a real user request, round 18: *blast analysis doesn't take
element kind into consideration; and in the monorepo case — one repo
populating the sources of many elements — it should answer "this repo
was touched: how many recipes rebuild?"* Both halves are right, and the
second opens an axis the tool has never had.

### What blast radius currently is, and what it is blind to

`compute_downstream_count` (`bga/graph/edg.py:281`) counts reachable
downstream *elements*, per element, unweighted. Two blindnesses:

1. **Kind.** `graph.json` already records `element_kind` per element,
   and the counts ignore it: a blast of 84 where 39 are `stack`s and
   4 are `import`s (no build commands, near-zero rebuild cost)
   overstates the damage the way "0 of 7 scheduled built" overstated a
   failed build's. The measured durations to weight by are in the same
   run directory.
2. **Sources.** Every blast question the tool can answer starts at an
   *element*. The user's question starts at a *resource* — a git
   repository, a local directory, a tarball — and no analysis maps
   resources to the elements they populate, though `read_element_yaml`
   already parses every element's `sources` stanza for the census.

### The mechanism that makes monorepos the worst case

BuildStream keys sources differently by kind, and the difference *is*
the monorepo problem:

- A **`git` source keys on its ref** (the commit sha). Twenty elements
  sourcing the same url with different `directory:` values all carry
  the same ref — any commit to that repository, touching any path,
  bumps the tracked ref and rebuilds **all twenty** plus their
  downstream closures. The `directory:` field narrows what is staged,
  not what is keyed.
- A **`local` source keys on content.** Elements staging different
  subdirectories of one checkout rebuild only when *their* files
  change — per-directory blast, which is what a monorepo wants and
  exactly what the git-url pattern does not give.

So the same monorepo consumed two ways has blast radii that differ by
an order of magnitude, the project's `.bst` files encode which way it
is consumed, and the tool can compute both today, offline, from the
element YAML plus `graph.json`. That is the new dimension: **group
elements by shared source resource, compute the union of their
downstream closures, weight by kind and by measured durations, and
rank resources by what touching them costs.** For `local` sources the
question refines to the file level — "which elements' source
directories contain this path" — which is the per-commit answer a
monorepo actually needs.

BuildStream has no native per-subdirectory git keying, so the
patterns worth documenting are: whole-repo git url (simplest, widest
blast — the pitfall this direction measures), per-component
repositories or refs (smallest blast, most maintenance), the
workspace/local-checkout pattern (content keying, per-directory blast,
the practical monorepo answer for CI that checks the repo out anyway),
and junction pinning (blast at junction granularity, visible the same
way). The report's job is not to pick one — it is to show what the
current pattern costs in measured time, so the choice is a number
rather than a taste.

### Decomposition

- `UX-171` — the source inventory and the report section: resource →
  elements → closure, counts by kind, measured cost when a run is
  present, keying semantics stated per resource. The monorepo case is
  the headline row.
- `UX-172` — `bga blast <resource|element|path>`: the query form of
  the same table, including the file-level answer for local sources.
- `UX-173` — kind-awareness retrofitted into the *existing* blast
  ranking and the compare-time invalidation note (the user's literal
  first sentence).
- `UX-174` — the monorepo patterns documentation: the keying
  semantics, the four patterns, and how to read the new section.

Plane 3 extension (not filed): cache logs already carry per-element
rebuild history; joining it to the source inventory would turn "what
would touching this cost" into "what has touching this cost this
month" — worth filing once UX-171's inventory exists to join against.

## Direction 7: the viewer — a thin window onto the JSON (argued 2026-08-21, round 21)

**Serves:** R1, R2, R3 and R4 — everyone who reads a report rather than a payload. The viewer serves no role the payloads do not; that is the whole of its thinness ([roles](roles.md)).

**Status:** landed — all three iterations' decompositions closed (`UX-193`..`UX-214`).

Filed from the user's request, round 21: *"we are on the verge of
necessity for making a viewer"* — `bga view @snapshot` serving a local
page, timelines offloaded to ui.perfetto.dev, the schema enriched so
standard visualization libraries can render the findings, and the
whole thing thin enough to keep maintaining as the reports grow.

### The one rule that keeps it thin

**The published JSON is the entire interface.** UX-190 just gave every
output a self-declared schema (`analyze/v1`, `compare/v1`,
`blast/v1`); the viewer consumes exactly those payloads and nothing
else — no private endpoints, no server-side rendering of report
semantics, no viewer-only computation of numbers. Two consequences do
all the work:

1. *Anything the viewer should show must first exist in the JSON.*
   Wanting a new panel forces the data into the published schema,
   where the text renderer, CI consumers and external tools get it
   too — the viewer can never fork the report's meaning.
2. *The viewer renders the schema, not the report.* Sections are
   generated generically — arrays with column hints become tables,
   `findings[]` with severity become the findings list, deltas with
   direction semantics get their arrows — so a new field renders with
   zero viewer changes. Custom code is budgeted per-view and starts
   at exactly one place: the Perfetto handoff.

The door for "dozens of cool TypeScript libraries" is the same door:
**view-hints in the schema** (a `bga:unit`/`bga:quantity`/
`bga:severity` vocabulary on the JSON Schema properties — duration_us,
bytes, share, count; finding severities; column orderings). Any
external tool that reads JSON Schema can then chart the report without
bga shipping or blessing a frontend stack. If a richer TS app ever
exists, it is a *consumer* of this contract, not part of `bga view`.

### The server: standard library, localhost, ephemeral

`bga view @last`: `http.server` bound to `127.0.0.1` on an ephemeral
port, `webbrowser.open`, `--port`/`--no-browser` for the rest. It
serves three things: the static page (checked into the repo — vanilla
ES modules, **no node toolchain, no build step**; the repo is a Python
project and stays one), the snapshot's JSON payloads (generated
through the same `main()`s the CLI uses, cached beside the run), and
the chrome trace for the timeline handoff. Nothing writable, nothing
outside the snapshot, no directory listing — the threat model is
"local tool", and the binding plus a path allowlist keeps it that.

### Timelines: all of it goes to Perfetto

No timeline of our own, ever — ui.perfetto.dev's renderer and its SQL
engine are better than anything this repo should maintain. The
mechanics are the documented deep-link handshake: the local page opens
`ui.perfetto.dev`, waits for the `PING`/`PONG`, and `postMessage`s the
trace bytes — ~30 lines, no server round-trip, and worth one sentence
of docs because it *looks* like an upload and is not: the trace goes
browser-to-browser-tab, processed client-side.

`bga view --perfetto @last` skips the report page entirely: serve the
trace, open the handshake page, done — UX-188's `bga timeline` output
is exactly the input. The **SQL engine** is exposed the cheap way: a
"queries" page of canned PerfettoSQL snippets (per-element aggregates,
sandbox-tax shares, longest stalls — each one paste-ready), grown as
questions recur, costing a docs page rather than a feature.

**Format decision, recorded**: stay with legacy Chrome JSON. Perfetto
ingests it natively; the protobuf format buys density and streaming,
not capability we lack, and our traces gzip well (Perfetto accepts
gzipped input). Revisit trigger: a real capture whose JSON trace
exceeds what the handshake comfortably posts (~hundreds of MB), which
is UX-169 territory before it is a format problem.

### Two delivery modes, one page

The same static page runs from the server *and* as a file:
`bga view --export report.html` inlines the JSON into the page and
writes one self-contained artifact — the CI journey's PR-comment
sibling (attach it to the pipeline), the "send me your report" answer
for remote debugging, and the mode that needs no port. The Perfetto
handoff works identically from a `file://` opener.

### Usage scenarios (the brainstorm, kept)

- **Snapshot home**: Key Findings first, the verdict banner with the
  refusals given visual weight — a `NOT COMPARABLE` or suspend banner
  in red is the honest-refusal work finally *looking* like what it is.
- **The band, drawn**: compare view renders the noise band as a strip
  with the baseline runs as dots and the candidate as a marker —
  UX-170's "within the baseline set's own observed range" becomes
  self-evident in a way no sentence achieves.
- **Blast explorer**: the Shared Sources table with each row
  clickable into its blast view; an element/path/url search box that
  is `bga blast` in the browser.
- **Store trend**: the run store as a timeline — durations, verdicts,
  cache-trend per snapshot — making `--list` visual and the history
  legible.
- **Canned SQL page** (above) and **`--perfetto`** direct mode.
- Deliberately *not* filed: a dependency-DAG view. It is the one
  panel that would need a real graph library; it waits until a
  concrete question needs it, with the vendoring decision made then.

### Decomposition

- `UX-193` — the core: server, shell page, schema-driven rendering,
  view-hints v1 in the schemas.
- `UX-194` — the Perfetto handoff: handshake, `--perfetto`, gzip,
  canned SQL page, the format decision as a guard-visible note.
- `UX-195` — the export mode and its CI wiring.
- `UX-196` — the comparative views: band strip, store trend, blast
  explorer.

### Second iteration (argued 2026-08-21, round 22): the viewer learns what it is looking at

Synthesized from two inputs after UX-193..196 landed: the user's four
field observations, and an external review of the shipped viewer whose
code claims round 22 verified one by one — **all six confirmed**. The
review's thesis, adopted: *the biggest opportunity is not more generic
JSON rendering; it is making the viewer understand BGA's analytical
relationships and use Perfetto as the execution-detail engine.* The
foundation (thin server, schema boundary, export, handoff) stays.

**Adopted, with the ground truth that earned each:**

1. **Recursive schema semantics** (review P0). Confirmed: hints are
   read from top-level properties only, and everything nested falls to
   `guessQuantity(key)` name-sniffing — two semantic systems that
   demonstrably disagree (`peak_rss_mb: 512` renders "512 B";
   a 0-100 `cpu_pct` renders "4200.0%"). The fix is the direction's
   own rule taken seriously: hints resolve through nested schema
   nodes, columns carry per-column metadata, the findings/blast item
   shapes enter the schemas, `verdict` becomes a declared enum beside
   its sentence (the banner currently string-matches prose), and
   schema `description`s render on demand — the "why is this number
   important" answer, sourced from the spec rather than viewer prose.
2. **The BGA overview and the evidence header** (review P0 twice).
   The shipped page renders sections; it does not render the
   *argument* — real duration → scheduling gap → runtime gap →
   floors, and above it the evidence line (confidence, coverage,
   incompleteness). Every number from published JSON; the UX-196
   no-arithmetic guard extends to both.
3. **Perfetto as investigation, not destination** (review §6/§7).
   Buttons that carry *why you are going* — a finding's context, a
   pre-selected canned query — with a small link-builder
   (TraceContext) rather than a new layer. Ordered **after** the
   transport fix below, because context on a blocked popup is
   context on nothing.
4. **Tables that can be searched** (review §10), **the export keeps
   its questions** (§8, option B — inline them), and **focused graphs
   only** (§13/§14 — the review's own restraint matches the
   direction's deferred-DAG stance: critical-path chain and blast
   tree, no general DAG viewer).

**Adjusted:** the review's four-layer architecture is directionally
right and over-built for a no-toolchain viewer — TraceContext ships
as a module, not a layer. Its P3s (element inspector, comparison
workspace) stay deferred.

**What the review missed and the field supplied:** the handoff it
praises is **popup-blocked by construction in current Chrome** — the
`window.open` is never synchronous with the user's click (the
`--perfetto` page auto-runs with no activation at all; the report
button opens only after an async fetch). Transport first: open the
tab inside the click, fetch after, post when both are ready; the
`?url=` deep-link (with a CORS allow for ui.perfetto.dev only)
as the belt to the braces. And two shipped views cannot be seen at
all — the band view renders only compare payloads, which no CLI path
ever serves; the trend plots snapshot *size* where the filing
promised duration and verdicts — found by this round's verification,
not the review, and filed with it.

Decomposed as `UX-198`..`UX-206`; the wheel-shape guard gap (CI never
runs an installed `bga view`) rides with the unreachable-views item.

### Third iteration (argued 2026-08-22, round 23): stop adding, start compressing

The second external review, taken after UX-198..206 landed, opens
with a verdict this direction accepts in full: **stop adding major
viewer architecture; spend the next iteration on compression and
actionability.** Its diagnosis, confirmed against `boot()`: the page
is functionally rich but *report-shaped* — evidence, overview,
fourteen generic sections, drawings and tools all at one visual
level, with the TOC and collapse compensating for density rather
than solving prioritization. The reader has to read too much before
knowing what deserves attention, while the answer the product is
framed around — what should I fix first, and what is it worth —
already exists in the published findings and renders mid-list.

**The rule adopted for everything that follows:** *first screen =
decision, everything else = evidence.* The page should show the
smallest amount of information needed to choose the next useful
investigation, then make that investigation one click away.

**Adopted, with the house adjustment that keeps the viewer thin:**
the decision panel's inputs — the chain-bound/scheduler-bound
diagnosis (computed at `bga/findings.py:974`, published today only
as prose in one finding's sentence), the opportunity split, the top
actions — enter `analyze/v1` as a published `headline` block first,
because a viewer that derived them would be a second analyzer. Same
rule, third application (the band needed the compare payload, the
blast tree needed published depth). Decomposed as `UX-207`
(decision first), `UX-208` (every important object carries its
investigation), `UX-209` (questions for names, a rail for the
contents page).

**Declined with the review's own argument:** the stat-card
dashboard it warns against (§15) — bga's numbers are relational,
and a card grid is where the relations go to die.

**What the review missed, supplied by this round:** it praised the
question library without reading the SQL — four of six canned
queries are track-blind and answer wrongly on exactly the merged
two-plane traces the tool is proudest of (`UX-210`); its
remember-my-state item is `localStorage` thinking where the house
ethos (evidence you can paste) wants view state in the link
(`UX-211`); and it never looked at the drawings' color-only
encodings at all (`UX-212`). Verification added what no review
sees: the round-22 landing's named mutation guards are pinned to a
capture that exists on one machine and skip everywhere else
(`UX-213`), and the trend's colouring is a second verdict chain
that re-litigates the disputed region (`UX-214`).

**What landing all eight cost, recorded because a proxy that moves
is worth less than one that is explained.** Direction 7's page-size
ceiling is a byte count standing in for "the viewer stayed thin, no
framework". This round's features — the decision panel, the rails,
the table tools, the trace context, the SQL cookbook as data, the
view state in the fragment — carried the page from 62 KB past
80,000 B and then past 90,000 B. Every recoverable byte was
recovered (the export strips the stylesheet's comments now, as it
already stripped the modules'); the rest is feature code, and only
a deletion would bring it back. The ceiling moved once, to 96,000
B, with the arithmetic in the guard's own docstring — and a second
guard now asserts the thing the number was standing in for: the
page *is* the checked-in modules plus the stylesheet, so 4 KB of
new feature and 4 KB of vendored library stop looking alike.

## Direction 8: the provenance model — every claim carries its evidence (argued 2026-08-23, round 27)

**Serves:** every role that has to trust an answer secondhand — R4's
CI comment and R8's prioritisation case most of all; R1 directly
([roles](roles.md)).

**Status:** landed — `UX-227`..`UX-230`, and the regression verdict's own evidence chain (`UX-593`), which is what the CI comment had been quoting the candidate diagnosis's in place of. Publishing that chain as a `compare/v2` key is filed.

The fourth external review's strongest idea, adopted — and it is the
house pattern one level up. Round 24 found the relationship layer
computed and unpublished (`correlate/v1` closed it). What remains
unpublished is the layer above the facts: **why bga believes what it
believes.** The headline says `execution-bound`; the attribution
fields that fired the diagnosis, the thresholds they crossed, and the
Perfetto query that would prove it deeper are all real — and the
chain from claim to evidence exists nowhere a consumer can read. The
viewer composes fragments of it (`elementFacts()` walking five report
sources was the review's own tell), the CI comment asserts verdicts
without their grounds, and a reader who asks "why do you say this"
gets a document to grep rather than an answer.

The fix is a published contract, not a UI: each claim — the
diagnosis, each finding, each top action — carries its evidence as
**references into the same payload** (field paths and the values
read), the rule that fired, and the trace query id that deepens it:

    claim → evidence (field refs) → rule → trace query → action

One object, four consumers: the page renders it (and stops composing
its own), the text renderer prints it, the CI comment cites it, and
any future interface — an IDE panel, an LLM asked "why is this build
slow" — reads the same chain instead of re-deriving one. That last
consumer is the review's point and worth recording: a model that
explains itself is the difference between an AI interface that
paraphrases bga and one that hallucinates around it.

**Challenged, against the positioning:** the review's trajectory ends
in an investigation *workspace*, then a build-performance IDE. Both
are renderer rearrangements, and both are declined for now with the
argument round 24 already recorded against the drawer: panes and
overlay machinery are the parts of a page that do not survive an
export, a print, or a pasted anchor — and the document form is what
makes the report evidence. The model comes first; if a workspace is
ever worth it, it will be a cheap rearrangement of published objects
rather than a place analysis secretly lives. The "causal graph"
likewise: the *object* is this direction; a drawing of it is a
deferred maybe, behind the same bar every graph has faced here.

### Decomposition

- `UX-229` — publish the provenance object; the anchor everything
  else reads.
- `UX-227` — "why is this ranked first", composed from published
  fields today, re-plumbed onto `UX-229` when it lands.
- `UX-228` — focus becomes an investigation mode: the evidence
  around one element, organised, from published relations only.
- `UX-230` — what-if selection, constrained to published or
  server-computed projections (the review's checkbox sketch, minus
  the client-side simulator it warned against itself).
- Later, on top: the CI comment quoting evidence chains; the
  explain-path for compare ("here is the chain behind this
  regression verdict", extending `UX-221`'s culprits).

## Direction 9: the team axis — from one build to the fleet (argued 2026-08-23, round 27)

**Serves:** R5, R6, R7, R8 — the roles the
[role model](roles.md) found unserved.

**Status:** landed — the aggregate fact-base (`UX-234`), the queue seam (`UX-594`), the capacity model (`UX-595`) and the cost translation (`UX-596`). Two tails are filed rather than open here: the start clock's provenance, and a stamped contract for the model's answer.

Everything bga answers today is answered within one build, or one
store's history of one project. That satisfies R1-R4 — and
twenty-six rounds of serving them well is exactly why the
presentation Pareto is exhausted there. The unserved questions live
**across** builds:

- **R5, the capacity operator:** how many concurrent builds does
  this hardware sustain; what utilization do we actually achieve;
  what would one more builder buy; is the cache infrastructure
  earning its cost?
- **R6, the CI user:** why did my verdict take 40 minutes when the
  build took 12 — and the honest answer involves a queue bga cannot
  currently see, because its clock starts when the build does.
- **R7:** what is the p95 build, and is it drifting?
- **R8:** what does build time cost the team, and what is a fix
  worth in those terms?

**The throughput-latency contradiction is the design center.** R5
wants machines full; R6 wants queues empty; these are the same curve
read from opposite ends. The house answer is the one the noise band
already gave the gate-strictness contradiction: model it, publish
both readouts, and let the argument happen over numbers. Queueing
models need arrival rates and service-time distributions — and a
store full of bga captures *is* a measured service-time
distribution, per project, per host class, with resource profiles
attached. That is the mathematical-modeling asset this direction
builds on.

**Non-goals, stated before anyone asks:** not a monitoring system,
not a scheduler, not a dashboard product, not Perfetto-for-fleets.
bga stays the entry point: measured facts, published contracts, a
model with stated assumptions, and a refusal grammar for what the
data cannot support (`UX-186`'s cross-host honesty already is this
direction's tone).

### Decomposition

- `UX-234` — the aggregate contract: distributions over a store
  (durations, variance, hit rates, resource percentiles), the
  fact-base every R5/R7 answer stands on. The anchor.
- Then, in argued order: the **queue seam** (a capture that can
  record when the build was *requested*, not just started — one
  optional timestamp, and turnaround becomes measurable end to end);
  the **capacity model** (builders N + measured profiles →
  utilization and wait-time distributions, assumptions printed with
  every number); the **cost translation** (R8's units, opt-in
  rates); and only then any presentation.

## Round 24: publish the relationship, then navigate it

A third external review, evaluated the same way as the first two. Its
one-line statement of where the tool is, adopted:

> the next improvements should not make the page prettier; they should
> turn existing BGA facts into stronger navigation and investigation
> primitives.

**The finding that reframes it.** `bga/correlate.py:141` already
assembles the relationship layer — one `ElementJoin` per element,
Plane 1's path share, saving and blast radius beside Plane 2's
achieved parallelism, CPU coverage, peak RSS and dominant binary. `bga correlate --format json`
emits it, correctly and completely — and unversioned: no `schema`
stamp, so `UX-190`'s contract does not cover it; no view-hints, so the
viewer could not render it generically; and `payloads()` does not serve
it. `correlate --schema` says so itself: *"correlate produces no
versioned JSON output"*. So the "element inspector" and the "three-plane
investigation ladder" the review proposed as new work are one
already-computed join missing a contract.
That is this project's oldest pattern, on its fourth occurrence after
`blast_tree`, `headline` and the compare payload the band needed: **the
analysis knows, and the published schema does not say.** Direction 7's
rule is what makes the fix cheap and the shortcut expensive — a viewer
that assembled the join itself would be the second analyzer the whole
architecture exists to prevent.

**And the correction to round 23's own work.** `UX-208` shipped a
generic Inspect on every element row, anchored at a fragment nothing in
the page sets: 19 links, 11 distinct targets, 11 unresolvable. The
guards asserted the affordance existed, not that it arrived. Same
failure class this project keeps finding, in the round that was about
finding it — which is the argument for `UX-216` naming resolution, not
presence, as its acceptance.

**Declined, with the reasons recorded:** the element inspector as a
*drawer*. Overlay machinery is the one part of this page that would not
survive an export opened from a downloads folder, a print,
`filter: grayscale`, or a pasted anchor — and a section gets the same
cross-reference value while making the dead anchor resolve as a side
effect. "Resist adding more charts" was agreed rather than filed: it is
this document's standing position already.

**What the review did not look at: the loop.** Every item it proposed
improves one reading of one report. The friction this tool is built
around is `capture → analyze → read → change → capture again`, and that
is where the repetition is. Three items came from walking it — the next
three commands are always retyped and can be *published* (so the
terminal, CI and the page agree on the next step rather than the viewer
deciding), the investigation is not resumable because `UX-211` carried
the view and not the decision, and "did my fix work?" is still answered
by opening two reports side by side.

## Round 25: the first four, executed

Round 24's argument, executed. Four items, in the order the audit
recommended, and the order mattered: nothing after the first is honest
without it.

**`UX-215` was a stamp, a schema and thirty lines of wiring**, and it
is the one that made the rest cheap. `correlate/v1` publishes the
`ElementJoin` that `bga/correlate.py` had been computing since `UX-51`
and emitting unversioned. Then the viewer needed **no change at all**
to draw it: measured on `examples/06`, an eleven-row `element_join`
table under its declared question, with the element role earning every
row an Inspect. That is `UX-193`'s schema dispatch paying for itself,
five rounds after it was built — and the clearest argument yet for the
rule that a field enters the published contract first.

**`UX-216` fixed the round-23 defect and was the reason to look.**
Nineteen Inspect affordances resolving to nothing, because the guard
asserted the affordance *existed*. The acceptance is resolution now,
and the fix is one expression rather than two: `cssId` delegates to
`elementAnchor`, because a link and its target spelling drifting apart
*is* the defect. The mutation that proves it is not renaming the anchor
— it is duplicating the expression with a different character class,
which is exactly how it would recur.

**The drawer was declined and the reasons recorded**: overlay machinery
is the one part of this page that would not survive an export from a
downloads folder, a print, `filter: grayscale`, or a pasted anchor. A
section is linkable, printable, collapsible by machinery that exists,
and it makes the dead anchor resolve as a side effect.

**A guard stopped being about the calendar.** The page-size ceiling was
crossed by ordinary feature work in three consecutive rounds and raised
twice. A number that moves whenever a feature lands is measuring the
calendar, so the third time the *measurement* changed: composition (the
page **is** the checked-in modules plus the stylesheet — the only check
that can tell 6 KB of feature from 6 KB of vendored library),
Direction 7's ratio at the scale the rule names (1,000 elements:
691,401 B of data against a 97,488 B page, **7.1x**), and a loose
structural backstop. The small fixtures invert the ratio and always
did; that is a property of small reports, not of the viewer, and it is
why the absolute was the wrong instrument all along.

**`UX-218` is the first item aimed at the loop rather than the
report.** `next_steps` is published, so the terminal, CI and the page
give the same next command — and the branch that chooses it stays in
the pipeline, because a viewer that picked the next command from
`chain_share` would be the second decision-maker `UX-207` exists to
prevent. The acceptance is not "a command is shown" but "the command
runs": every published `argv` is executed against the fixture. What is
*absent* is asserted too — a chain-bound build is not told to add
builders, a run outside a store is not told to compare.

## Round 26: the eight that were left

Round 24 filed twelve items; round 25 took the first four. These are the
other eight, and the pattern across them is one thing said three ways.

**Twice a task file was wrong about the code, and both errors were worth
finding.** `floors.certified_us` — named in UX-220 as "the most
misreadable number this tool publishes" — has never existed; the
certified floor is `floors.lb`. And UX-221 said no element appears in
`compare/v1` anywhere, when in fact `element_diff` has carried
*appearance and removal* since UX-79 — the two cases the file predicted
a naive join would drop were the two already present, and the elements
in **both** runs, which is what "because of what?" actually asks about,
were the ones missing. An audit is a hypothesis. Reproducing it first is
not ceremony.

**Twice a mutation a task file specified could not fail.** UX-219's
"re-add the savings instead of reading `cumulative_saving_us`" cannot
discriminate on any real report, because the two are equal by
construction. UX-221's "sort the strip by its own computed delta" passed
because the four-case fixture puts exactly one element in each group and
no assertion about the order of a one-element list can fail. Neither was
counted. One was replaced with a synthetic payload where the two values
differ; the other with a three-regression fixture. A mutation that
cannot redden is not evidence, and writing it down as though it were is
the failure this discipline exists to prevent.

**Three times a guard had to change, and each change is recorded as a
decision rather than absorbed.** UX-201's fixtures were pinned to three
`utilisation` keys no code path emits — re-pointed at published fields
rather than deleted, and they still catch the original renderer bug.
UX-196's "only two custom drawings" asserted a count while its docstring
stated the rule; it holds the named set now, which also catches a
drawing being moved or removed. And the page-size backstop was crossed
for the fourth round running.

### The backstop, and what a number cannot measure

UX-218 replaced an absolute page ceiling with composition + ratio + a
loose absolute, having watched the old ceiling get raised twice, and
wrote the reason down: *a number that moves whenever a feature lands is
measuring the calendar*. Round 26 crossed the new absolute too.
Measured at the crossing:

```text
page (data removed)   123,785 B
  modules             109,913 B
  style.css            12,552 B
  index.html            1,433 B
  accounted           123,898 B   = 100.1% of the page
export total          184,934 B   = 2.20% of the 8 MiB attachment budget
```

Every byte is a checked-in module. So the backstop did its job — it made
someone look — and the answer was "a round landed", for the fourth time.
The stated purpose was to catch *something structural*, and a byte count
cannot tell a feature from a library.

It is raised to 200,000 and now stands beside a guard that measures the
thing directly: no module may look like vendored or minified code — a
few enormous lines, almost no comments. That guard catches a 12 KB
minified blob which **both** the byte ceiling and the composition guard
let through. If the absolute fires again it should be because that one
is silent and something genuinely odd is happening.

### What the round added to the loop

The first five rounds of the viewer made the report readable. This one
made it *resumable*: the horizon is a plan rather than a table, an
element can be focused, the reader's own marks travel in the link, and
each element carries what it cost across the snapshots. Round three of
an optimization no longer reads exactly like round one — which was
UX-225's complaint, and is the closing of the loop UX-126 opened.

Two clauses were declined and recorded rather than quietly dropped: a
global key to open the palette (it needs a decision about the table
filters UX-205 put everywhere), and markdown detection for the copied
finding (a button claiming to know what a paste target accepts would be
guessing).

## Direction 15: a snapshot bigger than RAM (argued 2026-08-25, round 40)

**Serves:** R1 and R2 first — the field user this round's showstopper
hit — and R5 structurally, since fleet-scale capture is this problem
multiplied ([roles](roles.md)).

**Status:** landed — both iterations closed (`UX-296`..`UX-300`, `UX-308`..`UX-312`).

The field report that opens the axis: a real project's dual-plane
snapshot produced a **~2 GB run directory** — `plane2.json` at
1.5 GB, the raw Plane 2 log another 400 MB gzipped — and `bga view`
on it **runs out of memory** near server start, after a long freeze
in parsing. This is not a defect in a feature; it is the storage
architecture meeting its ceiling. Every event this tool has ever
processed has travelled as one JSON document, parsed whole into
Python objects — and a JSON array's bytes multiply several-fold in
RAM as objects. At example scale that was invisible. At field scale
it is a showstopper, and it was always going to be: **the format was
the decision, made implicitly, at thirty events.**

Round 40 reproduced it at scale and measured every path (the full
table is in [round 40](../audits/round-40.md)). The verdict in one
paragraph: `bga view`'s startup serially runs **every whole-file
load path in the codebase** before the socket binds — a 2.9×
bytes-to-RAM `json.load` of the monolith for the report, a second
full parse of *every store snapshot's* monolith for two scalars, a
per-historical-run re-analysis for the band, and then a merge step
that decompresses the raw log to ~4.7 GB of disk and reads it as
one string at a measured 6.3× amplification — ~30 GB projected,
immediately before the server is constructed. Two facts sharpen it
from "big files are big" into an architecture finding: **~95 % of
the monolith is dead weight** (the embedded per-process record
list has no production reader — every consumer reads the small
aggregates beside it), and **the streaming fix already exists on
the wrong path** (`UX-168` taught the capture-time tracer to
stream and consume; the converter `bga view` actually calls still
does `pair_events(parse_trace_log(f.read()))`). The scale axis is
this project's oldest pattern in a third costume: the analysis
knows how to be small — and the paths that matter never learned.

### The rules the redesign is built under

1. **Capture computes; view serves.** `UX-226` decided a history
   slice is written at capture time because view-time analysis
   multiplies by the store. That decision, promoted to an
   architecture rule: nothing on the `bga view` path may do
   O(events) work — the viewer process opens large artifacts only to
   stream bytes to a socket. If a capture predates its artifacts,
   the page says which command to run; it does not run it.
2. **Events are a stream, not a document.** Any artifact whose size
   is O(events) must be writable and readable without materializing
   the whole: written incrementally at capture, read incrementally
   or not at all. One JSON array of two million objects satisfies
   neither and is retired from the event path.
3. **The event artifact is Perfetto's format.** Adopted, from the
   user's proposal, with the argument made explicit: the deep half
   of every event question is already answered by handing the trace
   to Perfetto, so the event artifact should *be* the interchange —
   protobuf TrackEvent (`Trace` = a stream of `TracePacket`s;
   `TrackDescriptor` per lane with uuid/parent for the two planes'
   hierarchy; `TYPE_SLICE_BEGIN/END` with interned names;
   `TYPE_COUNTER` for the resource series). Appendable
   packet-by-packet, so it streams and gzips on the fly; varints and
   interning make it several-fold smaller than the JSON it replaces;
   and `trace_processor` can query it later if an analysis ever
   needs to — without bga growing a query engine.
4. **No new dependency for it.** The protobuf wire format is varints
   and length-delimited fields; a TrackEvent emitter is a small
   single module in the standard library, with field numbers pinned
   as named constants. Correctness is held the house way: a golden
   trace opened in Perfetto once with the result recorded, digest
   stability guarded, and a round-trip check in CI where
   `trace_processor` is available — never by trusting the writer.
5. **Analysis reads aggregates, not events.** `correlate`, the
   census and every published number already reduce events to
   per-element figures; the reduction happens **once, at capture**,
   streamed over the events, and lands in small JSON beside the
   trace (`element_join`, the history slice — the pattern exists).
   The published contracts stay JSON: kilobyte documents were never
   the problem, and every consumer keeps its round-trip guard.
6. **The handoff streams too.** Tab-to-tab postMessage carries the
   whole trace through browser memory — right at 25 KB, absurd at
   1.5 GB. Above a size threshold the `?url=` deep link is the
   default (Perfetto fetches and streams it), and the export stops
   inlining the trace as a `data:` URL, carrying the command and
   link instead — the blast-box honesty pattern at gigabyte scale.
7. **Memory is a guarded budget.** A generated big-run fixture
   (order of 10^6 events, never committed) with peak-RSS and
   startup ceilings on the capture, analyze and view paths — the
   page-size lesson applied to RAM: instruments with argued
   numbers, so scale regressions redden instead of shipping.

### What is deliberately not adopted

- **SQLite / DuckDB as the store** — a query engine inside the tool
  whose positioning is to hand queries to Perfetto's.
- **Parquet/Arrow** — a dependency for columnar analytics no
  analysis runs.
- **The protobuf library** — the wire format needed here is a page
  of code; a dependency would buy generated classes nobody else
  uses.
- **Converting the small contracts** — `analyze/v2` and its
  siblings are the tool's public interface, human-inspectable and
  guard-covered; their scale is bounded by elements, not events.

### Decomposition

- `UX-296` — stop the bleeding: the view path stops parsing runs
  (the measured sites), with the RSS guard that keeps it stopped.
- `UX-297` — extraction streams, and the plane2 monolith retires:
  events reduced at capture into per-element aggregates plus the
  trace artifact; legacy runs stay readable behind one interface.
- `UX-298` — the TrackEvent emitter and the timeline that uses it.
- `UX-299` — the handoff and the export at scale.
- `UX-300` — capture-side footprint and retention: what a 2 GB
  snapshot does to a store, priced and governed.

### Second iteration (argued 2026-08-26, round 43): the trace learns to say what bga knows

The first iteration made the trace the right *container*; round 43
audited whether it uses the container's *vocabulary*, against the
user's question — are we really using Perfetto's power? Measured
answer: no. A slice today carries exactly one fact, its name — for
Plane 2 a command truncated to 120 characters — while the record it
was built from carries CPU time, peak RSS, exit status and the exec
chain, and the Plane 1 task knows its element kind, task type,
cache outcome and every dependency edge. Perfetto's semantic
surface for all of it sits unused: debug annotations (the details
panel is empty; `extract_arg` has nothing to extract), flows (the
dependency arrows a timeline exists for), counter tracks (the
`TYPE_COUNTER` constant was pinned and reserved), trace-level
identity (a trace leaves the machine and forgets whose build it
was), and descriptor ordering (lanes open in discovery order, not
where the report would send the reader).

The iteration's rule extends rule 3: **the artifact is not just
Perfetto's format — it is Perfetto's vocabulary.** Every fact the
capture already holds that Perfetto can express enters the trace in
Perfetto's own idiom, so the UI shows it, `trace_processor` selects
on it, and the canned questions stop querying names and timestamps
because that was all there was. Field numbers keep the UX-298
procedure — read from the protos, never from memory — and every
enrichment rides the existing single streaming pass, under the
existing RSS ceilings. Annotation keys become a contract (the trace
dictionary), because a query built on a drifting key breaks
silently.

Decomposed as `UX-308` (annotations, the full command, the failed
category), `UX-309` (dependency and exec flows, bounded and
priced), `UX-310` (the three counter series the reserved constant
was waiting for), `UX-311` (run identity in the trace, lanes
ordered by the path), `UX-312` (the question library learns the
vocabulary, and the dictionary gets its guard).

## Direction 16: the visual contract (argued 2026-08-25, round 41)

**Serves:** every reader of the page; R1 first ([roles](roles.md)).

**Status:** landed — `styleguide.md` and its guards (`UX-302`, `UX-306`).

The report's visual language, made a governed contract:
[`styleguide.md`](styleguide.md). One dispatch from published shape
to control (raw JSON only where deliberate and labeled), series and
distributions drawn as their shape with a stated `n`, a budgeted
emphasis system (one accent; status tones never without a non-color
channel — the round-41 validator measurements are the argument), and
dark as the design surface with print kept honest. The guide is
enforced the house way — booted-page walks, token guards, a
conformance line in the fixing guide — and amended, not bypassed,
when a new shape appears. Decomposed as `UX-302`..`UX-306`.

## Direction 17: utilization is one envelope, read by three roles (argued 2026-09-05, round 91)

**Serves:** R4 (the CI owner), R2 (the element owner), R3 (the graph
owner), R5 (the capacity operator) — the four whose questions
contradict on the surface and share one quantity underneath.

**Status:** partial — the four corrections are argued here; `UX-675`..`UX-684` are open.

The user's brief, in three questions: can a CI owner tell whether the
agent's cores are the binding resource without overcommitting memory;
can an element owner see their transitive dependencies and blast
radius, and be told whether to split or consolidate; can a graph owner
show evidence that the graph's shape lets a cold build use the whole
machine and a cached build rebuild the cheapest subgraph. Round 91
checked each against what the tool computes (the round-91 inventory: builders and per-element `max-jobs`
known (`UX-377`); every over-time surface counting processes, not
cores; `idle_periods` computed and never published; a memory series
with no CPU field; a sweep with no memory resource; fan-out deep and
fan-in absent; a kind-based foundation exemption; change frequency
absent; remote execution deliberately unfiled since round 1) and
argues four corrections to the brief before it argues the plan.

### Four corrections

**1. "Forty cores occupied" is not the objective; the envelope is.**
Five builders times a native `max-jobs` of eight is a *ceiling*, and
a build that never touches it is not necessarily wasting the machine:
configure, link, staging and cache pushes are single-threaded or
I/O-bound by nature, and a core idle during them is idle by
construction. The quantity a CI owner needs is the **utilization
envelope** — cores busy against cores available, subject to memory
headroom, *as a series over the build* — and its two violations:
under-utilization (busy well below available while work is ready)
and overcommit (load above cores, or swap above zero). Both are
intervals on the same series; neither is a count. The tool has the
memory half of the series (`host-samples.jsonl`, `UX-378`) and no CPU
half: it knows CPU *totals* per process and *processes running* over
time, and processes running is not cores busy — a blocked process
holds a slot and no core.

**2. Per-element `max-jobs` tuning is the wrong lever; sharing is.**
The brief's diagnosis is right — BuildStream has no cross-element
job server, so builders × native jobs is a static product that
over- or under-commits depending on which elements happen to overlap
— and its remedy is fragile: a `max-jobs` chosen per element is
tuned to one graph shape on one machine, and drifts the day either
changes. Every native build system BuildStream drives (`make`,
`ninja`, `cmake`'s generators, `cargo` through `-j`) speaks the GNU
jobserver protocol; what is missing is a jobserver *outside* the
sandboxes that every element's build system joins. That is a
prototype this tool is unusually placed to build: it already owns a
sandbox-injection path (the `bwrap` shim and the `LD_PRELOAD` hook)
and already measures the outcome (Plane 2's process starts against
the host series). Static tuning stays as the fallback the tool
advises where a jobserver cannot be run — priced, not guessed.

**3. Remote execution is two different things, and the tool prices
both without either being installed.** BuildStream's own REAPI runs
an element's whole sandbox on a remote worker (the agent then spends
staging and waiting, and the worker's `max-jobs` is what matters);
compiler-level remote execution (`recc`, `reclient`, `goma`) runs
inside the sandbox and needs a network the sandbox is built to deny.
Neither is a bga feature; both are what-ifs the tool can already
half-price — `bga sweep` prices more builders, and a per-element
compute share prices what a remote worker would take off the agent.
The gap is the sentence that says so.

**4. A blast threshold is the wrong instrument; expected cost is.**
An element owner asked to keep their blast radius "under a
threshold" will split until the graph is a mesh of trivial elements
— which is the other failure. The quantity is **expected rebuild
cost**: how often an element changes (Plane 3's kept logs know)
times what its blast rebuilds (weighted by duration and CPU, with
assembling elements free but counted for height). Split when the two
halves' consumers never change together; consolidate when two
elements always rebuild together — and the co-change matrix that
decides this is the one artifact neither role has. The foundation
tier (toolchain, base image, the things everything depends on by
design) is not noise to filter out of a ranking; it is a *declared*
tier the ranking reports separately, because a discovered tier moves
with the graph.

### What follows

The plan is one series, two rankings and two verdicts, filed as
`UX-675`..`UX-684`:

- **The series** (`UX-675`): busy cores, load and core count on the
  host sampler's tick, beside memory, and on the trace as three more
  tracks. Everything below reads it.
- **The envelope and its intervals** (`UX-676`): the CI owner's
  short answer — were the cores the binding resource without
  overcommitting memory — and the long one: the under-utilized and
  overcommitted intervals as tables, each row naming the elements
  building per builder with their `max-jobs`, the Plane 2 process
  count, the predecessors just finished and the successors waiting,
  and a Perfetto query scoped to the interval. The user's table, with
  its columns; the dead `idle_periods` code re-based on cores and
  published, or deleted.
- **The advisor and its constraint** (`UX-677`, `UX-678`): a
  recommended `max-jobs` per element under a no-overcommit
  constraint, priced by replay; memory as a resource the sweep and
  the queue model honour, so a knee is named by whichever bound came
  first.
- **The sharing alternative** (`UX-679`): a jobserver every sandbox
  joins, through the shim the tool already owns — a spike, judged by
  the envelope before and after, because dynamic sharing is what
  static tuning approximates.
- **Remote execution priced** (`UX-680`): what unbounded builders
  buy (the sweep) and what moving the compiler's CPU off the agent
  buys (Plane 2's share), each with its assumption, neither built.
- **Fan-in** (`UX-681`): direct and transitive upstream counts, the
  never-read share, and the dominator every path passes through —
  the element owner's incoming half, the graph owner's suspicious
  fan-in.
- **Change frequency and co-change** (`UX-682`): from the logs the
  project already keeps, without the ref variation `UX-92` was
  blocked on; expected rebuild cost per element, and split /
  consolidate as findings decided on co-change rather than on a
  threshold.
- **The foundation tier declared** (`UX-683`): because a toolchain
  built with `autotools` is not a structural kind and tops every
  ranking today; the discovery proposes, the owner declares, the
  ranking reports the tier apart.
- **The cached-build verdict** (`UX-684`): the graph owner's evidence
  for the build that happens most — the share of the change history
  that rebuilt under the median blast, height and weight stated
  separately, with its rule and denominator the way the cold verdict
  states them.

What the direction declines: a blast *threshold* (replaced by
expected cost), per-role hues in the page for these findings (§4
rule 7 stands), and observing a remote build (`UX-9` stands — the
tool prices it and does not watch it).

## Direction 18: the suite verifies what was built; the walk verifies what was promised — and both are planned before the code (argued 2026-09-05, round 92)

**Serves:** R8 (the maintainer deciding when to release), and every
implementing session — the suite is theirs, the walk is the reader's.

**Status:** partial — the corrections are argued here; `UX-685`..`UX-692` are open.

The user's brief: the suite grows and hand exploration still finds
problems every time; so a cadence of exploratory testing on a cheaper
model, tied to the release; an impact analysis at the design stage;
a hierarchical backlog so impact and test planning stop rescanning
hundreds of tasks; and, planned carefully, a restructuring of the
specification and the architecture document. Round 92 checked each
against the tree (the round-92 inventory: 472 one-claim files and three journey-shaped ones; the journey guard with an answer key real and unchanged since round 64; no property-based test, no flake ledger, no release gate on a walk; no area field on 682 tasks and no module→contract→guide index; the batch gate settled against batching by `UX-500`'s own numbers; the spec's edge decisions taken in `UX-564`..`UX-568`) and argues five corrections.

### Five corrections

**1. Exploration finds what it finds because the suite tests claims
and a reader tests journeys — so make the journey the unit.** Every
guard in `tests/unit/` is one file per claim, and a claim is true
the moment it is written; a reader meets the page in sequence, with
a real capture, after twenty other changes landed. That is why the
round-45 stranger, the round-63 walk, the round-77 controls, the
round-90 design review each found a class the suite could not: the
suite had no journey-shaped assertion. The remedy is not more
exploration; it is turning each exploration's *protocol* into a
guard with an answer key (`UX-402`'s shape), so the next walk starts
from what the last one already holds and spends its budget on what
moved. Exploration then has a job the suite cannot do — variation —
and a shape that keeps it cheap: a seeded scenario drawn from the
area tree and the input classes, a fixed report, a finding that
becomes a guard.

**2. A cheaper model is right for the driving and wrong for the
judging.** Round 90's advisory put reading and checking on `sonnet`;
a scripted walk (capture, export, drive one control per class, take
the census, diff against the answer key) is checking, and belongs
there — round 77's walk cost 336k tokens because it also *judged*
every control. The judgement (is this reasonable, is this the
guide's promise, what should the rule be) stays with the session's
model, on the walk's report rather than on the page. The cost target
is one row in the run ledger: a scripted walk under 100k, a
judgement under 50k.

**3. Tie exploration to the release, and make the release wait for
it.** A release is a contract state (`UX-251`); nothing today makes
it wait for a walk. The gate is mechanical: the release candidate is
the last commit that changed a contract, and a release is cut only
when a walk and a design review have run on or after that commit,
their reports are in the audits, and every finding they filed is
either closed or declined in the release notes. Cadence follows from
the contract changes, not from a calendar — a quiet month needs no
walk, a round that bumps `analyze` needs one before it ships.

**4. Impact analysis exists in pieces and is run by hand; derive it.**
The `decompose` skill's surfaces are derived by the touching map and
the selector; what a design-stage reader also needs — which contracts
a module emits, which findings it produces, which guides name it,
which styleguide sections cite it, which open filings sit on it — is
five greps in the `orient` skill. One tool runs them all and prints
the impact set for a filing or a diff, and the set is what the
filing's decomposition pastes. The hierarchical backlog the brief
asks for is the same index read the other way: not a new tree of
files (682 task files, guarded links, closed rows verbatim — a move
would cost a round and break the record) but an **area** field per
task, derived once from the files each closing commit touched and
kept by a guard, with generated area pages: modules, contracts,
guards, guides, open and closed tasks. Impact analysis then reads one
page.

**5. Do not restructure the specification; layer it. Restructure the
architecture document one area at a time.** The spec is frozen
outside Part 32 by rule, and its five edge decisions are taken
(`UX-564`..`UX-568`); a rewrite would re-open them for no reader. The layering already begun — the
Part 32 registry, the Part→guard index, the advisory-Parts note — is
what makes the spec navigable without moving a line. The
architecture document is different: its guarded skeletons are exact
and its prose drifts, and the area pages of correction 4 are where
each chapter's prose belongs — so the restructure is a *move per
area*, one track each under the `decompose` skill's merge rules,
never a rewrite, with the docs guards holding every link across the
move. Planned as a round of tracks, judged by one number: no
sentence lost (the round-82 review's method, run on the before and
after).

### What follows

Eight filings, `UX-685`..`UX-692`:

- **Exploration as a seeded scenario** (`UX-685`): `dev_scenario.py
  --seed N` draws area × input class × role and prints the scripted
  walk; the driving half runs on the reporters' model, the judging
  half on the session's, each a ledger row under a target; every
  finding adds a row to the journey's answer key in the same round.
- **The release waits for the walk** (`UX-686`): a third condition
  in the release guide, read by the derivation guard — a walk and a
  design review on or after the candidate commit, their findings
  closed or declined by name.
- **The impact set derived** (`UX-687`): one tool prints modules,
  contracts, findings, guides, styleguide sections, guards and open
  filings for a diff or an id; the decomposition pastes it.
- **Areas, as a view** (`UX-688`): an Area field derived from the
  closing commits, generated area pages, no file moved.
- **The architecture document moved one area at a time**
  (`UX-689`): the spec layered and left; the prose into the area
  pages under the merge rules, judged by no sentence lost.
- **A shape budget and a filed test analysis** (`UX-690`): the
  suite's purpose mix derived and bounded; a feature names its input
  classes and the journey it extends.
- **A flake ledger** (`UX-691`): excursions counted before they are
  called flakes.
- **The invariants for any shape** (`UX-692`): a seeded sweep over
  generated projects asserting I1-I13, determinism and the volume
  budget — the exploration nobody can do by hand, mechanised and
  cheap.

What the direction declines: a calendar cadence for exploration
(the contract change is the clock), a new tree of task files (the
area is a field and a generated page), and a specification rewrite
(layered, not moved).

## Direction 19: the gate holds the numbers; the review holds the design (argued 2026-09-05, round 93)

**Serves:** every implementing session, and R8 deciding whether a
change may land — the gate is the tool's, the review is the reader's.

**Status:** partial — the corrections are argued here; `UX-693`..`UX-703` are open.

The user's brief: static analysis and coverage exist, but no
refactoring cadence, so comments go stale and complexity grows; revise
the analysis rules; put more analysis on the GitHub gate — performance,
security, maintenance — without slowing the inner loop; a CodeQL skill
for navigation in place of several greps; quality metrics whose control
is delegated to tools, with review reserved for design; and a cheap
self-review skill against the guidelines that exist. Round 93 measured
the gate and the tree ([round 93](../audits/round-93.md)) and argues
six corrections.

### Six corrections

**1. The cadence is not missing; the measurement is.** Fixing guide
§6a already defines the refactor stream by "a measured cost — size,
duplication, a budget", and no refactor has ever been priced because
nothing writes the cost down. The gate runs one rule family
(`select = ["F"]`), under a comment that calls the tree "~30-module"
and promises to widen "in a later task" — 104 modules later, the
comment is the stalest one in the repository and the task never came.
Meanwhile 84 functions exceed McCabe 10, four files sit at
maintainability 0.00, and `format_text` is 548 lines at complexity
135. A calendar cadence would refactor what nobody measured; a
**ledger** — per-file complexity, longest function, file length,
suppressions, type errors, committed like `tests/ci_reference.json` and
ratcheted so a row may only shrink — makes the refactor stream what
§6a says it is: the top row, one track a round, judged by "the
measurement moved and no behaviour did". The renderers go first: the
golden snapshot is already the judge that no behaviour moved.

**2. Stale comments have a shape, and it is not the one the brief
guesses.** The census checked 1,585 backticked identifiers in comments
against the tree: 0 unresolved. A guard on identifiers would find
nothing — an instrument reading a proxy (§5). What has drifted is
**counts and promises** ("~30-module", "widen later") and **history**
(31 lines in `bga/` and `tools/` name a round; the register says the
story lives in the task file). The guard is the register's own rows:
no round number in code, a count in a comment dated or derived, and
the commit-body budget read from the pull request — three rows the
register states and nothing yet enforces.

**3. Three shelves, not one gate.** Every stronger tool tried finds
signal today's gate cannot see — 1,378 pyupgrade hits, 87 bandit-class,
270 pyright errors, 70 eslint problems — and none of it can become a
zero-tolerance gate in one commit. So the rule set grows on three
shelves: **auto-fixed** (pyupgrade, simplify, unused suppressions —
fixed in one commit, enforced from the next), **ratcheted** (complexity,
size, bandit-class, type errors — the ledger, may not grow), and
**gate-only** (CodeQL or its private-repo substitute, pip-audit against
a lockfile, Dependabot, secret scanning — hosted, minutes, never local).
The inner loop does not slow because it already runs the right tool:
`ruff` on the edited file in 10 ms, and the widened set rides the same
hook. Everything slower runs only on GitHub, and `make lint` stays what
it is. Per-file rules by layer, not per-line suppressions: `tools/`
prints by design (355 hits), `tests/` is not library code.

**4. CodeQL is a gate tool; navigation wants an index.** A CodeQL
database is a minutes-long build over 62k Python and 13k JS lines;
what a session asks while navigating — where is this defined, who
calls it, who imports this module, what does this module export that
nothing reads — is symbol-shaped and grep answers it in milliseconds.
The `orient` skill's five greps are slow only in **tokens**: each
returns raw lines the session then reads. One AST tool
(`dev_symbols.py`: definitions, callers, importers, fan-in/out,
unreferenced exports — Python and, via `dev_js_deps`, the viewer)
returns the answer as a table, and the five recipes become one
command. What grep cannot do — follow a log field through
`bst_native_build_tracer.py` to a `subprocess` call, or to the page —
is data-flow, which is CodeQL's job, at the gate, on GitHub, never in
a skill.

**5. Delegating control to tools is what `REVIEW.md` already asks
for — so the review shrinks as the gate grows.** Its "do not report"
rule excludes anything `make lint` enforces; every rule the gate holds
is a pass the review no longer runs. The metrics are the ledger's
columns, few and per-file, so a refactor track can be priced and a
review can say "the ledger row grew" instead of "this feels long".
What stays with a reader is routed, not chosen: a diff whose impact
set (`UX-687`) touches a contract, a spec Part, a hook or a skill gets
the design review; a diff that touches nothing of the kind gets the
self-review and the gate.

**6. The self-review is the existing policy on the diff, on the
reporters' model — not a second checklist.** `REVIEW.md` has four
passes and a finding shape; the rules card has the rules; two lists
drift. The skill reads the diff, the task file and those two documents,
returns findings in `REVIEW.md`'s shape, never re-reports what the gate
holds, and costs one row in the run ledger — target under 40k tokens.
The session's model then reads a report, not a diff.

### What the brief forgot

Dependencies are unpinned (`>=` throughout) and there is no lockfile,
so `pip-audit` has nothing honest to read; the viewer has never been
linted (5 exports referenced nowhere); no benchmark guards `UX-531`'s
superlinear analyzer; `falsify` is a hand ritual a mutation run could
mechanise on the touched modules; duplication is unmeasured; and the
gate's own tool versions float (`ruff>=0.6`), so a rule set that holds
today can change under the same configuration tomorrow.

### What follows

`UX-693` the rule set widened by layer, in one auto-fix commit, tools
pinned (High) · `UX-694` the quality ledger, ratcheted like the CI
reference (High) · `UX-695` the refactor stream takes the ledger's top
row, renderers first (Medium) · `UX-696` the register's unguarded rows:
no round in code, dated counts, the commit body (Medium) · `UX-697` a
type-error ratchet, contracts first (Medium) · `UX-698` the gate-only
shelf on GitHub: code scanning, a lockfile and audit, Dependabot,
secret scanning (High) · `UX-699` the viewer linted as one module graph
(Medium) · `UX-700` the symbol index, and CodeQL declined for
navigation (High) · `UX-701` the `self-review` skill (High) · `UX-702`
a performance ratchet at the gate (Medium) · `UX-703` a mutation run on
the touched modules, weekly (Low).

## Round history

This document used to carry the findings of rounds 2-6 inline, which
made it an argument about direction *and* a changelog. They live with
the other rounds now:

| round | what it found |
|---|---|
| [2](../audits/round-2.md) | scale probe — the tool at 1200 elements |
| [3](../audits/round-3.md) | cross-checking quantities that ought to agree, and did not |
| [4](../audits/round-4.md) | the plane seam, settled by measurement |
| [5](../audits/round-5.md) | the structural plane against a real project's graph |
| [6](../audits/round-6.md) | every real CI build is incremental |
| [7](../audits/round-7.md) | plus the planning notes this document used to carry |
| [8](../audits/round-8.md) | element attribution, 14.9% -> 86.1% |
| [9](../audits/round-9.md) | the first real freedesktop-sdk capture |
| [10](../audits/round-10.md) | both usage scenarios walked end to end |
| [11](../audits/round-11.md) | round 10's fixes re-verified; verification discipline is where the defects were |
| [12](../audits/round-12.md) | directions 3-4 re-verified; the MVP verdict: met |
| [13](../audits/round-13.md) | round 12's fixes re-verified; the polish direction opened (`UX-125`..`UX-127`) |
| [14](../audits/round-14.md) | the polish verified as a user; the docs read as a stranger (`UX-135`..`UX-145`) |
| [15](../audits/round-15.md) | a real field failure the tool cannot see; the diagnosability chain filed and the fix claims re-verified (`UX-147`..`UX-154`) |
| [16](../audits/round-16.md) | the tool meets a big project: a failed build verdicts IMPROVED, Ctrl-C destroys the trace, auto-spine bills every nested layout (`UX-156`..`UX-162`) |
| [17](../audits/round-17.md) | all eight round-16 landings verified live and holding; the new findings are seams between verified features (`UX-163`..`UX-168`, plus `UX-169` from fixing them) |
| [18](../audits/round-18.md) | every measured number reproduced exactly — the clean audit's tail is guards weaker than their prose; Direction 6 opened from the user's monorepo question (`UX-171`..`UX-177`) |
| [19](../audits/round-19.md) | the source axis landed and met its own output: the printed identity does not round-trip, and one guard passes with its sorter reverted (`UX-178`..`UX-182`) |
| [20](../audits/round-20.md) | the field speaks: nine usage observations ground-truthed into ten filings, and the elision that reopened the round-trip (`UX-183`..`UX-192`) |
| [21](../audits/round-21.md) | all ten field landings verified holding; Direction 7 argued — the viewer as a thin window onto the JSON, timelines to Perfetto (`UX-193`..`UX-197`) |
| [22](../audits/round-22.md) | the viewer landing verified; the field and an external review synthesized into Direction 7's second iteration, plus two shipped views nobody can reach (`UX-198`..`UX-206`) |
| [23](../audits/round-23.md) | eight of nine round-22 landings hold; the ninth's guards only guard one machine. A second external review's Pareto turn adopted — decision first, everything an action — and its blind spots filed with it (`UX-207`..`UX-214`) |
| [24](../audits/round-24.md) | the relationship layer the third external review asked for is already computed in `correlate.py` and published nowhere; round 23's own Inspect anchors resolve to nothing; three of the review's premises corrected, and the loop it did not look at filed (`UX-215`..`UX-226`) |
| 25 | round 24's first four executed: `correlate/v1` published and the viewer drew it with no change; the dead anchors resolve; findings show their evidence; the next command is published rather than derived. The page-size ceiling stopped being a number and became a ratio (`UX-215`..`UX-218`) |
| 26 | round 24's remaining eight executed: the schema learned to say what its numbers mean, `compare/v1` learned which elements changed, the store learned to remember one, and the page learned to draw a plan, focus one element and carry the reader's own marks in the link. Two task premises corrected and two mutations rejected for not discriminating (`UX-219`..`UX-226`) |
| [27](../audits/round-27.md) | twenty for twenty on the eighteen-commit landing, two hollow guards filed. The role model written: four roles served, four unserved; Direction 8 (provenance) adopted from the fourth review, its workspace declined; Direction 9 (the team axis) opened from the user's positioning (`UX-227`..`UX-235`) |
| 28-39 | the sibling's execution rounds: UX-236..295 landed, Directions 10-14 argued — recorded in each direction's section and the backlog's round sections rather than as audit files |
| [40](../audits/round-40.md) | the field's first architectural showstopper: a 2 GB dual-plane snapshot OOMs `bga view` — every load path measured, ~95 % of the monolith unread, the streaming fix on the wrong path; Direction 15 argued (events as a Perfetto TrackEvent stream, capture computes / view serves) and the rounds 28-39 sample verified six for six (`UX-296`..`UX-301`) |
| [41](../audits/round-41.md) | a design round while Direction 15 executes: the user's brainstorm became the visual contract (`styleguide.md`) — shape→control mapping, sparklines and density strips, a measured-and-budgeted palette (two validator failures found), dark first with print kept honest (`UX-302`..`UX-306`, Direction 16) |
| [43](../audits/round-43.md) | Direction 15 and the visual contract verified eleven for eleven, fourteen mutations discriminating; then the user's question answered by inventory — the trace speaks Perfetto's format and none of its vocabulary, while the capture holds the content for all of it (`UX-308`..`UX-312`, Direction 15's second iteration) |
| [44](../audits/round-44.md) | the trace vocabulary verified seven for seven with one dead question surviving its own class's purge; the user's thirteen readability observations became four visual-contract sections — drawing grades, apparatus placement, the depth budget and table focus, the click budget (`UX-316`..`UX-321`) |
| [45](../audits/round-45.md) | the guides walked by a stranger: four bugs forty-four feature rounds never saw — the no-bst traceback, the user-install crash, the self-crashing printed command, the ghost invocations — plus the round-44 landing verified with one cascade evasion (`UX-324`..`UX-332`) |
| [46](../audits/round-46.md) | three field errors measured to mechanisms — the trim that interns 3,000 compiles to two names, the CSP that silently breaks tick labels on served pages, the TypeError that was never bga's — and the implementation loop re-tooled with a measured 2.5× (`UX-333`..`UX-336`) |
| [63](../audits/round-63.md) | seventeen implementation rounds (47-62) recorded in the backlog's own sections, then the sibling's outsider walk run twice: six populations vanish between a cold and an incremental run, fourteen Plane 2 blocks reach no browser, and the Tabulator question filed as a product decision (`UX-388`..`UX-397`) |
| [64](../audits/round-64.md) | the walk that judged the answers: against example 06's `optimized/` answer key, Plane 2 names every intended fix and correlate compresses them into one 12.9 s paragraph that reaches no page; the rounds 47-63 landing held eleven-of-twelve under falsification; the library question answered with a factory measurement, and the test plan built from the escape ledger (`UX-398`..`UX-410`) |
| [64 · the guard census](../audits/guard-census-round-64.md) | the falsify ritual run as a sweep rather than the per-round sample it had been since round 18: eleven guard families, one mechanism-revert mutation each, so that a family with no discriminating guard is found rather than a file (`UX-403`) |
| [72 · the planted-defect walk](../audits/planted-defect-walk-round-72.md) | three defects **chosen first**, generated into real BuildStream projects with `tools/bga_gen_project.py` and built by a real `bst`, recording how far the front door gets each reader towards the answer that was planted (`UX-468`) |
| [74](../audits/round-74.md) | rounds 65-73 reviewed as a workflow and measured — a 5m30s suite gated per item, 60 KB read before every task file, Outcomes at a median 114 lines, 12 % of commits housekeeping; a Register section and its guard, the `decompose` and `orient` skills landed, and the lifecycle's remaining steps filed (`UX-497`..`UX-506`) |
| [75](../audits/round-75.md) | the round-74 slate closed under its own decomposition — three implementer tracks in worktrees (943-1,174 s, 81k-131k tokens each), `UX-500`'s first count (Regime A: 15 suite runs, two misses outside the selector's set), the rules card, the derived index, the self-recording CI reference (`UX-500`..`UX-510`) |
| [76](../audits/round-76.md) | the tail closed, and `main` found red from CI's own adopt commit — the batch gate cannot assume a green base (`UX-511`..`UX-517`) |
| [77](../audits/round-77.md) | three field reports about waiting, measured and filed — the `bst show` tail on big projects, a run bundle to carry, a Perfetto button silent for minutes (`UX-518`..`UX-521`) |
| [78](../audits/round-78.md) | the three field reports implemented under a decomposition, everything shipping in the bundle by default (`UX-518`..`UX-521` closed) |
| [79](../audits/round-79.md) | the controls walked on a two-plane page (782 in 193 classes): the "All rows" table is nested rows migrating into their parent; the served page is the capture-time analysis; the volume budget breached at the top of its own class; the suite weighed — forty browser files are half its seconds (`UX-522`..`UX-536`) |
| [80](../audits/round-80.md) | the round-79 slate closed in six worktree tracks: `UX-500`'s second regime measured and refused — **4 of 9** defects the batch gate caught were outside `test-touching`'s set, so fixing guide §3 stays; a run bundle you can carry, `analyze/v5`, the export's data half bounded and compacted, and three cross-track collisions only a merge could see (`UX-514`, `UX-516`..`UX-539`, `UX-92`) |
| [81](../audits/round-81.md) | twenty-two rows, seven premises falsified by measuring — the drift gate's cause filter, a stale base under both tracks, the suite line that was not the run's (`UX-538`..`UX-562`) |
| [82](../audits/round-82.md) | every document read against the tool by five researchers: a sentence a guard reads is exact, a sentence no guard reads has drifted — twenty-four filings asking for derivation and dating, and the `review` skill (`UX-563`..`UX-586`) |
| [83](../audits/round-83.md) | round 82's twenty-four rows executed, most of them not "correct a sentence" but "give the sentence a guard and let the correction follow" — the `UX-549` shape (a figure the guard derives) and the `UX-511` shape (a block labelled with its date and its cuts), extended to where round 82 found them missing (`UX-563`..`UX-586`) |
| [84](../audits/round-84.md) | the fifteen rows round 83 filed rather than fixed, seven tracks wide — and the round where a filed premise is re-measured before it is implemented, because `UX-589`'s was false and `UX-592` had already refuted it (`UX-589`..`UX-604`) |
| [85](../audits/round-85.md) | the rows round 84 left, plus the seven the round filed against its own work and six from architecture review 15 — and the round where a premise **carried forward** is a sentence again: seven of nineteen moved under re-measurement, five of them written by the orchestrating session from another track's report (`UX-604`..`UX-627`) |
| [86](../audits/round-86.md) | the rows round 85 left and the three this round filed — and the round where every item turned out to be one shape: **a guard's population is bounded by a rule somebody typed**, and where that rule is wider than the claim the guard goes quiet rather than failing. Six of eight, plus the session's own undeclared skip reason (`UX-597`..`UX-635`) |
| [87](../audits/round-87.md) | the `bga view` walk that began with pressing Expand twice — four tracks on disjoint modules, and the round where **three of six filings were corrected by the measurement that implemented them**: `UX-638`'s mechanism needed a scroll inside focus, `UX-640`'s not-a-defect held only where the listener runs, `UX-642`'s broken population was the smaller half. All three shared-value merge hazards fired and each merged cleanly into a wrong number (`UX-638`..`UX-649`) |
| [88](../audits/round-88.md) | round 87's eight open rows, five tracks wide, plus the review the cadence guard called due — and the round where **four rows were closed by disproving their own premise**, three of them the orchestrating session's: settling was not the geometry gap, the shallow-clone sweep was already closed, the reader map was derivable, and nine page-built sections were thirteen (`UX-636`..`UX-656`) |
| [89](../audits/round-89.md) | round 88's five open rows in three parallel tracks, and the round where **every closed row was the same defect at a different scale**: a fact written twice, one copy guarded and exact, the other drifted — plus three more found while working, one of them two rows round 88 wrote by hand (`UX-651`..`UX-659`) |
| [90](../audits/round-90.md) | the process given a ledger — reporters on `sonnet`, the walk and the design review as skills, a run ledger — and the page looked at through seven screenshots: the rail as a source list, a reader as a shape not a hue, a runbook as a shape, a rail click that overshoots (`UX-663`..`UX-674`) |
| [91](../audits/round-91.md) | a design round: whose question utilization is — the tool counts processes where the CI owner needs cores, computes idle intervals it never publishes, exempts foundations by kind so a toolchain is not exempt, and has no change frequency; Direction 17 argues the envelope, the jobserver, priced remote execution and expected rebuild cost (`UX-675`..`UX-684`) |
| [92](../audits/round-92.md) | a design round on the test workflow: the suite verifies what was built and the walk what was promised — exploration as a seeded scenario that grows the answer key, a release that waits for the walk, the impact set derived, areas as a view, the architecture prose moved one area at a time, a shape budget, a flake ledger, the invariants for any shape (`UX-685`..`UX-692`) |
| [93](../audits/round-93.md) | a design round on the development workflow: the gate holds the numbers and the review holds the design — the rule set widened by layer and pinned, a ratcheted quality ledger that queues the refactor stream, the register's unguarded rows, a type ratchet, a gate-only shelf on GitHub, the viewer linted, an AST symbol index in place of CodeQL for navigation, a `self-review` skill, a performance ratchet, a weekly mutation run (`UX-693`..`UX-703`) |

## Verification Log

Written 2026-08-16 from a real session: BuildStream 2.7.0 with
`buildstream-plugins`, real `bwrap` sandboxes, real `gcc 13`/`cmake 3.28`
staged by `examples/stage_cpp_toolchain.sh`, on a 4-core / 16GB Linux
host. Every number quoted is from a real build and a real `bga`
invocation in that session, recorded in
[`case-study-06-macro-micro.md`](../audits/case-study-06-macro-micro.md); every
claim about what the code does was checked against the source rather than
inferred from output. The proposed report and CI-comment layouts are
illustrations of intent, not implemented output.

## Direction 10: releases as contract states (argued 2026-08-24, round 30)

**Serves:** R4 and R8 — the two who pin something and need to know
when it moved — and, through the store, R1 and R7, whose questions are
answered by comparing this build against builds an *older* `bga`
measured.

**Status:** landed — `CHANGELOG.md`, three release rows, the generated body, `UX-241`'s review gate, and the tags. `UX-597` cut `v0.3.0` and `v0.4.0` and a guard reads them; `UX-634` made step 8 publish the release rather than only tag it; `UX-633` turned out to be no defect at all — all three tags are ordinary release tags, and the row that said otherwise was read off a truncated history, which its own file now records.

`bga` is unusual among analysis tools in one way that matters here:
**it reads its own past output as input.** `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate` — every one of them
opens artifacts written by whatever `bga` was installed at the time,
which on a project six months old is not the one running now.

Measured today:

```text
bga --version                      0.1.0     (unmoved across 29 rounds)
git tag                            0 tags
CHANGELOG                          none
published contracts                9, every one at /v1, never bumped
artifacts recording their producer  0
```

`__version__` is read in exactly one place — the `--version` string.
It is written into nothing. A `run-context.json` from round 3 and one
from round 29 are indistinguishable to the tool that reads them both.

### The gap is a missing comparability dimension, not a missing number

This repository is already strict about comparability, and strict in
the right way: `bga compare` **refuses** two runs from different hosts
(`UX-186`) and refuses a caches-off run against a caches-on one, with
an exit code of its own rather than a caveat, because "these are not
comparable" and "these are comparable and equal" must not look alike.

Producer identity is the same kind of dimension and it is simply
absent. If a later `bga` re-buckets an attribution category, renames a
finding id, or changes how a percentile is taken, the aggregate over a
year of stored runs silently mixes two definitions — and every existing
refusal would pass it, because the host is the same and the mode is the
same. That is the exact defect class the refusals exist to prevent,
on the one axis nothing watches.

So the first move is not a release process. It is: **an artifact says
what produced it.**

### Why the version must be derived from contracts, and what it is *not* for

The user's instinct — base it on contract breakage or extension — is
right, and it is right because this repository already has the
contracts enumerated: nine schema ids, a CLI surface, a run-directory
layout. A release does not need to invent a compatibility story; it
needs to *record the one already implied* by those.

The trap is making a single package number the load-bearing thing. It
is a lossy summary of nine independent contracts: `whatif/v1 → v2`
tells an `analyze/v1` consumer nothing, and if the package version were
what they pinned, a break in a document they never read would look
identical to one in the document they do. So:

| level | answers | moves when |
|---|---|---|
| **contract version** (`analyze/v1`) | can my parser read this document? | that document breaks |
| **package version** (`bga 0.3.0`) | which build produced this artifact? | every release |
| **the release row** | which contract states shipped together? | every release |

**The package version's job inside an artifact is provenance, not
compatibility.** Compatibility is decided per contract, against the
contract set the artifact itself recorded. That is stricter *and*
looser than a version comparison in exactly the right places: two runs
from `0.1.0` and `0.9.0` still compare if every contract they touch is
unchanged, and two runs one patch apart refuse if one of them isn't.

The version number is then *derived*, not chosen: the contract set at
the last release row against the contract set now decides whether this
is a break, an extension, or neither. A guard checks the derivation,
because a version somebody picked by feel is a number with no meaning
and this repository has spent twenty-nine rounds refusing those.

### Where the release process should *not* go

Two arguments against parts of the obvious design, both from what this
repository has already measured.

**A release must not become a second trigger for documentation review.**
`UX-241` landed a review cadence one round ago: a stream, a checklist,
and a guard that reddens past 25 closed rows. Adding "and also sweep
the docs at release time" would create two mechanisms racing for one
job — and *two hand-maintained copies of one fact drifting apart* is
the single most-repeated defect in this backlog's history. The release
should **consume** the review, not duplicate it: a release may only be
cut when a review row exists at or after the previous release, and that
review's findings are the release's documentation work. This makes the
release cheaper, not richer, and keeps one answer to "when do we
sweep".

**The cadence must not be time-based.** There are no external consumers
yet and nothing to deploy; a monthly release would be ceremony
generating no information. The trigger is contract movement and a
current review — both measurable, both already in the tree.

### What a release is, then

Five things, of which four are mechanical:

1. a row in `CHANGELOG.md` with the contract set, the closed-row
   marker, and the commit;
2. a version derived from the contract delta and checked by a guard;
3. a review row at or after the previous release (guard);
4. notes whose **body is generated** from the closed rows since the
   last marker — the narrative already exists there and a hand-written
   third copy would drift — and whose **head is written**: the theme,
   the contract delta, and what a consumer has to do about it;
5. a tag.

The one genuinely new piece of writing per release is item 4's head,
which is a paragraph. Everything else is derivation.

### What this does *not* fix

The staleness the user names is real, and a release does not cure it —
`UX-241`'s review does, and the release only refuses to proceed without
one. Saying otherwise would be the second-trigger mistake wearing a
different hat. What the release adds is the *changelog*: 3,549 lines of
audit rounds and 789 lines of closed rows currently hold the "what
landed" story, and no document answers "what changed between the thing
I installed and the thing I have now" at all.

## Direction 11: a ranking answers "what should I do", not "what is big" (argued 2026-08-24, round 32)

**Serves:** R1 and R3 first — the optimizer deciding where to spend a
day, and the graph owner who knows which of those choices the graph
forbids — and R8, who is handed the ranking as a case for funding.

**Status:** landed — the ranking (`UX-260`, `UX-303`), and every `yes` row in the table below both publishing a distribution and declaring `bga:distribution` (`UX-598`), which the note under that table derives.

The report ranks elements by blast radius and tells the reader to fix
the top one. Measured on a 1,202-element run:

```text
next_steps[0]: "toolchain.bst is the first thing to fix - this is what
                changing it rebuilds."

toolchain.bst   downstream_count 1201   element_kind "import"
                is_structural_kind TRUE
```

The advice is *true* and *useless*. A base image, a toolchain, a
`host_strip_tool` has a thousand dependents **on purpose**; that is
what makes it a base image. Telling someone to optimize it is telling
them their graph is a graph.

And the tool already knows. `is_structural_kind` is computed and
published on the very entry it ranks first. `bga/findings.py` even
applies the right rule one function away — `_criticality_findings`
excludes structural kinds outright, citing `UX-76`:

> *"structural elements are excluded rather than annotated here"*

The blast ranking simply never got the same treatment.

### The deeper problem: a number with no scale

Even among the non-structural entries, the ranking implies a precision
it does not have. The measured distribution of downstream counts:

```text
p10    0      p60     66      p95    575
p20    1      p70    157      p99    682
p30    4      p80    293      p100  1201
p40   10      p90    465
p50   30
```

Positions 2 through 12 run 753, 753, 739, 727, 721, 720, 712, 709,
706, 702, 697 — an 8% spread across eleven elements, presented as an
ordered list of what to do first. The honest statement is *"these
eleven are all in the top percentile and are indistinguishable"*, and
the way to say it is to publish the **distribution** rather than the
rank.

A percentile answers the question the raw count cannot: *is 753 a lot?*
It is p99.9 here and would be unremarkable in a graph of forty
thousand. The number travels; the rank does not.

### Where percentiles belong, and where they do not

The rule that decides: **a percentile helps when a reader cannot know
the scale, and the population is comparable.** Blast radius qualifies —
every element is a member and the counts span three orders of
magnitude. Applying it everywhere would be cargo cult:

| quantity | key | percentile? | why |
|---|---|---|---|
| blast radius (downstream count) | `blast_radius` | **yes** | three orders of magnitude, every element a member, no intuition for the scale |
| element duration | `element_duration` | **yes** | the same shape; "is 40s slow here?" has no answer without the distribution |
| share of the critical path | `share_of_critical_path` | **no** | already a percentage of a known whole — a percentile of a percentage is a second scale for one fact |
| sandbox tax (Plane 3) | `sandbox_tax` | **yes**, per element | the useful question is "is this element's tax unusual", which is exactly a percentile |
| processes per element (Plane 2) | `process_count` | **yes** | heavy tails; one element with 40,000 processes is the finding |
| confidence, coverage, efficiency | `confidence`, `coverage`, `efficiency_score` | **no** | single run-level numbers with no population to be a percentile of |

The `key` column is the entry in `DISTRIBUTED_QUANTITIES` or
`UNDISTRIBUTED_QUANTITIES` (`bga/analyzer.py`), where the split is
recorded with an argument per row; the `percentile?` cell is that
membership, and `test_the_percentile_rows_are_the_published_ones.py`
derives one from the other rather than letting a reader compare them.

**All four `yes` rows publish a distribution — re-measured round 84,
2026-09-03.** `UX-581` dated an earlier count that read
`bga/schemas.py` as a proxy for what publishes one; two of the four are
emitted by `bga/correlate.py` into `correlate/v2` instead, and the grep
could not see them:

```text
$ python3 -c "from bga.correlate import _scale_of; print(sorted(_scale_of(payers, native)))"
['process_count_distribution', 'sandbox_tax_distribution']
$ git grep -n "_distribution(" bga/schemas.py        element_duration, blast_radius
```

What `UX-598` found was the other half: those two published keys were
declared by nothing, so every percentile inside them reached the reader
as a bare number — `UX-343`'s defect. Both now carry `bga:distribution`
in `_CORRELATE_HINTS`.

Deciles are the right granularity: ten buckets is a shape a reader
takes in at a glance, and finer only matters in the tail — where the
named p95/p99 already carry it.

### What the first view should rank instead

The presentation follows from the same argument. "Biggest" is not a
rubric; these are:

- **Longest on the critical path** — what the build is actually waiting
  for, which is already computed and is the honest first answer.
- **Blast radius density** — not one element's count but the *shape*:
  half the elements here reach 30 or fewer, the top decile reaches 465
  or more. A graph where one element reaches everything is a different
  problem from one where a hundred do, and the reader deserves to know
  which they have before being handed a list.
- **Unusual for its kind** — the outlier, which is what "worth
  optimizing" actually means once the structural entries are set aside.

### What this does not change

No number moves. Structural elements stay in the payload, stay
reachable, and stay *reported* — `UX-203` was filed because views were
unreachable, and answering this by hiding them would trade one defect
for an older one. What changes is that they are reported as **the
graph's shape** rather than ranked as **the reader's next task**.

## Direction 12: the report is read, not decoded (argued 2026-08-24, round 35)

**Serves:** R1 first, and R3 — the two who open the page rather than the
JSON.

**Status:** landed — `UX-263`..`UX-272`.

Reported from a real run, in nine parts. Every number below was
measured on a served report in Chrome 141, not estimated.

### What is actually wrong

Two of the three pages `bga view` serves **ran nothing at all**:

```text
                   CSP violations   main children   body text
index.html                      0              26      11,056
sql.html                        1               0         508
perfetto.html                   1               4         398
```

`default-src 'self'` refuses inline **script** exactly as it refuses
inline style, and `sql.html` and `perfetto.html` each carried one.
`UX-263` fixed the style half and checked `index.html` only. That is
`UX-266`, and it is fixed.

The rest is one line of code. Every object and every array that is not
an array-of-objects renders as:

```js
el("details", {}, el("summary", {}, "object"),
   el("pre", {}, JSON.stringify(value, null, 2)))
```

A summary that says `object` and a wall of raw JSON behind it. On a
44-element run that is **34 such cells and 32,393 characters** of
`<pre>`, the largest 8,191. It explains four separate complaints at
once: clicking every object to find out what it is, JSON-as-string,
unreadable arrays, and nothing searchable or bounded.

### Where the reader's diagnosis is right, and where it is not

**Right, and under-stated:** the collapsed-object problem. The reader
called it *"quite inconvenient and puzzling"*; measured, one of those
cells at 1,202 elements is ~224,000 characters behind a label that says
nothing.

**Right:** small objects belong inline as table cells, long ones behind
a fixed height with a scroll and a search. Both are what a spike
measured as best; the spike also found the trap — unfolding everything
into tables took the document from 13.8 screens to **35.5**, and
bounding rows got it only to 32.3. The fold is not the enemy. A
summary reading `object` is. Keeping the fold and labelling it
`Blast radius · 44 entries` gave zero raw JSON at 14.9 screens.

**Challenged — depth is not the problem.** The proposal was to analyse
JSON depth and choose representations by it. Measured, the document is
7 levels deep and only **three nodes** live at level 7:

```text
depth   0    1    2    3    4    5   6  7
nodes   1   19  129  500  794  229  88  3
```

The mass is at 3–4 and the pain is at **level 2**: maps with one key
per element. A depth rule would fix almost nothing; a **width** rule
fixes all of it. That is `UX-267`.

**Challenged — a third column is the wrong shape.** A navigation column
carrying the JSON structure would make the *document's shape* the
organising principle, which is precisely what `UX-207` and `UX-199`
moved away from: the page answers questions, and a JSON tree is a data
browser. At 1440px a third column also leaves under 900px of reading
width, undoing `UX-254`. The need behind the request is real — the rail
is flat and the page is 30+ sections — so the answer is to make the
**existing** rail two levels deep, not to add a column. That is
`UX-271`.

**Challenged — the header is not where the space goes.** Measured at
1440x900 it is 92–184px, **0.1–0.2 screens** of a 13–15 screen
document. Moving the actions right is cheap and worth doing, and it
will not make the report meaningfully shorter; the honest framing is
tidiness, not space. That is `UX-272`.

### What nobody asked for and matters most

Six of the seven wide maps in `signals` are **the same element list**
seen through different fields — `blast_radius`, `slack`,
`element_durations`, `downstream_count`, `criticality_probability`,
`unweighted_depth`, all keyed by element UID, all 44 keys here and
1,202 on a real run. They are one table with six columns, rendered six
times as six opaque blobs.

The seventh, `wall_clock_share`, is keyed by **task** —
`app.bst|BUILD|BUILD|0` — and shares *zero* keys with the other six.
Nothing on the page says so, and a reader comparing them is comparing
different populations. That is `UX-268`, and it is the largest single
readability win available.

## Direction 13: the report has 48 fragments and no chapters (argued 2026-08-24, round 38)

**Serves:** R1 first, and R7 — the two who read the page top to bottom
before they know what they are looking for.

**Status:** landed — `UX-284`..`UX-286`.

Proposed from a real reading: *"maybe we need to review our data and try
to group it into semantic blocks that should occupy exactly one screen?
and transform our navigation pattern into going through several
screens?"*

Two ideas in one sentence. **The first is right and the measurement is
stronger than the argument for it. The second is refuted by the same
measurement**, and separating them is the whole of this direction.

### What the page actually is

Measured at 1440×900 in Chrome 141, on the 1,202-element synthetic run
(`bga gen-synthetic --seed 1`) and on the committed `macro_micro`
fixture:

```text
                              1,202-element     macro_micro
sections                                48              39
document                          18.8 scr        20.1 scr
median section                    0.24 scr        0.35 scr
smallest                          0.07 scr        0.07 scr
largest                     1.98 (findings) 3.42 (findings)

sections within 0.8–1.0 screens          0 (0%)          0 (0%)
sections under 0.8 screens              46 (95%)        37 (94%)
sections over one screen                 2 (4%)          2 (5%)
```

The median section is **0.24 screens — 216 pixels**. Not one section on
either run is near a screen tall. The report is not a sequence of
chapters; it is **48 fragments averaging a fifth of a screen**, read by
scrolling past them.

That is the defect the proposal is reacting to, and naming it that way
is worth more than the nine items round 38 filed against symptoms of it.

### Why "exactly one screen" is the wrong fix, measured

Padding each section to a screen does not reduce scrolling — it
multiplies it:

```text
document today                    18.8 scr        20.1 scr
document at one screen/section    48.0 scr        39.0 scr
padding introduced               +31.3 scr       +20.5 scr
```

A **2.6× longer document**, made of whitespace. The reader who found 48
fragments tiring would find 48 screens worse.

And a fixed cell cannot hold this content. Section height spans **0.07
to 3.42 screens — a 49× range** — because the tall ones are tall for a
reason a design cannot overrule: `findings` holds one row per finding,
`signals` one row per element. Ten sections on each run size themselves
from the run rather than from the layout. A one-screen grid has exactly
two options for a table of 1,202 rows, and both are wrong: overflow the
cell, or hide rows the reader came for.

### What the grouping half buys, and what it must not cost

Group the 48 into a small number of **chapters**, each answering one
question a reader actually has — the shape `UX-207`'s decision screen
already proves works, and `UX-271`'s rail already gestures at with one
level of nesting. Then `UX-285`'s finding stops being a placement bug
and becomes a chapter boundary: the three identity blocks are one
chapter, and it belongs at the end.

Navigation then moves **chapter to chapter**, which is the reader's
instinct in the proposal at the granularity the content supports — six
to eight destinations instead of 48, with ordinary scrolling inside
each.

Three things the page must keep, and each one refuses **pagination** as
the mechanism:

1. **`Ctrl-F` finds everything.** `UX-195`'s export is "the report you
   can attach"; a reader who has been sent one searches it. Content
   behind a page that has not been rendered is content the browser
   cannot find, and no in-page search substitutes for the one every
   reader already knows.
2. **A link opens what it names.** `UX-211` puts view state in the
   fragment and `UX-225` puts the working set in the link. A paginated
   deck needs its own page coordinate, which is a second navigation
   model layered on the one that already works.
3. **It prints, and it reads aloud.** A ticket attachment gets printed
   and pasted into slides; a document is one flow and a deck is not.

So: **chapters, not slides.** Grouping is a change to the document's
structure; pagination is a change to its medium, and the medium is
load-bearing.

### The challenge to the proposal, stated plainly

The proposal's premise is that sections are too big to take in. Measured,
they are the opposite — 95% are under four-fifths of a screen and the
median is a fifth. The tiring part is not the size of each block; it is
**how many of them there are and that nothing groups them**. A fix aimed
at block size would have made the report longer while leaving the count
untouched.

The second challenge is that "exactly one screen" is unmeasurable on a
page whose content is set by the run. `bga` reports 11-element and
1,202-element builds through one renderer; any fixed geometry has to be
wrong for one of them. The bound this repository already uses —
`UX-187`'s cap and `UX-262`'s `Top N` — bounds *rows*, which is a
property of the data, rather than pixels, which is a property of a
window that varies by reader.

### What follows

Grouping is filed as its own item rather than argued further here.
`UX-285` (identity blocks, blast placement) is its first instance, and
`UX-284` (tools above their table) is the affordance that makes a long
chapter usable. What none of them settle is what the chapters *are* —
that is a decision about the report's argument, not its markup, and it
wants the reader's questions in front of it rather than the section list.

**Settled by `UX-286`** (round 39): seven chapters, each named for a
question the reader has, with the sections whose published
`bga:question` is a spelling of that question. The reader's questions
were in front of it after all — the schema had been publishing them
since `UX-209`. Measured after: the document is 18.10 screens where it
was 18.51, so the grouping cost no height, and `UX-285`'s placement
passes became chapter boundaries and were deleted.

## Direction 14: the same elements, drawn nineteen times (argued 2026-08-24, round 39)

**Serves:** R1 and R7 first — and every open viewer item, because most
of them get smaller if this lands first.

**Status:** landed — `UX-288` then `UX-289`, in that order; brainstorm items 5-7 are marked there as unmeasured proposals, not commitments.

Proposed from a real reading: *"we have critical path shown three times
with a slightly different set of columns, and one time in form of
blocks. There definitely other duplications … almost all current open
tasks can be made significantly easier if we firstly deduplicate
information, then think of making tables with presets for default
filters."*

Measured, and the proposal understates it.

### What the page draws

On the 1,202-element synthetic run, every table that names elements,
with its column count and the set of element uids it holds:

```text
19 tables name elements.  They draw 13 distinct populations.

overlap  shared  A                                    B
   100%      14  signals/critical_path         [2c]   critical_path_detail  [5c]
   100%     135  signals/leaf_analysis         [8c]   signals/value         [2c]
   100%     135  signals/leaf_analysis         [8c]   signals/value         [4c]
   100%     135  signals/leaf_analysis         [8c]   structural/deferrability [6c]
   100%     135  signals/value                 [2c]   signals/value         [4c]
   100%     135  signals/value                 [2c]   structural/deferrability [6c]
   100%     135  signals/value                 [4c]   structural/deferrability [6c]
    94%     127  signals/leaf_analysis         [8c]   structural/value      [2c]
```

The critical path is two tables of the same fourteen elements, plus the
drawing — the reported three. **The leaf population is worse: 135
elements, drawn four times, every pair at 100% overlap.**

### Where the duplication actually is

Not in the page. In the contract:

```text
signals.leaf_analysis.leaves                    135 uids
signals.leaf_analysis.leaves_detail             135 uids   identical to leaves: True
structural.deferrability.{deferrable,non_}      135 uids   identical to leaves: True

signals.critical_path                            14 uids
signals.critical_path_detail                     14 uids   identical: True

signals.element_durations                     1,202 uids
   critical path is a subset of it:  True
   leaves       is a subset of it:  True
```

`analyze/v1` publishes the **same element membership three times** for
leaves and twice for the critical path, and every one of those
populations is a subset of the one 1,202-row element table. The page is
faithful; it renders every copy it is given.

**Corrected after this was first written.** Two of the three are exact
duplicates and the third is not:

```text
leaf_analysis.leaves == keys(leaves_detail)                    True
signals.critical_path == uids of critical_path_detail          True  (order too)
deferrability's lists derivable from a published field          False
```

`structural.deferrability` splits the leaves by a **duration-risk rule**
(under a second is deferrable), which is different information from
`leaves_detail.is_potentially_deferrable`, a graph fact. On the
1,202-element run the two disagree by design: 8 against 134. So the
partition is real and only the *membership* is the third copy.

Worse, the field that would make the lists derivable is computed and
**thrown away**: `structural/analyzer.py` builds `deferral_risk` per
leaf and the payload publishes `risk_keys=0` of it. The dedup there is
to publish the per-leaf risk and let the lists become filters — which
removes a copy of the membership while *adding* information the tool
already has.

That is the finding, and it moves the work: this is a **contract**
question first and a rendering question second. Deduplicating the page
while the payload still publishes three copies would put the page and
the payload into disagreement, which is the one thing the viewer axis
has refused since `UX-193`.

### An honest cost of round 38's own fix

Two of the four leaf renderings are nested tables that **`UX-277`
created**. Before it, `leaves` and `leaves_detail` were two stringified
cells — the same duplication, one line each. `UX-277` was right and it
made this duplication expensive: two 136-row tables where there were
two strings.

The rule holds — a value should be drawn by its shape — and it exposed
that the shape is published twice. That is what a good fix does; it is
also why this direction is filed immediately rather than after the
remaining round-38 items.

### The shape of the fix

**Membership is a column, not a list.** An element record carries
`is_leaf`, `on_critical_path`, `path_index`, `is_choke_point`. Then a
"list" is a *filter* over the one element table, and there is exactly
one place any element's facts live. The pattern already exists —
`signals.blast_radius` carries `is_leaf` per element today — it is just
not the pattern the lists use.

**A preset is a named (filter, columns, sort, bound).** "Critical path"
is `on_critical_path`, ordered by `path_index`, showing duration and
share. "Leaves" is `is_leaf`. "Latent heavies" is a sort and a bound.
The page has bounds (`UX-262`'s `Top N`) and filters (`UX-205`) already
and **zero named presets** — measured. The controls exist; what is
missing is the naming that turns them into views.

This is why it makes the open items smaller rather than larger:

- `UX-286`'s chapters have fewer things to group — 13 populations rather
  than 19 tables.
- `UX-283`'s choke points become a preset over a table that already has
  Inspect, sort and filter, rather than a new table.
- `UX-278`'s magnifier has one row per element to point at.
- `UX-284`'s tools are attached to one table rather than nineteen.

### Brainstorm, marked by what is measured

Measured, worth doing:

1. **Column headers are mostly placeholders.** Across 41 tables the
   commonest headers are `name` (36), `Value` (20), `Key` (10). A reader
   scanning for a column name mostly finds a word that names its
   position in a map. Presets fix most of this by giving a table a
   subject; the rest wants schema declarations.
2. **The widest table is 13 columns.** Presets are also how that becomes
   readable: four to five columns per view rather than thirteen for all
   of them.
3. **`#1`/`#2` for tuple members**, shipped this round after the first
   draft emitted `C0`/`C1` — 16 headers that read as codes. The real fix
   is for the schema to describe those arrays (`UX-290`).

Measured and **not** a problem, recorded so it is not proposed again:

4. **Empty sections.** One of 48 is near-empty, and it is the blast
   control, which is correct. There is no dead-section problem.

Unmeasured, and therefore proposals rather than findings:

5. **A distribution as one cell.** The percentile maps (`p10`…`p90`)
   are nine columns of one shape. A sparkline drawn from published
   percentiles is rendering, not deriving, so Direction 7's boundary
   permits it — but whether it reads better than nine numbers has not
   been tested.
6. **Sticky column headers** on tables taller than the viewport, beside
   `UX-284`'s sticky tools.
7. **One vocabulary for "what this is about".** A reader currently meets
   `element_uid`, `element`, `key` and `name` for the same thing in four
   tables.

### What follows

Filed as `UX-288` (the contract publishes membership three ways) and
`UX-289` (one element table, many presets), in that order, because the
second is unsafe before the first.
