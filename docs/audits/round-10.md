# Audit round 10: the user's walk, end to end

Run on 2026-08-18 in a fresh environment: clean venv, BuildStream 2.7.0
+ buildstream-plugins, real `bwrap` sandboxes, gcc 13 / cmake 3.28
staged by `examples/stage_cpp_toolchain.sh`, 4-core / 16 GB Linux host —
deliberately the same shape as the environment every prior number came
from, but set up from nothing by following the docs, which is itself
part of the audit. Three probes, run as one session:

1. **Claims vs reality** — every substantive README/`docs/guides/cli.md` claim
   traced to code or a live invocation.
2. **The full macro→micro optimization cycle** on `examples/06`, done
   the way a user would: capture → read → act on what the report says →
   rebuild → compare → repeat — plus a growth experiment the examples
   don't cover.
3. **The real-project infrastructure**: the `captures/fdsdk-latest`
   branch, all 24 runs of the `Real-project capture` workflow, and
   `bga analyze`/`correlate` re-run against the published fdsdk capture.

Everything filed from this round is `UX-77`..`UX-92` in
[`scenarios/`](../backlog/scenarios/README.md). This document is the narrative and
the verdict.

## What the tool claims to be, and what it is

The claim structure of the README is: four questions answered, two
planes, certified (not estimated) floors, conclusions as data, and a CI
gate that distinguishes "slower" from "less efficient". The audit's
answer, compressed:

**The analysis is what it claims.** Attribution summed to the horizon
*exactly* (verified to the microsecond on the 1202-element fixture);
the scale fixture's published numbers reproduce byte-for-byte from
`--seed 1`; the fdsdk report in the README reproduces byte-for-byte
from the published capture — in **0.27 seconds**, which is its own kind
of claim honored. All four gate directions exercised live returned the
documented exit codes. Round 9's "the loop is closed" held up under
re-verification by a different pair of hands.

**The packaging is not.** The first documented real-project command,
run from a modern-pip install — editable or not, repo root or not —
dies with a raw `ModuleNotFoundError: No module named 'tools'`,
because `pyproject.toml` packages `bga*` only and every `bga
wrap/extract/capture` alias imports `tools.*` at dispatch time
(`UX-77`). Every consumer that works — CI, pytest, presumably every
prior round — reaches the tools by a path a user is never told about.
This round's entire hands-on cycle ran with a manual `PYTHONPATH`
export that appears in no document.

**Three promises are stronger than the code.** The compare "refusal"
on mismatched runs is a warning wearing a guarantee's clothing —
a golden fixture vs a real run produced `Verdict: REGRESSED
(+105668.8%)`, exit 0, and exit 4 under the gate (`UX-78`). The
documented capture command cannot produce the documented join on a
project that overrides `build-root`, because the flag that makes
attribution work (`--invocation-log`) appears only in CI's invocation,
zero times in the docs (`UX-80`). And the README quick start shows the
output of a different command than the one it tells you to run, along
with a dozen smaller verified drifts — the formula for Efficiency Score
among them (`UX-88`).

**One tier of the test suite is dead.** With a real bst installed,
4 bst-gated tests fail — including per-element `max-jobs: 16` override
extraction returning 4, the host core count — and no CI job runs pytest
with bst present, so nothing could have noticed (`UX-84`).

## The walk: macro, then micro, on `examples/06`

The protocol, exactly as a user would run it (all times real, 4 cores,
`--builders 4 --max-jobs 4`, caches cleared between builds):

| step | project variant | wall-clock | Dispatch Occupancy | Efficiency Score |
|---|---|---|---|---|
| baseline capture | mis-optimized | 27.87s | 29.0% | 1.00 |
| **macro fix** (unchain libs, scope codegen) | macro-only | 25.05s (−10.1%) | 59.3% | 0.86 |
| **micro fix** (remove `notparallel`) | `optimized/` | 16.92s (−32.4% more) | 61.2% | 0.79 |

Total −39.3%, found in the order the example intends, and the two-signal
design (`UX-27`) is vindicated again: **the build got 39% faster while
Efficiency Score fell monotonically 1.00 → 0.79**. Anyone still tempted
to gate on that number should read this table twice.

What the reports did well, concretely:

- After the macro fix, `bga correlate` led with *exactly* the right
  next action, unhedged and quantified: *"`core.bst` holds 50% of the
  critical path and fixing it is worth 9.0s … runs at only 0.90 cores
  busy … its native build asked for -j1: remove `notparallel`"*. That
  is the product working: Plane 1 impact, Plane 2 cause, one sentence.
- The declared-but-never-read detection flagged every decorative edge
  in the baseline — including the chain edges and `codegen.bst` —
  with the honest runtime-only hedge each time.
- `bga compare` verdicts were correct in all four directions tested,
  and the redundancy detector correctly identified the 9× repeated
  cmake configure probes with per-element recoverable bounds.

Where the user is left alone (each filed):

- Nothing ever *says* the macro fix. The chain is on the critical path;
  each chain edge is individually measured never-read; the conclusion
  "these six should fan out, worth ~2.9s" is never drawn (`UX-82`).
  The baseline headline instead points at UNTRACKED HEAD —
  BuildStream's own startup — as the "Biggest Opportunity".
- On the macro-fixed run, Plane 1's headline and `sweep` both steer
  toward **more builders on an already-saturated 4-core host** (knee
  point: capacity 5) while `correlate` on the same capture names the
  real, zero-cost fix (`UX-83`). The planes disagree and nothing
  arbitrates.
- Seven of nine `correlate` rows are the same finding repeated with
  different names (`UX-89`).

One more thing the evidence trail showed that the example itself does
not acknowledge: **every** `core.bst → lib-*` edge is also measured
never-read, so the tool's evidence, taken seriously, leads *past* the
example's own "right answer" — the optimized variant retains six
decorative edges on the heaviest element in the build. The walkthrough's
gold standard is itself improvable by the tool's own data, which is the
strongest possible argument for `UX-82`'s synthesis existing.

## The growth experiment: the CI question, answered on real builds

The build owner's rule: *adding elements may make the build slower —
that is allowed; adding them inefficiently is not.* Tested by adding two
elements to `optimized/` twice — once fanned out at `-j4`, once chained
behind everything at `-j1`:

| addition | wall-clock | duration gate | Dispatch Occupancy | efficiency gate |
|---|---|---|---|---|
| two elements, well-parallelized | +4.7% | fails (exit 4) | 61.2% → 72.3% | **passes** |
| same two, chained + `notparallel` | +19.0% | fails (exit 4) | 61.2% → 55.1% | **fails (exit 5)** |

The duration gate cannot express the rule; the efficiency gate
expresses it exactly — on this project. The margin is the finding: the
*worst possible* two-element addition moved global occupancy 6.1pp
against a 5.0pp default in an 11-element project. Occupancy is a
whole-build average; at fdsdk's 90 elements the same crime moves it
under 1pp and walks. The gate the CI story needs is **marginal** — the
efficiency of the diff, not of the repository (`UX-79`) — and its
supporting per-element diff is the same 2b item
`design-directions.md` has carried since round 1.

Two adjacent gate defects, also filed: the gates silently stop gating
when `occupancy_ratio` is absent from either run (`UX-87`), and the
mismatched-run "refusal" that would catch a mis-wired CI artifact path
is a warning (`UX-78`).

## The infrastructure: one capture, force-pushed over

The `captures/fdsdk-latest` branch and workflow are genuinely good at
what they do — warm/cut/verify is the right design, the published
capture is complete and fresh, and `bga analyze` on a fetched checkout
reproduces the README verbatim. But as *infrastructure for the CI
story* it is one-shot by construction:

- **history**: force-pushed single commit — each publish destroys its
  predecessor, while the tool's own docs require a ≥3-run baseline set
  and measure 2.9% noise against the 1% default rule (`UX-81`);
- **cadence**: no schedule trigger, so trend data cannot accumulate
  (`UX-81`); meanwhile **17 of 24** workflow runs were push-triggered
  cancellations, several after 25–57 runner-minutes (`UX-90`);
- **coverage**: every capture ever taken is incremental; the caches-off
  scenario — round 9's named gap — remains uncaptured (`UX-86`).

## Verdict

Round 9 said: MVP-ready analysis and reporting, CI gate not. Round 10,
with a fresh walk: **the analysis engine and the two-plane correlation
are past the MVP bar and re-verified; the product around them is not
yet** — a first-run experience that crashes on the first documented
command (`UX-77`), three documented guarantees the code doesn't keep
(`UX-78`, `UX-80`, `UX-88`), and a CI story whose gate logic is right
but whose sensitivity model (`UX-79`) and data supply (`UX-81`,
`UX-86`) don't yet meet the stated rule. None of these is analysis
work; all of them are between the analysis and its users.

The order that follows from this round: `UX-77` first (it is the front
door), then `UX-80` + `UX-78` (make the documented path produce the
documented result and fail honestly), then the CI chain `UX-81` →
`UX-79` → `UX-86`, with `UX-82`/`UX-83` as the highest-value analysis
additions and `UX-91`/`UX-92` as the next capability round after that.

---

> Moved out of [`docs/design/directions.md`](../design/directions.md) during the round-11 documentation housekeeping.

## The tenth round: the two usage scenarios, re-argued (2026-08-18)

Round 10 ([`audit-round-10.md`](../audits/round-10.md), filings
`UX-77`..`UX-92`) walked both scenarios end to end in a fresh
environment — the full macro→micro cycle on `examples/06` with real
dual-plane captures (**27.9s → 25.0s → 16.9s**), a real growth
experiment against both CI gates, and the fdsdk capture infrastructure.
What follows is the state of each scenario after that walk, and where
each should go next. The one-line version: **the analysis has crossed
the MVP bar in both scenarios; what remains between the tool and its
users is packaging, synthesis, and data supply — in that order.**

### Scenario 1: the local optimization helper

The loop works, and this round is the first time a full cycle was run
by following only the documentation — which is how it found that the
documented entry point crashes on install (`UX-77`) and that the
documented capture omits the flag the join needs on real projects
(`UX-80`). Both are plumbing. Fix them first; nothing else in this
scenario matters to a user who never gets past the first command.

Past the front door, the round's experience says the helper's next
frontier is **synthesis, not measurement**. Every fact of the
walkthrough's macro problem was measured — the chain on the critical
path, every chain edge individually never-read — and the conclusion was
left to the user (`UX-82`). The two planes disagreed about what to do
next on the same capture, and nothing arbitrated (`UX-83`). The measure
→ conclude gap is now the defining gap of the local scenario, and the
round's sharpest evidence for it is reflexive: the tool's own evidence,
taken seriously, improves on the walkthrough example's own "optimized"
answer (six decorative edges retained on the heaviest element). A tool
that can out-reason its own gold standard but doesn't say so out loud
is exactly one synthesis pass short of its value.

### Scenario 2: the CI tool

Three sub-jobs, re-verdicted on this round's evidence:

- **Gather analytics: works, has nowhere to put anything.** The JSON
  contract is real (findings ids, stable fields, verified). But the
  capture infrastructure force-pushes over its own history (`UX-81`),
  has no schedule, and burned 17 of 24 runs on push-cancellations
  (`UX-90`). Analytics need a time series; today the pipeline keeps
  exactly one point. This is entirely infrastructure work and it gates
  everything below.

- **Highlight problems: blocked on the per-element diff.** Unchanged
  verdict from round 1's 2b, now with sharper evidence: the growth
  experiment produced runs where the *right* CI comment is obvious
  ("`lib-h.bst`: serialized behind `lib-g.bst`, +4.1s of critical
  path, declared dep never read") and every ingredient exists — new
  elements are identifiable from the two graphs, their path deltas
  from `UX-74`'s machinery, the never-read evidence from `UX-46`. It
  is still unassembled.

- **Stop regressions: right gate, wrong denominator.** The round's
  growth experiment is the strongest validation the efficiency gate
  has ever had — it passed legitimate growth (+4.7% wall-clock, gate
  green) and failed the same growth done badly, exactly the build
  owner's stated rule. It is also the strongest indictment: the worst
  possible two-element crime scored 6.1pp against a 5.0pp default in
  an 11-element project, and dilutes below 1pp at fdsdk scale
  (`UX-79`). A whole-build average can never express "the *new* work
  is inefficient" on a large project. The gate the rule needs is
  marginal — the inefficiency of the diff — with the whole-build gate
  kept for global serialization regressions. Until `UX-79` and
  `UX-81` (the ≥3-run baseline the band gate already requires) land,
  the honest advice to a CI owner is: gate on
  `--fail-on-efficiency-regression` for repositories under ~20
  elements, treat it as advisory above that, and never gate on
  Efficiency Score (this round: build 39% faster, score 1.00 → 0.79,
  monotonically).

Two hardening items apply to any gate that ships: a gate must say when
it did not run (`UX-87`), and a comparison of the wrong two runs must
refuse rather than verdict (`UX-78`).

### The next capability rounds: what the tool could see that it doesn't

Brainstormed against this round's evidence and filed where concrete:

1. **BuildStream's own cached logs as a third plane** (`UX-91`).
   Everything `bga` reads today requires deciding to capture *before*
   building. BuildStream already persists a timestamped per-element log
   for every artifact on every machine. That is the only path to
   retrospective analysis ("what did last night's unwrapped build
   do?"), longitudinal per-element trends, per-phase
   (configure/compile/install) splits with zero capture overhead, and
   frequency analysis of repeated operations across *builds* rather
   than within one. It composes with, not replaces, the wrapper — the
   certified floors keep requiring a real capture.

2. **Cache effectiveness as a first-class analysis** (`UX-92`). For
   the incremental builds that are every CI build, the cache is the
   dominant efficiency mechanism and the tool's entire cache story is
   "stop miscounting cached elements" (`UX-55`). Hit ratios per run
   and subtree, pull-vs-rebuild economics, trends over `UX-81`'s
   history — and above all **cache-key churn detection**: an element
   that rebuilds while its declared inputs are unchanged is plausibly
   BuildStream's largest real-world waste, is pure set arithmetic over
   data already in `graph.json` across two runs, and is invisible to
   every occupancy-based signal (a churning build can score as
   perfectly efficient). If one item in this list becomes the next
   `UX-45`-class capability, it should be this one.

3. **Timestamp/operation correlation heuristics** across those logs —
   the cheap approximations of Plane 2's redundancy findings
   (recurring identical operations across elements and builds) for
   environments where the tracer can't run. Folded into `UX-91`'s
   scope rather than filed separately; measure the persisted logs'
   timestamp quality first (`UX-06`'s lesson applies).

4. Further out, in the order the evidence suggests: the marginal gate's
   successor metric (per-element CPU stretch from Plane 2's `getrusage`
   data, once Plane 2 runs in CI routinely); remote execution (round
   1's item 4, still untouched, still real); and a many-core host
   capture (every number in ten rounds is from 4 cores).
