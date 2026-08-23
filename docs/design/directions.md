# Design directions: `bga` as a local optimization helper, and `bga` as a CI gate

Written 2026-08-16 after a full hands-on audit and a real macro-then-micro
optimization walkthrough
([`optimization-walkthrough-06.md`](../audits/case-study-06-macro-micro.md)). This
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

## Direction 2: `bga` as a CI tool

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
occupancy_ratio = Σ task occupancy / (wall_clock × capacity)

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
> `occupancy_ratio` with their own exit code `5` (`UX-39`), and the
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
`chain_ratio` would be the second decision-maker `UX-207` exists to
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
| [25](../audits/round-24.md) | round 24's first four executed: `correlate/v1` published and the viewer drew it with no change; the dead anchors resolve; findings show their evidence; the next command is published rather than derived. The page-size ceiling stopped being a number and became a ratio (`UX-215`..`UX-218`) |
| [26](../audits/round-24.md) | round 24's remaining eight executed: the schema learned to say what its numbers mean, `compare/v1` learned which elements changed, the store learned to remember one, and the page learned to draw a plan, focus one element and carry the reader's own marks in the link. Two task premises corrected and two mutations rejected for not discriminating (`UX-219`..`UX-226`) |
| [27](../audits/round-27.md) | twenty for twenty on the eighteen-commit landing, two hollow guards filed. The role model written: four roles served, four unserved; Direction 8 (provenance) adopted from the fourth review, its workspace declined; Direction 9 (the team axis) opened from the user's positioning (`UX-227`..`UX-235`) |

## Verification Log

Written 2026-08-16 from a real session: BuildStream 2.7.0 with
`buildstream-plugins`, real `bwrap` sandboxes, real `gcc 13`/`cmake 3.28`
staged by `examples/stage_cpp_toolchain.sh`, on a 4-core / 16GB Linux
host. Every number quoted is from a real build and a real `bga`
invocation in that session, recorded in
[`optimization-walkthrough-06.md`](../audits/case-study-06-macro-micro.md); every
claim about what the code does was checked against the source rather than
inferred from output. The proposed report and CI-comment layouts are
illustrations of intent, not implemented output.
