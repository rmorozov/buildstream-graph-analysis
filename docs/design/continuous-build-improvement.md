# The readers are real now: bga as one team's improvement loop

Written 2026-09-20, from the owner's answers in the rollout thread.
Every role in [`roles.md`](roles.md) was written from a positioning
statement; this document is what changes when four of them acquire
names, a fleet, a review pipeline and a budget.

**Serves:** R1 and R2 (the developers who will optimise their own
areas), R5 (the build and infrastructure team sizing agents), R4 (the
review gate), R8 (the manager reading the quality gate's build half).

**Status:** proposed - an argument, not a numbered Direction and not a
filing. No code changed. Section 8 lists the rows filed with it. It is
deliberately unnumbered for the reason section 9 of
[`in-step-parallelism.md`](in-step-parallelism.md) gives: `## Direction
21` in [`directions.md`](directions.md) reddens
`test_every_direction_names_its_reader.py`, whose numbering assertion is
exactly `range(1, 21)`, and wants a round-history row and an audit
document. Two documents now wait on that one-line move; a session
running a round takes it.

## 1. What the owner said

Four groups, in the owner's own order:

| group | what they will do with it | roles |
|---|---|---|
| developers | optimise the build in their area of responsibility | R1, R2 |
| build and infrastructure | size build agents from review and nightly builds - CPU, memory, **disk and network** | R5 |
| managers | watch the health of the build half of the quality gate | R8 |
| the review gate | catch efficiency regressions as early as possible | R4 |

And four constraints, which are the material circumstances every filing
below is shaped by:

- **Capture overhead budget: 15-25%** of time and resources. Within
  that, Plane 2 is wanted on *every* build type. The agents already
  carry BuildStream and `bubblewrap`.
- **Both resource forks.** Host-level *and* per-element. The field case
  is a local cache too small to hold the project's artifacts, where
  reaching for an artifact triggered a rebuild - so artifact sizes and
  agent cache capacity are both in scope, as is whether the network is
  the bottleneck for source and artifact fetching on a review build with
  the cache on.
- **Runs live in versioned directories**, as bundles, keyed by a build
  number whose form already separates the build types: nightly
  `27.0.0.<seq>`, review `27.0.999.<seq>`.
- **The gate says seconds.** Not only the diff-only verdict
  `--fail-on-inefficient-additions` publishes today: the owner wants
  "this PR made the build N seconds slower".

## 2. The contradiction this resolves

The tool's development has been rigorous and self-referential: 129
rounds, 885 closed rows, a guard for every claim, and every reader
modelled rather than observed. That method produced a tool whose
*internal* coherence is high and whose *external* evidence is a single
project's captures. `UX-884` is the shape of the problem in one row: it
is held open waiting for a field report, and no field existed to send
one.

Naming four real groups resolves it, and immediately re-orders the work.
Three of the four live on the across-build axis, which is the half
[`roles.md`](roles.md) still marks Partial or Gap for R5, R7 and R8. The
axis that has had 129 rounds of attention - one build, read deeply - is
the one group that needs no new code to start.

The second contradiction is not resolved by this document and should be
stated: the same method that made the tool trustworthy makes it slow to
answer a new reader. The rows below are chosen so that the first three
need no new capture format and no new contract version.

## 3. Instrument, or intervention

Until the jobserver, bga only measured. The jobserver mode changes the
build: it injects a token pool into sandboxes, and it has already cost a
minimal-sandbox breakage (round 126) and a GCC LTO ICE (`UX-878`).

The owner's resolution, adopted here: **the jobserver is a subtool with
a boundary.** It stays integrated with bga for the measurement that
justifies it - before and after, on the same agent - and it is built so
that it can later move into a separate project of BuildStream helpers
without bga losing an answer. Filed as `UX-901`.

Two consequences worth stating as rules rather than intentions:

- **bga never requires an intervention to answer a question.** A capture
  with the jobserver off must produce every number a capture with it on
  produces, minus the ledger the mode itself writes.
- **An intervention publishes its own contract.** What the subtool did
  is data in the capture (`UX-847`'s token ledger), not a fact only the
  subtool's own logs hold. That is Direction 7's rule applied to a
  component that acts rather than reads.

## 4. BuildStream-first, decoupled later

The owner's position: BuildStream first, and nothing prevents decoupling
the logic later. The seam that makes that true is already in the tree -
`bga.ingest` reads three contracts (`run-context/v9`, `graph/v9`,
`trace/v9`) and the analysis reads only those. The rule this document
adds is directional rather than architectural:

> New instrumentation lands on the **ingest** side of that seam, as a
> key in a read contract, never as a BuildStream fact the analysis
> layer knows how to fetch for itself.

Both resource filings below (`UX-896`, `UX-897`) are written that way:
BuildStream already knows the artifact sizes, the configured quota and
the bytes it transferred, so the work is to carry those into the run
directory, not to teach the analyzer about CAS.

## 5. Report, API and gate are one layer stack, not three products

The owner wants all three unblocked incrementally. They already are, and
the discipline that keeps them cheap is Direction 7's: a consumer never
derives its own analysis. So the order for every new answer in this
document is fixed:

1. a key in a published contract, with its units and its assumptions;
2. then a line in the report and the page;
3. then a gate verdict or an exit code, if a gate wants it;
4. and the API is what step 1 already produced - 25 versioned documents
   with `--schema` behind each, which is an API nothing outside bga
   consumes yet.

An answer that appears first as a report line and acquires a contract
key later is the drift this rule exists to prevent.

## 6. The evidence budget, and the one number nobody has

The rollout's binding unknown is the capture overhead. The repository's
only statement about it is a sentence in
[`real-project.md`](../guides/real-project.md): `--trace-opens` "runs on
a hot path", capture it deliberately. There is no percentage anywhere in
the tree:

```text
$ grep -rEn "[0-9]+(\.[0-9]+)?\s*%.{0,40}(overhead|slower|hook|tracer)" docs/guides/*.md docs/design/*.md
docs/design/directions.md:139:41% of it; run the Plane 2 tracer against it"  - and a Plane 2 mode that
```

One line, and it is about a fixture's share of something else. So the
owner's 15-25% budget is currently a question, and it decides whether
Plane 2 runs on every review build or only on nightlies - the widest
fork in the rollout. `UX-895` is that measurement, and it is first.

## 7. Fast wins are a deliverable, not a by-product

The owner's framing: build performance is a process that never ends, and
adoption needs stories that can be shown. That makes a showcase case a
first-class artifact with a shape, and this document states the shape as
a rule:

> **A showcase case is two captures.** The before, the change, the
> after, each with the command that produced it and the run it came
> from. A case that names a saving without the second capture is a
> projection, and bga already has a word for that (`whatif`) and refuses
> to confuse the two.

Two cases are already in hand and are filed as the first entries
(`UX-902`):

- **The lone element that uses eight cores.** The owner's LLVM element
  builds alone for about forty minutes and takes BuildStream's default
  `max-jobs` while the rest of the agent idles. That is exactly the axis
  argued in [`in-step-parallelism.md`](in-step-parallelism.md), whose
  first increment is filed as `UX-891`; the jobserver is the
  intervention half, and the pair is the strongest before/after the tool
  can currently show.
- **Redundant rebuilds.** `bga blast` already answers what a change to a
  repository, a path or an element rebuilds, and the monorepo keying
  question (`git` sources key on ref, `local` on content) is the usual
  cause. The case is a developer scenario, needs no new code, and can be
  captured this week.

## 8. What this declines, and what it files

Declined, on purpose: a monitoring system, a scheduler, a dashboard
service, and any answer about a fleet bga has not measured. The house
shape holds - measured facts, published contracts, a model with stated
assumptions on top.

Filed with this document:

| row | what it is | first? |
|---|---|---|
| `UX-895` | the capture's own overhead, measured in three arms | **yes** - it gates Plane 2 on review builds |
| `UX-896` | artifact sizes and cache capacity, so eviction is visible before it rebuilds | |
| `UX-897` | transfer bytes, so "the network" is a throughput and not an adjective | |
| `UX-898` | a comparison class is the host class *and* the build type | before `UX-899` |
| `UX-899` | the seconds-slower gate, against a band rather than a pair | |
| `UX-900` | a store assembled from the bundles CI keeps in versioned directories | |
| `UX-901` | the jobserver behind a subtool boundary | |
| `UX-902` | the showcase case file, and its two-capture rule | |

## 9. The guidelines this document states

Four, each one a sentence a later round can be held to:

1. **A comparison class is the host class and the build type together.**
   A review build compares against review builds. Blending is refused
   the way host classes already are (`UX-898`).
2. **A showcase case is two captures** (section 7).
3. **New instrumentation lands at the ingest seam** (section 4).
4. **An intervention is a subtool behind a boundary, and bga never
   requires one to answer a question** (section 3).
