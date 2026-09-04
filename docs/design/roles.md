# Who bga answers to: the role model

Written 2026-08-23 (round 27), from the user's positioning statement.
This document exists so that every direction, audit round and backlog
filing can say *whose* problem it solves — and so the gaps stop being
invisible: a tool audited twenty-six rounds deep can still be serving
two roles brilliantly and six not at all, and nothing in a
feature-by-feature audit will ever say so.

## The positioning this document pins

`bga` is the **entry point for build-efficiency analysis for a team
whose interests partly contradict each other**. It identifies
improvement opportunities and prices them, always from facts — logs,
traces, and mathematical models with stated assumptions — and hands
the depth work to tools that already do it well (Perfetto for
execution detail; BuildStream's own logs for history). It does not
re-implement them. Where two roles want opposite things, `bga`'s job
is not to pick a side; it is to make the trade-off measurable, so the
argument happens over numbers instead of adjectives.

Two consequences, both already house rules in other clothes:

- **Every answer is a published fact.** A role's question is served by
  a published, versioned payload — never by a consumer deriving its
  own analysis (Direction 7's rule, stated for people instead of
  pages).
- **Depth is a handoff, not a feature.** The moment a question needs
  per-process timelines or SQL over spans, the answer is a
  *well-aimed* Perfetto handoff, not a new renderer.

## The roles

Two were always explicit — the guides are organised around them. The
rest were implicit or absent, which is what this table is for.

| # | role | what they want | what they fear | bga today, and what served it |
|---|---|---|---|---|
| R1 | **The local optimizer** — a developer inside the edit-build-run-debug cycle | the shortest path from "my build is slow" to a fix worth making; the inner loop fast again | spending a day optimizing the wrong element | **Served best.** The whole macro→micro cycle: `doctor`, `snapshot`, headline, ranked actions, what-if plan, blast, focus, Perfetto handoff — and since `UX-407` the terminal carries the finding that *is* the answer rather than pointing at the page |
| R2 | **The recipe author** — owns elements and their sources | the cost of *their* element: sandbox tax, achieved parallelism, what a change to their repo rebuilds | their local fix pessimising someone else's build | **Served.** The element object (`correlate/v2`), blast by resource, element history, Plane 2 lanes — focus as an investigation rather than a dimmer (`UX-228`), and the lanes the terminal and the viewer now agree about (`UX-329`) |
| R3 | **The graph owner** — owns the project's dependency shape | the structural answers: critical path, floors, what the graph makes impossible, junction/monorepo shape | a structure argument lost for lack of evidence | **Served.** Floors, chain-bound diagnosis, criticality, Direction 6's source axis — and, from round 32, the graph's *shape*: which elements reach most of it by design rather than by accident (`UX-258`) and the blast-radius distribution behind that judgement (`UX-259`). From round 73, one finding that reads the **graph and no duration at all**: how many dependency stages it has and how many elements its widest holds, which is the ceiling on concurrency no capacity lifts (`graph-width`, `UX-478`) - filed because on a six-element serial chain, the one project whose whole defect is the graph, every R3 finding was a function of measured durations and the reader was dropped |
| R4 | **The CI gatekeeper** — owns the regression gate | "did this PR make the build slower?" answered honestly | a gate that cries wolf, or one that waves regressions through | **Served.** Baselines, noise band, disputed region, culprits, exit codes, the CI comment — refusing a comparison across a contract move (`UX-250`) and reading a release as a contract state rather than a date (`UX-251`) |
| R5 | **The CI owner / capacity operator** — owns the fleet the builds run on | maximum concurrent builds per unit of hardware; utilization of CPU, memory, disk, network; cache infrastructure that earns its cost | buying machines that queueing would have solved, or the reverse | **Partial.** Something does aggregate across builds: `bga snapshot --aggregate` publishes `store-aggregate/v1` — min/median/p95/max/MAD per host class over finished runs, blending refused rather than printed (`UX-234`) — and `bga sweep --format json` publishes `sweep/v1`, the per-resource capacity sweep with its knee (`UX-339`). Still absent, and the reason this row is not **Served**: no queueing model, no arrival rates, no price on a builder |
| R6 | **The CI user** — a contributor waiting on a verdict | latency: their result now, their build prioritised | an afternoon lost to a queue nobody can explain | **Gap, now filed.** The queue is invisible: bga's clock starts when the build does, and the waiting the user actually experiences happens before that. Round 83 filed the measurement it would stand on - a requested-at instant beside the started-at (`UX-594`) - so R6 is the one row whose cell names an *open* item |
| R7 | **The release manager** — owns dates | predictability: worst-case build time, drift across a release cycle | the release build that takes three hours the one day it matters | **Partial.** The trend and baselines see drift in one store, and variance and worst-case are first-class answers: `store-aggregate/v1` publishes p95, max and a MAD per host class, nearest-rank so every figure is one a build actually took (`UX-234`), and `UX-303` draws the spread rather than tabulating it. Still absent: drift across a *release cycle* as one answer, and any predicted worst case rather than a measured one |
| R8 | **The engineering lead** — owns where effort goes | evidence for prioritisation: what build time costs the team, what a fix is worth in engineer-hours saved | funding infrastructure by anecdote | **Partial.** Headline and what-if price a fix in *build seconds*, for one project — with the reason a thing is ranked first (`UX-227`) and a price on a chosen *set* of fixes (`UX-230`); nothing aggregates across a team or converts to anything a budget speaks |

## The contradictions — the reason a role model earns its file

The user's observation, generalised: several of these roles want
opposite things, and a tool that only ever serves one side of each
pair is taking sides silently.

| tension | one side | the other | what "measurable" looks like |
|---|---|---|---|
| **throughput vs latency** | R5 wants utilization high — full machines, deep queues, batching | R6 wants latency low — idle headroom, priority, no queue | one model, two readouts: given measured build profiles, N builders and M builds/day, the utilization *and* the queue-time distribution. The trade-off becomes a curve, not an argument |
| **local fix vs global path** | R2 optimises their element | R3 owns the chain — an off-path element's win moves nothing | already measurable: `share_of_path`, latent heavies, blast. The model's job is to say *whose* fix moves the build |
| **cache as accelerator vs cache as capacity** | R1/R6 want hit rates (their time back) | R5 pays for storage, eviction, network egress | Plane 3 knows the hits; nothing prices the misses against the infrastructure that would remove them |
| **gate strictness vs contributor velocity** | R4 wants tight bands | R6 eats every false positive as a re-run | the disputed region and noise band already are this trade-off, quantified — the one contradiction bga has already made measurable, and the pattern for the others |

## The gap, stated plainly (written round 27; re-measured round 83, 2026-09-03)

Everything bga answers today is answered **within one build** (or one
store's history of one project's builds). R1-R4 live there, and
twenty-six rounds have served them to the point where an external
reviewer correctly calls the presentation-layer Pareto exhausted.
R5-R8's questions live **across builds**: distributions, aggregates,
concurrency, queues, money. That axis has almost no instrumentation —
not because it is hard to see, but because nobody had written down
that those readers exist.

Round 83 re-measured it (`UX-580`). "Four served thoroughly, four
barely" is no longer the shape: the across-builds axis has an
instrument, and **R6 alone has no filing at all.**

```text
$ git grep -l "🟢.*\*\*Serves:\*\*[^|]*R5" -- 'docs/backlog/scenarios/UX-*.md' | wc -l
12
```

Closed filings naming each role, measured that way over 587 scenario
files on 2026-09-03: R1 75 · R2 15 · R3 6 · R4 5 · R5 12 · R6 0 ·
R7 21 · R8 23. The dated figures rot; the *shape* does not, because
`tests/unit/test_the_roles_table_names_who_serves_it.py` recomputes it
and reads each row's last cell against it.

R5 and R7 moved because `UX-234` and `UX-339` landed and their rows
here did not: this table said "nothing aggregates across builds" for
four rounds after `bga/store_aggregate.py` began doing exactly that.
That is what rule 3 below is for, and why it is now read by a guard
rather than trusted.

What it is *not*: a monitoring system, a scheduler, or a Perfetto for
fleets. The house shape for this axis is the same as for every axis
before it — measured facts (build profiles bga already captures),
published contracts, and a model with stated assumptions on top
(queueing theory needs arrival rates and service-time distributions;
bga's captures *are* service-time distributions).

## Traceability

Four rules. The first three were convention when this file was
written; the fourth is the payload:

1. **Directions name their roles.** Every direction in
   [`directions.md`](directions.md) states which roles it serves —
   retroactively for 1-8 (`UX-231`), at birth for new ones.
2. **Filings name their roles.** A backlog task carries a `Serves:`
   line naming role ids from this table, so the backlog can answer
   "what are we doing for R6" with grep.
3. **This table is maintained, not archaeological.** A new role or a
   changed gap lands here in the same commit as the work that changes
   it — the same rule the status table already follows. Convention
   until round 83, when it had been broken for four rounds and nothing
   said so; now every row's last cell must name at least one **closed**
   filing whose own `Serves:` line carries that role, and a role with
   no closed filing must name none. Derived from rule 2's counts, so
   the next mechanism that serves a role cannot leave a row stale
   (`UX-580`, `test_the_roles_table_names_who_serves_it.py`).
4. **The report names its readers.** Since `UX-372`, every finding in
   `analyze/v6` carries a `reader` — one of R1–R5, this table's own ids
   — and the document publishes a `readers` index saying, for each
   reader this run has something for, their question and the finding
   that is their biggest lever on it. So "what does this build say to
   the person who owns the machines" is a lookup rather than a read of
   eleven findings, and the viewer's decision panel routes by it. R6–R8
   are absent from that vocabulary for the reason the gap section above
   gives: their questions live across builds, and one run's findings
   have nothing to put under them.

Current direction coverage, for orientation: Directions 1-7 serve
R1-R4 (Direction 2 is R4's; Direction 6 serves R2/R3; Direction 7
serves every *reader* but adds no new answered question). Direction 8
(the provenance model) serves every role that has to *trust* an
answer secondhand — R4's CI comment and R8's prioritisation case most
of all. Direction 9 is R5/R6's first.
