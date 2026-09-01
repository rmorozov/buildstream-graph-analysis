# BuildStream Build Efficiency Analyzer (`bga`)

`bga` reads a BuildStream build and answers the four questions a build owner actually has:

- **Where did the time go?** — per-element attribution, every category summing to exactly the wall clock, not aggregate stats.
- **How much faster could this build possibly be?** — a *proven* lower bound, not an estimate. When there is nothing to win from rescheduling, it says so, which saves you the week you would have spent tuning `--builders`.
- **What should I fix first, and what is it actually worth?** — ranked by how much the build would really lose if that element were free, which on a dense graph is a very different number from how big it is.
- **And then what?** — the next few fixes, what the build drops to after each, and whether their savings add — projected from the capture you already have (`bga whatif`), instead of costing you another full build per finding.

It works in three planes — one build's element schedule, the processes inside a single element's sandbox, and the per-element logs BuildStream already wrote for every build on your machine. What each one sees and costs is the table in [`docs/README.md`](docs/README.md#three-planes). **New here?** Install, then run the two commands under [Use it on your real project](#use-it-on-your-real-project); [`docs/guides/real-project.md`](docs/guides/real-project.md) is the same path at length, with real output at every step.

## Install

Into the venv of the project you want to analyze — `bga` does not have to live in that project, or anywhere near it. Clone `--single-branch`: this repository also carries eight `captures/*` branches of published capture data, and a default clone fetches all of them (50 MiB against 5.3 MiB); nothing needs them up front, and `bga baseline` fetches the refs it wants on demand.

```bash
git clone --single-branch https://github.com/rmorozov/buildstream-graph-analysis
pip install ./buildstream-graph-analysis   # or the git URL directly
```

Plane 1 and Plane 3 work on that alone; capturing Plane 2 also needs a real `bst` and `bubblewrap`
in the same venv (`pip install -e ".[bst]"`, or your project's own BuildStream install; `bga[all]`
is `bst` plus completion). `pip install -e .` from inside this checkout is the **contributor** mode,
which is what `make test` and `make lint` expect and not what a user needs.

Tab completion — subcommands, flags, and `@last`/`@prev`/stamps wherever a run is accepted — is `pip install "bga[completion]"` plus one line in your shell rc: `eval "$(register-python-argcomplete bga)"` for bash/zsh, or `register-python-argcomplete --shell fish bga | source` for fish.

## Quick start (30 seconds, no BuildStream needed)

```bash
bga analyze tests/fixtures/golden/mixed_task_kinds --diagnostics   # or: make dev-run
```

A three-element fixture that runs instantly. The report is **91 lines**;
its two headline sections are below, verbatim, with every cut marked —
`UX-192` is on file for a block that claimed to be full output and was
not:

```text
Key Findings:
  This build is chain-bound, not scheduler-bound: the critical path is 100% of the time tasks were running, at or above the 90% chain-bound line, so the way to a shorter build is a shorter chain.
  Biggest wait category: 12.5% of wall-clock time is UNTRACKED TAIL (0.00s)
    -> real time after the last tracked task finished - outside per-task tracking, not a scheduling issue
  Where the time is: 3 element(s) are 100.0% of the 0.0s critical path - this build is chain-bound, not scheduler-bound

[... elided: the three ranked elements, the mesh note, the joint saving, the work order and the latent heavies ...]

  Confidence: 0.88 (high)
  Efficiency Score: 1.00 (scheduling is near the certified floor for this graph - further gains need the graph or the work itself to change, not the scheduler (see Dispatch Occupancy and Critical Path))

[... elided: Certified Floors, Attribution Breakdown ...]

Critical Path Length: 3 elements
  Path: base.bst → lib.bst → app.bst

[... elided: CPU Utilisation, Advanced Diagnostics ...]
```

The first two lines repay a second read, because they name **two
different denominators on purpose**. The critical path is 100% of *the
time tasks were running*; 12.5% of wall-clock is untracked tail, which
is time no task was running and no scheduler could have compressed.
`UX-477` is on file for the round when the first line divided by the
second's denominator too, and called a strict chain "scheduler-bound"
because BuildStream's own startup was in the divisor. The 90% line the
sentence names is what flips it, and `--explain` prints that constant
from the same place (`UX-331`).

Bigger fixtures need no BuildStream either: `make dev-run ARGS=--large` runs a 14-element sample, and `bga gen-synthetic /tmp/scale --seed 1` a byte-reproducible 1202-element one — which is how [round 2](docs/audits/round-2.md) found four defects invisible at eleven elements.

### Without BuildStream: one command for the whole tool (`UX-330`)

`analyze` reads a run directory, but most of `bga` reads a **store** —
two runs to compare, a Plane 2 report, a wrapped log to draw a timeline
from. One command plants one:

```bash
bga gen-synthetic --store /tmp/bga-demo
cd /tmp/bga-demo
bga snapshot --list          # the two runs it planted, newest first
bga analyze @last            # the report
bga compare @prev @last      # what moved between them
bga view @last               # the same report, in a browser
bga timeline @last -o t.gz   # both planes in one trace, for Perfetto
```

Nothing there needs `bst` or `bubblewrap`. The seed is synthetic and says
so — it is a shape to learn the commands on, not a measurement of
anything — but it is the same shape a real capture has, read by the same
code, so every answer above is the answer you will get from your own
build.

## Use it on your real project

The short version is two commands, run from inside the project:

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/spec/ingestion-pipeline.md
cd /path/to/your/project
bga doctor .                          # is this machine able to capture at all?
bga snapshot -- bst build <targets>   # capture + extract + analyze
bga view @last                        # the same report, in a browser (UX-193)
bga snapshot -- bst build <targets>   # after your change: compares against the previous run
```

Run `bga doctor` first — it takes a second or two. Every capture environment this project has stood
up was assembled by failure (a missing plugin, an absent compiler, `bwrap` blocked by a sysctl); each
has a one-line remedy, cheaper to read before a thirty-minute build than after.

`bga view` has one boundary worth knowing: **the report has no time axis** — every number in it is a
total, a per-element aggregate or a ranking. A question needing *when*, or one individual process
rather than the element around it, is a question for the trace, and the page's **Open timeline in
Perfetto** button is the way there.
[`docs/guides/what-the-viewer-answers.md`](docs/guides/what-the-viewer-answers.md) sorts all thirteen
canned questions by which side answers them, and says which [roles](docs/design/roles.md) the trip serves.

The second `snapshot` prints the analysis **and** the verdict against the first. Captures land
in `.bga/runs/<UTC-stamp>/` under the project (gitignored), and every command taking a run
directory also takes `@last`, `@prev` or a stamp prefix — `bga analyze @last`,
`bga compare @prev @last`. `bga snapshot` is those commands composed, so it changes no number
and keeps every refusal: a caches-off run compared against a caches-on one still refuses.

The pieces underneath, for a log captured elsewhere or a capture that cannot live in the project directory:

```bash
# Capture through the wrapper: it records the real invocation on its own first
# line, which is where `--max-jobs` lives - without it bga's capacity checks
# have nothing to check against and say so.
bga wrap /path/to/your/project /tmp/build.log -- bst build <targets>
bga extract --format wrapped /path/to/your/project /tmp/build.log /tmp/my-run
bga analyze /tmp/my-run --diagnostics
```

Either way, comparing two runs is one command — `bga snapshot` calls it for you, and you can call it on any two run directories yourself:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

It reports a signed delta for every certified floor, both efficiency signals, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`, or `within the baseline set's own observed range` when a duration your own baselines already reached falls outside their band) — gated on confidence. Two runs that are not comparable are **refused** rather than compared, with an exit code of their own ([`cli.md`](docs/guides/cli.md#exit-codes)).

> **One capture is not a baseline.** Five captures of the *same* freedesktop-sdk commit,
> nothing changed, span **33%** (3614.2s → 2712.4s) against a default significance rule of 1%.
> So gate CI on a baseline *set* and its noise band, not on a single pair — `bga baseline`
> assembles one from published capture refs, and `bga snapshot --aggregate` says the same thing
> about the runs you already have (min/median/p95 per host class; `--blend` to mix classes, which
> it refuses by default). The figures, the band those five define, and where it is still not enough:
> [`real-project.md`](docs/guides/real-project.md#step-7--change-something-then-prove-it)
> and [`ci-comment.md`](docs/guides/ci-comment.md).

## On a real project

Below is `bga analyze` on a real 3614-second [`freedesktop-sdk`](https://gitlab.com/freedesktop-sdk/freedesktop-sdk) build (4-core runner, `--builders 4 --max-jobs 4`), verbatim:

```text
Key Findings:
  Incremental run (caches on): BuildStream skipped elements it had already built, 2 of
  them on the critical path. Coverage and the floors below describe the work this run
  actually did, not the whole project - compare against another incremental run, not
  against a caches-off nightly
  Confidence: 1.00 (high)
  Biggest wait category: this build is execution-bound - no wait category exceeds 1% of
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

One command, every number measured rather than estimated. Three things worth taking from it:
it **names the constraint** ("chain-bound, not scheduler-bound" is a different problem from a
scheduling gap, and it says which one you have first); **share of the path and what a fix is
worth are different numbers** (`python3.bst` holds 17.7% of the chain and fixing it recovers
3.2% of the build — on a mesh graph that gap is the norm); and it **refuses to double-count**
(the top three are "exactly the sum of their individual savings", said because elsewhere they
would not be). `--explain` prints the evidence, the rule and a Perfetto query behind every one of
those claims, and `bga whatif <element>…` prices any set you pick instead of the three it ranked.
Line by line: [Reading the report](docs/guides/cli.md#reading-the-report); the same build walked
end to end: [`docs/guides/real-project.md`](docs/guides/real-project.md).

## Gating a CI pipeline

Two independent gates, because "slower" and "less efficient" are different verdicts — and on a
growing project the first fails legitimately while the second is the one that catches real harm:

```bash
bga compare runs/baseline runs/candidate --fail-on-regression             # exit 4: slower
bga compare runs/baseline runs/candidate --fail-on-efficiency-regression  # exit 5: less efficient
bga compare runs/baseline runs/candidate --fail-on-inefficient-additions  # exit 5: judged on the diff alone
```

The third is the one to reach for as a project grows: dispatch occupancy is a whole-build
average, so two maximally-mis-added elements move it **−14.6pp in an 11-element project** and
**−0.5pp in a 1201-element one** — the gate goes blind exactly where it is needed. Judging the
*change* scores those same two elements at 1.00 in both.

The whole CI sequence — capture, baseline set, gates, and posting the verdict as a PR comment —
is one page: [`docs/guides/ci-comment.md`](docs/guides/ci-comment.md).

## One repository, many elements

A `git` source keys on its **ref**, so `directory:` changes where a checkout is staged and not
what its cache key covers: twenty elements sourcing one monorepo all rebuild on any commit to
it. A `local` source keys on **content**, so only the elements whose files changed rebuild.
`bga` measures which one your project does, and what it costs:

```bash
bga analyze @last                    # a Shared Sources table, and a headline
                                     # when one repo's ref decides the graph
bga blast https://…/monorepo.git     # what a commit to it rebuilds, and for how long
bga blast components/lib-a           # the same question about one directory
```

The four ways to consume a monorepo and what each costs:
[`real-project.md`](docs/guides/real-project.md#one-repository-many-elements-the-monorepo-question).

## Looking inside one element (Plane 2)

A BuildStream log goes one start/end pair deep per element and says nothing about what happened
*inside* the sandbox. A second plane traces the real process tree there — `make -jN`,
`cmake --build` — through an `LD_PRELOAD` hook, plus a ptrace spine for statically linked
processes the hook structurally cannot see:

```bash
bga snapshot -- bst build <target>     # both planes, one build
bga correlate @last                    # and what neither can say alone
```

It answers what timing cannot: **real CPU time per element** (`getrusage`, the only genuine CPU
measurement in `bga`) separating compute-bound from waiting; **where that CPU went**, ranked by
time rather than invocation count; **peak memory**, which is what decides whether `--builders`
can go up — published as `memory_envelope` in `correlate/v2`, in megabytes, and explained in [`cli.md`](docs/guides/cli.md#how-many-builders-and-what-stops-you); **achieved parallelism against the `-jN` it asked for**, which is how a one-line
`notparallel: True` shows up as an element taking 3× as long as its work; and with
`--trace-opens`, **which declared build dependencies an element never actually read** — evidence,
never a verdict, since a runtime-only dependency is indistinguishable from an unused one.

Real output at every step, on a 127,627-process capture:
[`docs/guides/real-project.md`](docs/guides/real-project.md). What the spine costs and when to
pay it: [`docs/design/architecture.md`](docs/design/architecture.md#plane-2-knows-the-size-of-its-own-blind-spot).

## Free evidence: what your machine already recorded (Plane 3)

Both planes above need a build you decided to capture. A third needs nothing: BuildStream writes
a log for every element it builds and keeps them, so every build already on your machine —
including the ones nobody thought to instrument — is evidence.

```bash
bga cache-logs /path/to/your/project
```

It answers what neither capture plane can, because it sees *history* rather than one run: which
elements this project keeps rebuilding, how much of each element's time never reached the build
at all (the **sandbox tax** — staging, integrating, caching), and what the build tools claim they
spent on configure. It costs one second of resolution and knows nothing about the scheduler, and
says so. Worked example and limits:
[`docs/guides/real-project.md`](docs/guides/real-project.md#step-0a--the-evidence-you-already-have-plane-3).

## Documentation

[**`docs/`**](docs/README.md) is the index — it says which folder answers
which kind of question. The three entry points:

| you want to | read |
|---|---|
| **use the tool** on a real project | [`docs/guides/real-project.md`](docs/guides/real-project.md) — capture → read → go inside → join → act → gate, with real output at every step |
| **work on the codebase** | [`docs/design/architecture.md`](docs/design/architecture.md) — all three planes as one system, and every extension beyond the spec |
| **look something up** | [`docs/guides/cli.md`](docs/guides/cli.md) — every command, flag and exit code |
| **know what changed** since the build you installed | [`CHANGELOG.md`](CHANGELOG.md) — each release records a contract state, not a date |

## Development

```bash
pip install -e '.[dev]'   # pytest + ruff; `make test`/`make lint` need this, not the base install
make test-small           # the tier to run while you work: 21s, measured
make test                 # the whole suite: 5m11s, measured
make lint                 # ruff + markdown (`make dev-run` prints a real report)
```

<!-- UX-135 set `wc -l README.md` <= 250 and this file sat exactly at it. Round 46 took it to
     263 lines to state the viewer/Perfetto boundary above: readers were going looking in the
     page for answers that are only in the trace, and the six lines that say so are cheaper than
     the hunt. Round 50 takes it to 301 lines: the Quick start block claimed to be the full
     report over a sixth of it, and honest output costs the lines the elision markers and the
     restored diagnosis line take, and `UX-330`'s no-BuildStream seed paragraph is the rest -
     a stranger had no committed path into two thirds of the tool. Round 73 takes it to
     309 lines: `UX-477` changed which branch the Quick start's fixture takes, so the pasted
     block is the chain-bound one, needing an extra elision marker for the four findings that
     arm publishes and a paragraph on why the two lines above it name two different
     denominators. The budget is a measured target, not a law - but exceeding it
     silently is what turned 420 into "430" once before, so the number is here rather than in a
     commit message. -->

Tiers come from measured per-file duration (`tests/tiers.py`, `UX-238`), not from taste; `small` is
the default, so a new file joins it free. `pytest -m bst` needs a real BuildStream, and CI's
`bst-tests` job fails if any of that tier is skipped — a skipped tier would read as a pass.

## License

MIT
