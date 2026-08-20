# BuildStream Build Efficiency Analyzer (`bga`)

`bga` reads a BuildStream build and answers the four questions a build owner actually has:

- **Where did the time go?** — per-element attribution, every category summing to exactly the wall clock, not aggregate stats.
- **How much faster could this build possibly be?** — a *proven* lower bound, not an estimate. When there is nothing to win from rescheduling, it says so, which saves you the week you would have spent tuning `--builders`.
- **What should I fix first, and what is it actually worth?** — ranked by how much the build would really lose if that element were free, which on a dense graph is a very different number from how big it is.
- **And then what?** — the next few fixes, what the build drops to after each, and whether their savings add — projected from the capture you already have, instead of costing you another full build per finding.

It works in three planes — one build's element schedule, the processes inside a single element's sandbox, and the per-element logs BuildStream already wrote for every build on your machine. What each one sees and costs is the table in [`docs/README.md`](docs/README.md#three-planes).

**New here?** Install, then run the two commands under [Use it on your real project](#use-it-on-your-real-project). [`docs/guides/real-project.md`](docs/guides/real-project.md) is the same path at length, with real output at every step.

## Install

Into the venv of the project you want to analyze — `bga` does not have to
live in that project, or anywhere near it:

```bash
pip install /path/to/bga-checkout          # or the git URL
```

`pip install -e .` from inside this checkout is the **contributor** mode;
it is what `make test` and `make lint` expect, and not what a user needs.
Plane 1 and Plane 3 work on that alone. Capturing Plane 2 also needs a
real `bst` and `bubblewrap` in the same venv — `pip install -e ".[bst]"`,
or your project's own BuildStream install.

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

Bigger fixtures need no BuildStream either: `make dev-run ARGS=--large` runs a 14-element sample, and `bga gen-synthetic /tmp/scale --seed 1` generates a byte-reproducible 1202-element one — which is how [round 2](docs/audits/round-2.md) found four defects invisible at eleven elements.

## Use it on your real project

The short version is two commands, run from inside the project:

```bash
pip install -e ".[bst]"   # needs a real bst binary + bubblewrap - see docs/spec/ingestion-pipeline.md
cd /path/to/your/project
bga doctor .                          # is this machine able to capture at all?
bga snapshot -- bst build <targets>   # capture + extract + analyze
# ...make your change...
bga snapshot -- bst build <targets>   # ...and compare against the previous one
```

Run `bga doctor` first — it takes a second or two. Every capture
environment this project has stood up was assembled by failure: a
missing plugin, a compiler that is not there, `bwrap` blocked by a
sysctl. Each has a one-line remedy, and reading it before a thirty-minute
build is much cheaper than reading it after.

The second `snapshot` prints the analysis **and** the verdict against
the first. Captures land in `.bga/runs/<UTC-stamp>/` under the project
(gitignored), and every command that takes a run directory also takes
`@last`, `@prev` or a stamp prefix — `bga analyze @last`,
`bga compare @prev @last`. `bga snapshot` is those commands composed, so
it changes no number and keeps every refusal: a caches-off run compared
against a caches-on one still refuses.

The pieces underneath, for a log captured somewhere else or a capture
that cannot live in the project directory:

```bash
# Capture through the wrapper: it records the real invocation on its own first
# line, which is where `--max-jobs` lives - without it bga's capacity checks
# have nothing to check against and say so.
bga wrap /path/to/your/project /tmp/build.log -- bst build <targets>
bga extract --format wrapped /path/to/your/project /tmp/build.log /tmp/my-run
bga analyze /tmp/my-run --diagnostics
```

Either way, comparing two runs is the same command — `bga snapshot` calls it for you, and you can call it yourself on any two run directories:

```bash
bga compare /tmp/my-run-before /tmp/my-run-after
```

It reports a signed delta for every certified floor, both efficiency signals, and each attribution category, plus a verdict (`improved`/`regressed`/`no significant change`) — gated on confidence. Two runs that are not comparable are **refused** rather than compared, with an exit code of their own ([`cli.md`](docs/guides/cli.md#exit-codes)).

> **One capture is not a baseline.** Five captures of the *same*
> freedesktop-sdk commit, nothing changed, span **33%** — 3614.2s down
> to 2712.4s — against a default significance rule of 1%. Compare two of
> them and the fixed rule says `IMPROVED (-25.0%)`. So gate CI on a
> baseline *set* and its noise band, not on a single pair; `bga
> baseline` assembles one from published capture refs in one command.
> The figures, the band those five define, and where it is still not
> enough:
> [`real-project.md`](docs/guides/real-project.md#step-7--change-something-then-prove-it)
> and [`ci-comment.md`](docs/guides/ci-comment.md).

The full narrative version of this — capture, read, go inside, join, act, gate — is [`docs/guides/real-project.md`](docs/guides/real-project.md).

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


That is one command on a real 3,614-second build, and every number in it is measured
rather than estimated. What the block is doing, line by line, is
[Reading the report](docs/guides/cli.md#reading-the-report) in the CLI reference; the same
build walked end to end is [`docs/guides/real-project.md`](docs/guides/real-project.md).

Three things worth taking from it:

- **It names the constraint.** "This build is chain-bound, not scheduler-bound" is a different
  problem from a scheduling gap, and the report says which one you have before it says anything else.
- **Share of the path and what a fix is worth are different numbers.** `python3.bst` holds 17.7%
  of the chain and fixing it recovers 3.2% of the build; on a mesh graph that gap is the norm.
- **It refuses to double-count.** The top three are "exactly the sum of their individual savings",
  stated because on other graphs they would not be.

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

A `git` source keys on its **ref**, so `directory:` changes where a
checkout is staged and not what its cache key covers: twenty elements
sourcing one monorepo all rebuild on any commit to it. A `local` source
keys on **content**, so only the elements whose files changed rebuild.

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

Everything above is as deep as a BuildStream log goes: one start/end pair per element, nothing
about what happened *inside* its sandbox. A second plane traces the real process tree there —
`make -jN`, `cmake --build` — through an `LD_PRELOAD` hook, plus a ptrace spine for statically
linked processes the hook structurally cannot see:

```bash
bga snapshot -- bst build <target>     # both planes, one build
bga correlate @last                    # and what neither can say alone
```

It answers what timing cannot: **real CPU time per element** (`getrusage`, the only genuine CPU
measurement in `bga`) separating compute-bound from waiting; **where that CPU went**, ranked by
time rather than invocation count; **peak memory**, which is what decides whether `--builders`
can go up; **achieved parallelism against the `-jN` it asked for**, which is how a one-line
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
at all (the **sandbox tax** — staging, integrating, caching), and what the build tools themselves
claim they spent on configure. It costs one second of resolution and knows nothing about the
scheduler, and its own output says so. Worked example and its limits:
[`docs/guides/real-project.md`](docs/guides/real-project.md#step-0a--the-evidence-you-already-have-plane-3).

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
