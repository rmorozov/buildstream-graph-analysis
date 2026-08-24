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

| # | role | what they want | what they fear | bga today |
|---|---|---|---|---|
| R1 | **The local optimizer** — a developer inside the edit-build-run-debug cycle | the shortest path from "my build is slow" to a fix worth making; the inner loop fast again | spending a day optimizing the wrong element | **Served best.** The whole macro→micro cycle: `doctor`, `snapshot`, headline, ranked actions, what-if plan, blast, focus, Perfetto handoff |
| R2 | **The recipe author** — owns elements and their sources | the cost of *their* element: sandbox tax, achieved parallelism, what a change to their repo rebuilds | their local fix pessimising someone else's build | **Served.** The element object (`correlate/v1`), blast by resource, element history, Plane 2 lanes |
| R3 | **The graph owner** — owns the project's dependency shape | the structural answers: critical path, floors, what the graph makes impossible, junction/monorepo shape | a structure argument lost for lack of evidence | **Served.** Floors, chain-bound diagnosis, criticality, Direction 6's source axis — and, from round 32, the graph's *shape*: which elements reach most of it by design rather than by accident (`UX-258`) and the blast-radius distribution behind that judgement (`UX-259`) |
| R4 | **The CI gatekeeper** — owns the regression gate | "did this PR make the build slower?" answered honestly | a gate that cries wolf, or one that waves regressions through | **Served.** Baselines, noise band, disputed region, culprits, exit codes, the CI comment |
| R5 | **The CI owner / capacity operator** — owns the fleet the builds run on | maximum concurrent builds per unit of hardware; utilization of CPU, memory, disk, network; cache infrastructure that earns its cost | buying machines that queueing would have solved, or the reverse | **Gap.** bga measures *one build's* occupancy and idle; nothing aggregates across builds, models concurrency, or prices a builder |
| R6 | **The CI user** — a contributor waiting on a verdict | latency: their result now, their build prioritised | an afternoon lost to a queue nobody can explain | **Gap.** The queue is invisible: bga's clock starts when the build does, and the waiting the user actually experiences happens before that |
| R7 | **The release manager** — owns dates | predictability: worst-case build time, drift across a release cycle | the release build that takes three hours the one day it matters | **Partial.** The trend and baselines see drift in one store; nothing speaks about variance or worst-case as first-class answers |
| R8 | **The engineering lead** — owns where effort goes | evidence for prioritisation: what build time costs the team, what a fix is worth in engineer-hours saved | funding infrastructure by anecdote | **Partial.** Headline and what-if price a fix in *build seconds*, for one project; nothing aggregates across a team or converts to anything a budget speaks |

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

## The gap, stated plainly

Everything bga answers today is answered **within one build** (or one
store's history of one project's builds). R1-R4 live there, and
twenty-six rounds have served them to the point where an external
reviewer correctly calls the presentation-layer Pareto exhausted.
R5-R8's questions live **across builds**: distributions, aggregates,
concurrency, queues, money. That axis has almost no instrumentation —
not because it is hard to see, but because nobody had written down
that those readers exist.

What it is *not*: a monitoring system, a scheduler, or a Perfetto for
fleets. The house shape for this axis is the same as for every axis
before it — measured facts (build profiles bga already captures),
published contracts, and a model with stated assumptions on top
(queueing theory needs arrival rates and service-time distributions;
bga's captures *are* service-time distributions).

## Traceability

Three rules, enforced by convention now and by guards when the
backlog restructure (`UX-232`) lands:

1. **Directions name their roles.** Every direction in
   [`directions.md`](directions.md) states which roles it serves —
   retroactively for 1-8 (`UX-231`), at birth for new ones.
2. **Filings name their roles.** A backlog task carries a `Serves:`
   line naming role ids from this table, so the backlog can answer
   "what are we doing for R6" with grep.
3. **This table is maintained, not archaeological.** A new role or a
   changed gap lands here in the same commit as the work that changes
   it — the same rule the status table already follows.

Current direction coverage, for orientation: Directions 1-7 serve
R1-R4 (Direction 2 is R4's; Direction 6 serves R2/R3; Direction 7
serves every *reader* but adds no new answered question). Direction 8
(the provenance model) serves every role that has to *trust* an
answer secondhand — R4's CI comment and R8's prioritisation case most
of all. Direction 9 is R5/R6's first.
