# Active Backlog — User Scenarios & Workflow

Unlike `docs/backlog/progress-tracker.md` (spec-compliance backlog against `docs/spec/specification.md`, now closed), this backlog is about **how well `bga` actually serves its real user scenarios** - filed by walking through the tool's main use cases against its current CLI/docs and finding real friction, not spec gaps.

Same verification discipline as the closed backlog (see `docs/contributing/fixing-guide.md`): one task, one commit, a real pasted command + output before marking 🟢. Don't trust a claim of "done" (here or anywhere) without independently re-verifying it.

## Status Legend

| Status | Meaning |
|---|---|
| 🔴 Not Started | No work begun |
| 🟡 In Progress | Work underway, or claimed-done-but-unverified |
| 🟢 Done | Acceptance test run for real, output pasted into the task file |
| ⚪ Blocked / Deferred | Needs a product decision, or waiting on something else |

## Index

240 scenarios: **7 open**, 233 closed.
Closed rows live in [closed.md](closed.md), verbatim.

| Topic | Open | Total |
|---|---|---|
| capture | 0 | 50 |
| analysis | 0 | 49 |
| contracts | 0 | 23 |
| viewer | 0 | 40 |
| cli | 0 | 4 |
| store | 2 | 26 |
| docs | 5 | 16 |
| guards | 0 | 32 |

## Open scenarios

One line per scenario: the index job. The narrative lives in the
task file, which is the only place it ever lived twice.

| ID | Scenario | Topic | Priority | Serves | Status |
|---|---|---|---|---|---|
| UX-92 | [cache effectiveness — hits, misses, churn, trends — is invisible to the tool](UX-0092-cache-effectiveness-is-invisible-to-the-tool.md) | store | Medium | — | 🟡 |
| UX-96 | [the baseline set exists, but assembling it is a scavenger hunt](UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md) | store | Medium | — | 🟡 |
| UX-236 | [the front door is a round behind](UX-0236-the-front-door-is-a-round-behind.md) | docs | High | R1, R8 | 🔴 |
| UX-237 | [documentation debt has no way into the backlog](UX-0237-documentation-debt-has-no-way-into-the-backlog.md) | docs | Medium | R8 | 🔴 |
| UX-239 | [the context map is from the first week](UX-0239-the-context-map-is-from-the-first-week.md) | docs | High | all | 🔴 |
| UX-240 | [a session has no cheap entry point](UX-0240-a-session-has-no-cheap-entry-point.md) | docs | Medium | all | 🔴 |
| UX-241 | [architecture review has no cycle](UX-0241-architecture-review-has-no-cycle.md) | docs | Medium | R8 | 🔴 |

## UX-236..UX-241: the twenty-ninth round — the process, measured (2026-08-23)

Round 28 landed nine filings and the round's own cost became the
subject. Six items, all of them about how work is done here rather than
about what the tool says:

- **`UX-238`** is the lever. `pytest tests/` is `373s`; split by
  measured per-file total, **160 files cost 18.2s** and 7 cost 159s. An
  inner loop that runs everything spends six minutes to learn what
  twenty seconds would say. Google's small/medium/large/enormous, with
  the tiers assigned from the measurement.
- **`UX-239`** — the fixing guide's context map says
  `tests/test_e2e.py   only existing test file`. There are 220. It also
  names one entry ritual for six different kinds of work; the user's
  observation about *streams* is what that section is missing.
- **`UX-236`** — `UX-233` fixed the architecture document and left the
  front door: three commands and a flag from round 28 appear in neither
  `README.md` nor `docs/README.md`.
- **`UX-237`** — documentation a change needs and does not get has
  nowhere to go. A bug becomes a tracker row; a doc gap becomes a
  comment, or nothing.
- **`UX-240`** — skills, scoped narrowly to the procedures that get
  re-derived every session and are mechanical: verify, falsify,
  measure. Not to judgment.
- **`UX-241`** — the architecture drifted a whole axis before anyone
  noticed. Feature audits have a cadence; documentation review does
  not, and that asymmetry is the finding.

Order: `UX-238` first — everything after it is cheaper — then `UX-239`,
then `UX-236` and `UX-237` together, then `UX-240` on top of both, and
`UX-241` last because it is the cycle that keeps the rest true.

## UX-227..UX-234: the twenty-seventh audit round — the map is bigger than the page (2026-08-23)

Round 27 verified the eighteen-commit landing (the round-23 slate
plus the sibling's own rounds 24-26, UX-215..226), then did what a
feature audit cannot: asked *who* the tool answers to. The user's
positioning — bga as the fact-based entry point for a team with
partly contradictory interests — became the
[role model](../../design/roles.md): eight roles, and the finding
that twenty-six rounds served four of them thoroughly (the local
optimizer, the recipe author, the graph owner, the CI gatekeeper)
and left four nearly unserved (the capacity operator, the CI user,
the release manager, the engineering lead). The fourth external
review's verdict — the presentation Pareto is exhausted — was
accepted for the served roles and challenged as a map error: it
reached the end of one role's journey, not the end of the tool. Its
strongest idea (publish the claim→evidence→query chain) became
Direction 8 and [`UX-229`](UX-0229-publish-why-bga-believes-what-it-believes.md);
its workspace/IDE trajectory was declined with round 24's own
export-survivability argument; its two cheap items were adopted
([`UX-227`](UX-0227-why-is-this-ranked-first.md),
[`UX-228`](UX-0228-focus-is-an-investigation-not-a-dimmer.md)); its
what-if sketch was adopted minus the client-side simulator it
warned against ([`UX-230`](UX-0230-what-if-you-could-choose-the-fixes.md)).
The unserved half opened Direction 9 and its first contract
([`UX-234`](UX-0234-the-store-speaks-for-more-than-one-build.md)).
The round's third strand is the repository itself: traceability
([`UX-231`](UX-0231-every-direction-names-its-reader.md)), the
backlog split ([`UX-232`](UX-0232-a-backlog-you-can-navigate-at-234-items.md)),
and the architecture/spec drift guard
([`UX-233`](UX-0233-the-architecture-document-meets-the-viewer-axis.md)).
Verification of the eighteen-commit landing returned twenty for
twenty, with the two hollow guards and the underscore probe filed as
[`UX-235`](UX-0235-the-order-the-page-asserts-and-the-order-it-has.md).
Full narrative: [`../../audits/round-27.md`](../../audits/round-27.md).

## UX-112..UX-124: the twelfth audit round (2026-08-19)

Round 12 re-verified the sibling session's fifteen-item range (UX-60,
UX-80's acceptance, UX-93, UX-95, UX-96, UX-99..UX-104, UX-105..UX-108,
plus self-filed UX-109..UX-111) the same way rounds 10 and 11 worked:
every filed acceptance re-run against retained captures and fresh real
builds, a commit-by-commit claims review including a line-level code
review of `spine.c`, and a live inspection of the capture refs,
workflows and the new `bga baseline`/`bga cache-trend` machinery. Full
narrative and the **MVP verdict**:
[`../../audits/round-12.md`](../../audits/round-12.md).

The scoreboard: ten of fifteen VERIFIED outright (UX-93's churn
conditioning survived every live case including its own true-positive;
UX-108's decision-rule discipline is the round's model), three PARTIAL
on verification-discipline grounds (recorded in their files), two
reopened — `UX-100` (the merge candidate has never fired on real data)
and `UX-106` (a measured-failing acceptance clause shipped under 🟢,
with implementation-level causes found by code review: `UX-117`..
`UX-119`). The round's own hands-on found `UX-112` (the spine×opens
combination costs **+31-44%** while each alone is ~free — and the
combination is the workflow's default configuration) and the
baseline-set edges (`UX-114`). Forward-looking: Direction 5 files the
CI comment renderer (`UX-115`), the joint capacity answer (`UX-116`),
and census-targeted spine coverage (`UX-113`).

## UX-98..UX-104: linting, and the Direction 3 decomposition (2026-08-18)

Two sources, one batch. `UX-98` is a process fix with a live defect
behind it: the round-11 status table rendered broken in GitHub's viewer
(the escape discipline is now style-guide rule 8; the linter makes it
enforced). `UX-99`..`UX-104` decompose
[`design/directions.md`](../../design/directions.md) **Direction 3**
into implementable tasks — each carries its design in `Required Fix`,
its evidence already verified in a round, and an acceptance test
against data that exists (the round-11 log tree, the retained fdsdk
refs, the dual captures).

The dependency order that falls out: `UX-99 → UX-100` (measure the
toll, then advise on granularity), `UX-93 → UX-101/UX-103` (honest
churn labels before anything trends or ranks on them), `UX-96 →
UX-103` (the refs helper feeds the trend), `UX-83 → UX-104` (the
Plane 2 channel carries the memory envelope). `UX-101` is the round's
High: it answers a question (**which element costs the team the most
per week?**) that no single-run analysis can, from data already on
every machine.

## UX-93..UX-97: the eleventh audit round (2026-08-18)

Round 11 re-verified round 10's sixteen fixes the way the header of
this file demands — every filed acceptance test re-run for real, on the
retained round-10 captures where they existed and on fresh real builds
where they did not, plus a commit-by-commit claims review and a live
inspection of the new capture refs. Full narrative:
[`../../audits/round-11.md`](../../audits/round-11.md).

The score: **fourteen of sixteen hold up**, several impressively — the
marginal gate's scale-invariance is a pinned two-scale test, the cold
capture falsified one of its sibling's findings before this audit could,
and the restructuring synthesis out-reasons the walkthrough example's
own "optimized" answer. The failures are concentrated in *verification
discipline*, not code: `UX-80` is reopened (acceptance never run — its
tests cannot fail if the join breaks), `UX-85`'s record didn't exist
until this round wrote it, `UX-82`/`UX-83` shipped verified against
substitutes for the captures their acceptance named (both now verified
on the named captures, by this round, in their files). One genuine
defect survived contact with real builds (`UX-93` — churn without
cache continuity, the round's one High), two design debts were taken
knowingly and are now named (`UX-94`, `UX-96`), one is presentation
(`UX-95`), and five self-inflicted doc regressions from the fix round
itself are batched as `UX-97`.

## UX-77..UX-92: the tenth audit round (2026-08-18)

Filed from a fresh full-cycle audit: a claims-vs-reality pass over every
substantive README/cli.md claim, a real hands-on macro→micro
optimization cycle on `examples/06` (dual-plane captures of the
baseline, a macro-only-fixed variant, and `optimized/` — **27.9s →
25.0s → 16.9s** on a real 4-core sandbox host), a grow-the-project
gate experiment (two elements added well vs badly), and a review of the
`captures/fdsdk-latest` branch plus all 24 runs of the capture
workflow. Full narrative, protocol and verdict:
[`../audit-round-10.md`](../../audits/round-10.md); the design argument the
round feeds: [`../design-directions.md`](../../design/directions.md).

The round's shape in one sentence each:

- **The analysis held up; the packaging and the promises did not.**
  Every number re-verified was right (floors, attribution identity,
  gate exit codes, the fdsdk report reproduced byte-for-byte in 0.27s),
  while the first documented command a new user runs crashes with a raw
  traceback (`UX-77`), and three separate documents promise a refusal
  the code deliberately downgraded to a warning (`UX-78`).
- **The walkthrough works — because the user supplies the synthesis.**
  Both planted problems were *found* (the `notparallel` finding is
  exemplary), but the macro fix's conclusion is never drawn from its
  own measured evidence (`UX-82`), and Plane 1's capacity advice
  actively points away from the fix `correlate` names on the same
  capture (`UX-83`).
- **The CI story's remaining gaps are now precise.** The efficiency
  gate discriminates exactly as designed at 11 elements and provably
  dilutes at 90 (`UX-79`); the capture infrastructure destroys the
  history the gate's own documentation requires (`UX-81`, `UX-86`,
  `UX-90`); and a gate can silently stop gating (`UX-87`).
- **Two new capability directions** came out of asking what the tool
  could see within a few more cycles: BuildStream's own cached logs as
  a retrospective, longitudinal third plane (`UX-91`), and cache
  effectiveness — hits, churn, trends — as a first-class analysis
  (`UX-92`).
