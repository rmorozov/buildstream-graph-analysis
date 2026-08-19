# BuildStream Build Efficiency Analyzer (`bga`)

`bga` reads a BuildStream build and answers the four questions a build owner actually has:

- **Where did the time go?** — per-element attribution, every category summing to exactly the wall clock, not aggregate stats.
- **How much faster could this build possibly be?** — a *proven* lower bound, not an estimate. When there is nothing to win from rescheduling, it says so, which saves you the week you would have spent tuning `--builders`.
- **What should I fix first, and what is it actually worth?** — ranked by how much the build would really lose if that element were free, which on a dense graph is a very different number from how big it is.
- **And then what?** — the next few fixes, what the build drops to after each, and whether their savings add — projected from the capture you already have, instead of costing you another full build per finding.

It works in three complementary planes: a **whole-project** analysis of one build's element-level log; an **intra-element** tracer that looks *inside* a single element's sandbox at its native build system's real process tree (`make -jN`, `cmake --build`, …) — see [Advanced: looking inside one element](#advanced-looking-inside-one-element-plane-2); and a **retrospective** pass over the per-element logs BuildStream already wrote for every build on your machine, which needs no capture at all — see [Free evidence](#free-evidence-what-your-machine-already-recorded-plane-3).

**New here?** [`docs/guides/real-project.md`](docs/guides/real-project.md) is the full end-to-end walkthrough on a real project, with real output at every step.

## Install

```bash
pip install -e .
```

## Quick start (30 seconds, no BuildStream needed)

```bash
bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics   # or: make dev-run
```

A three-element fixture that runs instantly — small enough to read in full, which is the point:

```text
Key Findings:
  Confidence: 0.88 (high)
  Biggest Opportunity: 12.5% of wall-clock time is UNTRACKED TAIL (0.00s)
    -> real time after the last tracked task finished - outside per-task tracking,
       not a scheduling issue
  Elements Most Worth Optimizing First (by blast radius):
    1. base.bst (2 downstream elements)
    2. lib.bst (1 downstream elements)
    3. app.bst (0 downstream elements)
  Efficiency Score: 1.00 (scheduling is near the certified floor for this graph -
    further gains need the graph or the work itself to change, not the scheduler)

Critical Path Length: 3 elements
  Path: base.bst → lib.bst → app.bst
```

`make dev-run ARGS=--large` runs a bigger, more realistic sample — 14 elements across four
subprojects, with real headroom to find:

```text
Key Findings:
  Confidence: 0.99 (high)
  Biggest Opportunity: 5.6% of wall-clock time is IDLE (8.00s)
    -> nothing was dependency-ready at all - likely a critical-path/graph-shape issue,
       not a capacity one; check Critical Path
  Elements Most Worth Optimizing First (by blast radius):
    1. core-utils.bst:libcore.bst (7 downstream elements)
    2. ui-toolkit.bst:libwidgets.bst (2 downstream elements)
    3. data-format.bst:libjson.bst (2 downstream elements)
  Certified Headroom: up to 24.00s available (T∞=118.00s, LB=118.00s)
  Efficiency Score: 0.83 (worth checking Certified Headroom for real scheduling gains)

Certified Floors:
  T∞ (observed critical path): 118.00s
  LB (resource lower bound):   118.00s
  Certified Headroom:          24.00s
  T_C (replay makespan):       118.00s
  Dispatch Occupancy:          45.1% of available slot-time used

Critical Path Length: 4 elements
  Path: core-utils.bst:libcore.bst → ui-toolkit.bst:libwidgets.bst → ui-toolkit.bst:libui.bst → app.bst
```

### At a thousand elements, still no BuildStream needed

```bash
bga gen-synthetic /tmp/scale --seed 1   # 1202 elements, 14 levels, 16 builders
bga analyze /tmp/scale --diagnostics                            # ~3.8s
```

```text
  Biggest Opportunity: 70.1% of wall-clock time is RESOURCE WAIT (250.25s)
    -> a resource (PROCESS/DOWNLOAD/UPLOAD) was saturated - try --capacity N with a
       higher N, or `bga sweep` to find the real knee point
  Elements Most Worth Optimizing First (by blast radius):
    1. toolchain.bst (1201 downstream elements) [structural: import, may not reflect real compute work]
    2. layer00/mod037.bst (753 downstream elements)
    3. layer00/mod003.bst (753 downstream elements)
  Highest Criticality Elements:
    1. layer01/mod098.bst (70% probability of being on critical path)
  Certified Headroom: up to 9.09s available (T∞=85.65s, LB=346.06s)
```

A different shape from the sample above, and the report says so: this run is **resource-bound**, so the ceiling is `LB` (346.06s) rather than the critical path (85.65s) — more builders, not a shorter chain. The fixture is byte-reproducible from its `--seed`; it exists because a second audit round found four defects invisible at eleven elements.

## On a real project

Below is `bga analyze` on a real 3614-second [`freedesktop-sdk`](https://gitlab.com/freedesktop-sdk/freedesktop-sdk) build (4-core runner, `--builders 4 --max-jobs 4`), verbatim:

```text
Key Findings:
  Incremental run (caches on): BuildStream skipped elements it had already built, 2 of
  them on the critical path. Coverage and the floors below describe the work this run
  actually did, not the whole project - compare against another incremental run, not
  against a caches-off nightly
  Confidence: 1.00 (high)
  Biggest Opportunity: this build is execution-bound - no wait category exceeds 1% of
  wall-clock time, so there is no scheduling gap to close
  Where the time is: 4 element(s) are 94.0% of the 3610.5s critical path - this build is
  chain-bound, not scheduler-bound
    components/_private/cmake-stage1.bst    1569.8s (43.5% of path)  -> fixing it saves 1569.8s (43.4% of the build)
    components/openssl.bst                   672.1s (18.6% of path)  -> fixing it saves 522.5s (14.5% of the build)
    components/python3.bst                   639.8s (17.7% of path)  -> fixing it saves 114.1s (3.2% of the build)
    components/doxygen.bst                   513.5s (14.2% of path)  -> fixing it saves 513.5s (14.2% of the build)
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so
    savings on one element are often capped by the next chain rather than by its own duration
  Together, the top 3 are worth 2605.8s (72% of the build) - exactly the sum of their
  individual savings, so they are three separate pieces of work that do not overlap
  Work them in this order (by what a fix is worth, not by size), with what the build drops
  to: cmake-stage1.bst (2041s) -> openssl.bst (1518s) -> doxygen.bst (1005s)
  Waiting off the critical path, worth nothing to fix today:
  components/_private/git-minimal.bst (548s), components/icu.bst (431s) (+2 more)
```

Three things in that block are worth pointing at, because they are the difference between a report and an answer:

- **`python3.bst` is the third-largest element on the chain and worth 3.2% of the build to fix.** Share of the path and value of a fix are different numbers, and on a mesh graph they disagree by 5×. Ranking by size would have sent you after a week's work for a minute's gain.
- **The top three are worth 72% *together*, and that equals their sum** — so they are three independent pieces of work, and three people can take one each. Whether savings compose is a property of your graph, simulated rather than assumed.
- **`git-minimal.bst` is the fourth-heaviest element in the entire build and is worth nothing to fix today.** It appears in no ranking, correctly — and you still need to know it is there, because it is the floor your chain-shortening is heading towards.

Then the same build, seen from inside the sandboxes and joined back to whole-build impact (`bga correlate`):

```text
What to do next (ranked by Plane 1 impact):
  components/_private/cmake-stage1.bst:
    - holds 43% of the critical path and fixing it is worth 1569.8s (43.4% of the build)
      - already compute-bound at 3.41 cores busy, so there is nothing to gain from its
      parallelism; shortening it means less work
    - 81% of its measured CPU is one binary, `cc1plus` (885 process(es), 4353 CPU s) -
      this element is a `cc1plus` problem, so look there before anywhere else
    - `dwz` is a SINGLE process holding 138.6s of wall time - a serialization point no
      job count can help; it has to get faster or go away
    - its largest single process peaked at 1902 MB resident - see the memory envelope
      above for what that means for `builders`
    (84% of this element's processes were measured)
```

That last row used to end *"multiply by however many elements build concurrently before raising `builders`"* — arithmetic handed to the reader. It is now done, once, for the whole build, from the same capture:

```text
Memory envelope: 4 builders of this shape peak at ~4.0 GB of 15.6 GB (25%); 11 would
still fit, so memory is not what binds first here
```

(freedesktop-sdk, capture run `32223468993`. The envelope at N builders is the sum of the N largest measured per-element peaks, as if they all peaked at once — an upper bound, which is the useful direction to be wrong in when the question is whether to raise `builders`. A capture that recorded no host memory gets the multiplication back, and says why.)

That is one report telling you: the element that is 43% of your build is a C++ template problem, not a scheduling one; there is a 138-second serialization point inside it that no `-j` value touches; and four concurrent builders of that shape need ~7.6 GB. **Full step-by-step walkthrough, every command and every output: [`docs/guides/real-project.md`](docs/guides/real-project.md).**

## Reading the report

- **Confidence** — how much to trust the numbers below (data completeness/quality of this specific trace). Below "high"? Fix the underlying trace before acting on anything else. A build that *failed* is called out even louder, before any efficiency figure.
- **Certified Headroom** — a *proven* lower bound, not a guess: given the work this build actually did, it cannot possibly finish faster than `T∞`/`LB` (whichever is larger) without changing that work. Headroom above zero means real room to improve scheduling *without touching any element's build steps*; zero means rescheduling cannot help at all.
- **Efficiency Score and Dispatch Occupancy** — deliberately two numbers, because one cannot do the job. **Efficiency Score** asks *"did the scheduler pack this graph well?"*, and everything it is built from comes from the graph this run actually had — so a build whose independent elements were accidentally chained scores a perfect 1.00, correctly and uselessly. **Dispatch Occupancy** asks *"how much of the available slot-time did the run actually use?"* and never consults the graph, so serializing work that could have run concurrently pushes it down. Read them together: a high score with low occupancy means the scheduler did fine and the *graph* is the problem. (Real measured pair: three one-line fixes made a build 30.5% faster while Efficiency Score fell 1.00 → 0.83 and Dispatch Occupancy rose 27.8% → 63.0%. See [`docs/backlog/scenarios/UX-27`](docs/backlog/scenarios/UX-0027-efficiency-score-certifies-the-graph-it-was-given.md).)
- **Where the time is** — on a build the chain constrains, the headline is one table: each heavy element's duration, its share of the critical path, and what fixing it would actually recover. The rows are ordered by duration because that is what "where is the time" means; the fix order is named separately, because on a dense graph the two disagree.
- **What to do after that** — the next few fixes projected from the same capture: what the build drops to after each, whether the recommended set's savings *add*, and which heavy elements sit off the critical path worth nothing to fix today. Without it, finding the second thing to fix costs another full build. ([`UX-74`](docs/backlog/scenarios/UX-0074-one-capture-one-finding.md))
- **Elements Most Worth Optimizing First** — on a build the *graph* constrains rather than the chain, this ranks by blast radius instead: fixing a slow element near the root helps every downstream element too.
- **Biggest Opportunity / Attribution Breakdown** — where wall-clock time went, by category: execution, dependency wait, resource wait, scheduler wait, idle, retries, plus **untracked head and tail** (real wall-clock before the first task started and after the last one finished, which belongs to no task at all). All eight sum to exactly the total build time — nothing is hidden or double-counted, and the two untracked categories are why: on the quick-start fixture above, untracked tail is 12.5% of the build and is the *largest* non-execution category.
- **Critical Path** — the chain that determines total build time, printed in full with each link's duration and share.
- If a hard gate fails (e.g. `critical_path_coverage`), the violation names the specific missing element(s) and whether each is a structural element (`stack`/`import`/…) that never had a real compute task or a genuine gap worth investigating.

Everything in that block is also published as **data**, with a stable `id`, a `severity` and the numbers behind each sentence — so a CI job acts on `.findings[]` rather than re-deriving a threshold or grepping prose:

```bash
bga analyze /tmp/run --format json | jq '.findings[] | select(.id == "time-concentration") | .evidence'
```

```json
{
  "path_us": 3610500000,
  "share_of_path": 0.94035,
  "chain_bound": true,
  "rows": [
    { "element_uid": "components/_private/cmake-stage1.bst", "duration_us": 1569800000,
      "share_of_path": 0.43478, "realizable_saving_us": 1569800000 },
    { "element_uid": "components/python3.bst", "duration_us": 639800000,
      "share_of_path": 0.17720, "realizable_saving_us": 114100000 }
  ]
}
```

The `rows` array is the part a CI comment renders: each heavy element's measured duration, its
share of the chain, and — separately — what fixing it would actually recover, which on a dense
graph is a much smaller number than its share suggests.

## Use it on your real project

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/spec/ingestion-pipeline.md
# Capture through the wrapper: it records the real invocation on its own first
# line, which is where `--max-jobs` lives - without it bga's capacity checks
# have nothing to check against and say so.
bga wrap /path/to/your/project /tmp/build.log -- bst build <targets>
bga extract --format wrapped /path/to/your/project /tmp/build.log /tmp/my-run
bga analyze /tmp/my-run --diagnostics
```

Then iterate: make a change, rebuild, extract a new run, and compare it against the baseline:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

This reports a signed delta for every certified floor, both efficiency signals, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) — gated on confidence. If the two runs don't look like the same project, or one is a caches-off run and the other incremental, it **refuses** — exit 6, distinct from the gates' 4 and 5, so a CI job cannot mistake a wrong-artifact-path bug for a regression. `--allow-mismatch` compares anyway.

> **One capture is not a baseline.** Measured on **three** captures of the *same* freedesktop-sdk commit, taken by the scheduled capture workflow: 3614.2s, 3434.4s, 3405.8s — a **5.8% spread with nothing changed**, against a default significance rule of 1%. Compare the first against the third under the fixed rule and the verdict is `IMPROVED (-5.8%)`; judged against the band those three runs define (median 3434.4s ± 3×42.5s scaled MAD), the same pair is `NO SIGNIFICANT CHANGE` — which is the truth, because they are the same commit. For CI, build a baseline *set* and use the band. `--baseline-run` is *in addition to* the two positional arguments, not instead of them — and the band is built from the `--baseline-run` entries alone, so it needs **three of them**; the positional baseline is not counted:
>
> ```bash
> bga compare baseline/ candidate/ \
>     --baseline-run baseline-1/ --baseline-run baseline-2/ \
>     --baseline-run baseline-3/ --band-k 3.0
> ```
>
> With fewer, `bga` says so — `No noise band: 2 baseline run(s) supplied, 3 required` — and falls back to the fixed 1% rule rather than inventing a band.

The full narrative version of this — capture, read, go inside, join, act, gate — is [`docs/guides/real-project.md`](docs/guides/real-project.md).

## Gating a CI pipeline

Two independent gates, because "the build got slower" and "the build got less efficient" are different verdicts:

```bash
bga compare runs/baseline runs/candidate --fail-on-regression              # exit 4: slower
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression   # exit 5: less efficient
bga compare runs/baseline runs/candidate --min-efficiency 0.45             # exit 5: below an absolute floor
```

The second is the one worth reaching for on a growing project. Adding three new elements makes the build slower, and a wall-clock gate cannot tell that apart from a real regression — so the only remedy is raising the threshold, which blinds it to everything else. The efficiency gate asks the question a build owner actually has: **adding work is allowed; adding work *inefficiently* is not.** Measured on one real project:

| change | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| two more well-parallelized elements | +2.5% | **fails** | 60.0% → 73.8% | passes |
| graph serialized, one element pinned to `-j1` | +44% | fails | 63.0% → 27.8% | **fails** |
| oversubscribed (`8×8` on 4 cores) | +19% | fails | 63.0% → 48.6% | **fails** |
| nothing changed (repeat capture) | −7.4% noise | fires on ±1% noise | 60.0% → 59.0% | passes |

**On a growing project, reach for the third gate.** Dispatch occupancy is a whole-build average, so its sensitivity is inversely proportional to project size: measured on fixtures, two maximally-mis-added elements move it **−14.6pp in an 11-element project** (the gate fires) and **−0.5pp in a 1201-element one** (the gate passes, blind). `--fail-on-inefficient-additions` judges the *change* instead — what share of the work this diff added landed on the critical path — and scores those same two elements at **1.00 in both**:

```bash
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions   # exit 5
```

```text
New this change: g.bst, h.bst - 8.0s of work added, 8.0s of it on the critical path
(stretch 1.00)
```

Full flags, thresholds and how the defaults were derived: [`docs/guides/cli.md`](docs/guides/cli.md#ci-efficiency-gate---fail-on-efficiency-regression---min-efficiency).

Other useful commands:

```bash
bga analyze /tmp/my-run --format json > report.json      # machine-readable, for CI/tracking over time
bga sweep /tmp/my-run --resource PROCESS --min-capacity 1 --max-capacity 16  # "how many builders is enough?"
bga replay /tmp/my-run --capacity 16                      # simulate a hardware upgrade
```

The `graph`/`floors`/`replay`/`sweep`/`utilisation`/`diagnostics` subcommands are narrower slices of the same `analyze` report — reach for one of them instead of grepping `analyze`'s output for a single question. They are also genuinely cheaper: each runs only the pipeline stages its own section renders (`UX-47`), so on a 1200-element run `bga graph` costs ~1.2s against `analyze`'s ~3.7s. Full reference: [`docs/guides/cli.md`](docs/guides/cli.md).

## Advanced: looking inside one element (Plane 2)

Everything above answers *"across the whole build, where did the time go and what's the ceiling on making it faster?"* — that's as deep as a BuildStream log itself goes: one start/end timestamp per element, nothing about what happened *inside* its sandbox. A second, separate tool answers *"inside this one element, is its own native build system actually parallelizing well, or silently serializing / doing redundant work?"* — real per-process tracing via an `LD_PRELOAD` hook inside the sandbox, not a guess from timing alone:

```bash
bga capture run /path/to/your/project report.json -- bst build <target>
```

An `LD_PRELOAD` hook cannot see a statically-linked process — nothing loads it there. `bga capture census PROJECT` measures how large that blind spot is for a given project without building anything, and `--trace-spine` adds a ptrace process-event tracer that records every process whatever its linkage, at a measured **0.3–1.1 ms per process** (`UX-112`/`UX-129`; five independent measurements, raw figures in [`docs/audits/data/spine-cost-storm.md`](docs/audits/data/spine-cost-storm.md)). That is invisible where processes live tens of milliseconds and dominant where they live two, which is why it is a flag rather than the default — on `examples/01-resource-contention`, whose every command is static busybox, it is the difference between 0 processes and 24.

**Real CPU time per element** (`getrusage`, measured in-process — the only genuine CPU measurement anywhere in `bga`) answers what timing alone cannot: *was this element compute-bound, or waiting?* On the real `freedesktop-sdk` capture, on a 4-core runner:

```text
Real CPU time (getrusage): 11744.07s across 119492 of 127627 traced processes
  components/_private/cmake-stage1.bst 5351.14s CPU over 1567.12s wall =  3.41 cores busy  [84% measured]
  components/doxygen.bst               1825.48s CPU over  512.62s wall =  3.56 cores busy  [80% measured]
  components/bison.bst                  130.42s CPU over  142.97s wall =  0.91 cores busy  [100% measured]
```

The first two are genuinely compute-bound — nothing to win from their parallelism. `bison.bst` at 0.91 is the outlier: one core busy is the signature of a build that never overlapped any work, and that is a job-count setting, not a rewrite.

**Where that CPU went**, ranked by time rather than by invocation count — which is the difference between finding the problem and finding the most frequent process:

```text
  components/_private/cmake-stage1.bst
    cc1plus           4352.6 CPU s (81.3%)     885 process(es), 5525.6s wall
    as                 397.5 CPU s ( 7.4%)    1918 process(es), 5929.8s wall
    dwz                137.0 CPU s ( 2.6%)       1 process(es), 138.6s wall
    NOTE: dwz is a SINGLE process holding 138.6s of wall time - a serialization
    point that more parallelism cannot help
```

**Peak memory per element**, which is how you decide whether `--builders` can go up at all — `1901.9 MB` in a single process means four concurrent builders of that shape need ~7.6 GB.

**Achieved parallelism against the `-jN` it asked for** — the number that separates "this element is legitimately 13 seconds of work" from "this element is 4 seconds stretched to 13 by a one-line `notparallel: True`" (from a small local project, where that case exists):

```text
Per-element native parallelism (real compiler/assembler/linker processes only):
  element                  peak  req  achieved     span work
  core.bst                    2    1      200%   14.22s   32  <- pinned to -j1 while the rest of this build ran higher
  lib-a.bst                   3    4       75%    2.46s   22
```

And with `--trace-opens`, **which declared build dependencies an element never actually read** — by recording the files each sandbox opened and matching them against each dependency's own artifact contents. These are candidates with evidence, never verdicts: a runtime-only dependency is indistinguishable from an unused one from here, and a dependency that stages almost nothing of its own (a `stack` stages one marker file) is set aside rather than reported.

### Joining the planes

Capture both from one build, then join them on element UID — the only contract between the planes:

```bash
bga capture run --wrapped-log /tmp/plane1.log \
    /path/to/project /tmp/plane2.json -- bst build <target>
bga extract --format wrapped /path/to/project /tmp/plane1.log /tmp/run
bga correlate /tmp/run /tmp/plane2.json
```

This produces what neither plane can alone — see [the real example above](#on-a-real-project). Rows are ordered by evidence strength, strongest measurement first and explicitly hedged ones last; every row states its own measurement coverage; and a Plane 2 name that is not a declared element is excluded and listed rather than quietly recommended. The negative result matters too: an element reported as *already compute-bound* is one to stop looking inside.

It also detects real operations repeated independently across *multiple* elements' sandboxes (`autoconf` probes, `m4` runs — scored in recoverable wall-clock for the worst-affected element rather than summed across elements that ran concurrently) and can export a [Chrome Trace](https://ui.perfetto.dev)-viewable timeline, standalone or combined with the whole-project view into one file.

## Free evidence: what your machine already recorded (Plane 3)

Both planes above need a build you decided to capture. A third one needs
nothing at all. BuildStream writes a log for every element it builds and
keeps them — so every build already on your machine, including the ones
nobody thought to instrument, is evidence:

```bash
bga cache-logs --project <your-project>
```

```text
Sandbox tax: 13.0s of 4409.0s element time (0.3%) across 23 build log(s) went to
staging, integrating and caching rather than to the build itself

Configure tax (Plane 3, self-reported): 35.5s of 4409.0s element time (0.8%),
reported by 3 of 23 build log(s)
  5 element(s) have traced configure work and no self-report - an autotools or
  meson build system, and the case the self-report alone is blind to
```

It answers what neither capture plane can, because it sees *history*
rather than one run: which elements this project has spent the most time
rebuilding, how much of each element's time never reached the build at
all (the **sandbox tax** — staging, integrating, caching), and what the
build tools themselves claim they spent on configure. It costs one second
of resolution and knows nothing about the scheduler, and it says so in
its own output rather than letting you assume otherwise.

Pass `--native-report` and it puts Plane 3's self-reported configure time
beside Plane 2's traced CPU for the same elements — shown side by side,
never summed, because one is wall-clock a tool reported about itself and
the other is CPU seconds somebody measured.

## Documentation

[**`docs/`**](docs/README.md) is the index — it says which folder answers
which kind of question. The three entry points:

| you want to | read |
|---|---|
| **use the tool** on a real project | [`docs/guides/real-project.md`](docs/guides/real-project.md) — capture → read → go inside → join → act → gate, with real output at every step |
| **work on the codebase** | [`docs/design/architecture.md`](docs/design/architecture.md) — all three planes as one system, and every extension beyond the spec |
| **look something up** | [`docs/guides/cli.md`](docs/guides/cli.md) — every command, flag and exit code |

## Development

```bash
pip install -e '.[dev]'   # pytest + ruff; `make test`/`make lint` need this, not the base install
make test                 # run the full suite
make lint                 # ruff
make dev-run              # sample report, fast smoke check
```

Some tests are gated on a real BuildStream being present and are skipped without one. To run
them, add the `bst` extra and `buildstream-plugins`, then `pytest -m bst` (CI's `bst-tests` job
does exactly this, and fails if *any* of them is skipped — a skipped tier would otherwise
read as a pass).

## License

MIT
