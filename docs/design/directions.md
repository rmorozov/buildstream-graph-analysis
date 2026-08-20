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
