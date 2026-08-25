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

305 scenarios: **14 open**, 291 closed.
Closed rows live in [closed.md](closed.md), verbatim.

| Topic | Open | Total |
|---|---|---|
| capture | 2 | 52 |
| analysis | 0 | 50 |
| contracts | 0 | 35 |
| viewer | 6 | 74 |
| cli | 0 | 4 |
| store | 3 | 27 |
| docs | 3 | 29 |
| guards | 0 | 39 |

## Open scenarios

One line per scenario: the index job. The narrative lives in the
task file, which is the only place it ever lived twice.

| ID | Scenario | Topic | Priority | Serves | Status |
|---|---|---|---|---|---|
| UX-294 | [eleven viewer modules are named in no document](UX-0294-eleven-viewer-modules-are-named-in-no-document.md) | docs | Low | — | 🔴 |
| UX-295 | [`whatif/v1` is published, and named in no guide](UX-0295-whatif-v1-is-in-no-guide.md) | docs | Low | R5, R7 | 🔴 |
| UX-297 | [extraction streams, and the monolith retires](UX-0297-extraction-streams-and-the-monolith-retires.md) | capture | High | R1, R2 | 🟡 |
| UX-298 | [the timeline speaks Perfetto, natively](UX-0298-the-timeline-speaks-perfetto-natively.md) | capture | High | R1, R2 | 🔴 |
| UX-299 | [a handoff that does not carry the trace in its hands](UX-0299-a-handoff-that-does-not-carry-the-trace-in-its-hands.md) | viewer | Medium | R1 | 🔴 |
| UX-300 | [what a two-gigabyte snapshot does to a store](UX-0300-what-a-two-gigabyte-snapshot-does-to-a-store.md) | store | Medium | R1, R5, R7 | 🔴 |
| UX-301 | [the ordering authority moved and left its old uniform](UX-0301-the-ordering-authority-moved-and-left-its-old-uniform.md) | viewer | Low | — | 🔴 |
| UX-302 | [the mapping made law — no raw JSON that is not on purpose](UX-0302-the-mapping-made-law.md) | viewer | High | R1 | 🔴 |
| UX-303 | [the shape before the rows — sparklines and density strips](UX-0303-the-shape-before-the-rows.md) | viewer | Medium | R1, R7 | 🔴 |
| UX-304 | [dark first, with two grades of token](UX-0304-dark-first-with-two-grades-of-token.md) | viewer | Medium | R1 | 🔴 |
| UX-305 | [emphasis is a budget, spent once per block](UX-0305-emphasis-is-a-budget.md) | viewer | Medium | R1 | 🔴 |
| UX-306 | [the visual contract joins the tree it governs](UX-0306-the-guide-joins-the-tree.md) | docs | Low | — | 🔴 |
| UX-92 | [cache effectiveness — hits, misses, churn, trends — is invisible to the tool](UX-0092-cache-effectiveness-is-invisible-to-the-tool.md) | store | Medium | — | 🟡 |
| UX-96 | [the baseline set exists, but assembling it is a scavenger hunt](UX-0096-the-baseline-set-exists-but-assembling-it-is-a-scavenger-hunt.md) | store | Medium | — | 🟡 |

## UX-302..UX-306: the forty-first round — the page gets a visual contract (2026-08-25)

A design round while Direction 15 executes. The user's brainstorm —
no raw JSON unless deliberate, sparklines widely, a distribution
beside every long table, a pattern→control mapping, emphasis and
color rules, dark first — became
[`styleguide.md`](../../design/styleguide.md) and Direction 16.
Measured before ruled: `UX-267` had already won the raw-JSON war
except the labeled fold; the palette validator found the dark
tokens above the mark-lightness band and an adjacent amber↔green
CVD failure in light. Challenged where invited: dark-only became
dark-first with a print stylesheet; the density strip's
self-building draws the no-arithmetic line at "geometry yes,
printed derived numbers no"; the sibling's table folds were kept —
the missing thing was the shape of the whole, not a new mechanism.
Filed as [`UX-302`](UX-0302-the-mapping-made-law.md)..[`UX-306`](UX-0306-the-guide-joins-the-tree.md).
Full narrative: [`../../audits/round-41.md`](../../audits/round-41.md).

## UX-296..UX-301: the fortieth round — a snapshot bigger than RAM (2026-08-25)

The field showstopper: a real dual-plane capture at ~2 GB
(`plane2.json` 1.5 GB), on which `bga view` freezes and dies of
memory. Round 40 reproduced it synthetically and measured every
load path: the monolith parses at 2.9× bytes-to-RAM and the view
pays it twice before the socket exists; the store walk re-parses
every snapshot for two scalars; the merge step reads the
decompressed raw log as one string at 6.3× — ~30 GB projected. Two
architecture facts: ~95 % of the monolith is a `"processes"` list
no production reader consumes, and `UX-168`'s streaming fix never
reached the converter the view calls. The user's proposal — adopt
Perfetto's protobuf trace format — became Direction 15 with seven
rules (capture computes/view serves; events are a stream; the
artifact is TrackEvent via a stdlib emitter; aggregates not
events; the handoff inverts to the deep link; RAM is a guarded
budget), decomposed as
[`UX-296`](UX-0296-the-view-that-parses-nothing.md)..[`UX-300`](UX-0300-what-a-two-gigabyte-snapshot-does-to-a-store.md).
The sampled verification of rounds 28-39 returned six for six with
one superseded acceptance filed as
[`UX-301`](UX-0301-the-ordering-authority-moved-and-left-its-old-uniform.md).
Full narrative: [`../../audits/round-40.md`](../../audits/round-40.md).

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
  `tests/test_e2e.py   only existing test file`; `tests/unit/` alone
  holds 218. It also names one entry ritual for six different kinds of
  work; the user's observation about *streams* is what it is missing.
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
All six are done; their rows are in [closed.md](closed.md).

`UX-245`..`UX-247` are what `UX-241`'s **first review** found, which is
the item working rather than a coincidence: the architecture's CLI
table is two shipped subcommands behind, the end-to-end guide never
reaches the command for its own last step, and the architecture's
Verification Log is stale about its own currency.
[`../../audits/architecture-review.md`](../../audits/architecture-review.md)
is the round type, the checklist and the log; the cadence is a guard,
not a memory.

`UX-242`..`UX-244` were filed *by* `UX-237`'s new rule, on its first
application: three round-28 mechanisms whose only documentation was a
docstring or a payload note. They are what the rule is for, and the
fact that they had to be filed by hand in the round that wrote the rule
is the measurement of how long they would otherwise have waited.

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

## UX-248..UX-252: the thirtieth round — releases as contract states (2026-08-24)

The user's observation, and it has two halves that are easy to
conflate. **`bga` reads its own past output as input** — `@last`, the
baseline set, `cache-trend`, `store-aggregate` — and nothing an
artifact records says which build of the tool wrote it. And the
"what changed since I installed this" document does not exist: the
material is 3,549 lines of audit rounds and 789 lines of closed rows,
all organised by when the work happened rather than by what a consumer
sees. [Direction 10](../../design/directions.md) argues both.

- **`UX-248`** is the prerequisite and the surprise: 9 contracts are
  stamped in the code, `schemas.names()` knows 7, and **`sources/v1`
  is in no registry and no guard at all** — while being written to
  `sources.json` in every run directory and read back. The same
  "a guard that names one file will not see the second" pattern
  `UX-233` was filed against, one level up.
- **`UX-249`** — the producer stamp. Recording only; no refusal, so
  the record lands before the policy that reads it.
- **`UX-250`** — the policy: refuse when a *contract the comparison
  depends on* moved, not when the package version differs. A refusal
  that fires on every upgrade gets switched off.
- **`UX-251`** — `CHANGELOG.md`, and a version **derived** from the
  contract delta with a guard on the derivation. It consumes
  `UX-241`'s review rather than adding a second doc-sweep trigger.
- **`UX-252`** — the notes' body is generated from the closed rows; the
  head is written. A hand-written body would be the third copy of one
  fact.

Order: `UX-248` first — nothing else can enumerate contracts without
it — then `UX-249`, then `UX-251`, then `UX-250` and `UX-252`, which
both read what the first three built.

All five are done, and `0.2.0` is the first recorded release: see
[`../../../CHANGELOG.md`](../../../CHANGELOG.md).

## UX-254..UX-257: the thirty-first round — the report you can actually read (2026-08-24)

Reported from a real run after `0.2.0` merged, and **reproduced on
`main` rather than taken on trust** — the report was current, not a
stale export. Measured in a real browser on a 1,202-element run:

```text
viewport      nav.toc   % of screen   first content at   % of screen
1280x800      573px     71.6%         y=701              87.6%
1440x900      573px     63.6%         y=701              77.8%
1920x1080     573px     53.0%         y=701              64.9%
```

- **`UX-254`** — `.toc` is `position: sticky` *in the reading column*,
  so it both pushes content down 573px and covers 573px of every screen
  after a scroll; its 54 flex-wrapped links inline ~24 element names,
  which is why it looks like content; and `insertBefore(…,
  body.firstChild)` puts it above the run identity.
- **`UX-255`** — the heading arrives at y=630, after the navigation,
  and carries less than the footer does.
- **`UX-256`** — the user's "checker if everything is collapsed by
  default". It is not, deliberately: 3 of 49 `<details>` open and all
  12 sections open, both with reasons already written. Nothing asserts
  either, so drift in either direction is silent.
- **`UX-257`** — the recheck for overlap was done by hand and **cannot
  currently be a guard**: the viewer harness is a DOM shim with no
  layout engine, which is what let `UX-235`'s reversed document survive.
  The instrument is the decision to argue.

Order: `UX-254` first, then `UX-255` inside the layout it creates, then
`UX-256`; `UX-257` last, because it is the argument about what can hold
the other three.

`UX-254`, `UX-255` and `UX-256` are done. **`UX-257` is deliberately
still open**: the layout it would guard now exists, the geometry is
measured in a browser and recorded in each Outcome, and what the
guards hold is the *mechanism* rather than the pixels. Choosing the
instrument — a browser in CI, or the CSS contract and a stated blind
spot — is an argument, not an implementation, and it should be made
rather than defaulted into.

## UX-258..UX-262: the thirty-second round — a ranking says what to do (2026-08-24)

Reported from a real project: the blast analysis ranks
`linux_base_image.bst`-shaped elements first, which is true and
useless. Reproduced and measured on a 1,202-element run, plus a
122-deep one for the layout half.
[Direction 11](../../design/directions.md) argues all of it.

```text
next_steps[0]  "toolchain.bst is the first thing to fix"
toolchain.bst  downstream 1201  kind "import"  is_structural_kind TRUE

blast radius distribution, 1202 elements:
  p10 0   p50 30   p80 293   p90 465   p95 575   p99 682   p100 1201
positions 2-12:  753 753 739 727 721 720 712 709 706 702 697
```

- **`UX-258`** — the ranking includes structural kinds. `findings.py`
  applies the right rule one function away (`_criticality_findings`
  excludes them, citing `UX-76`); the blast ranking never got it.
- **`UX-259`** — `753 downstream` has no scale. It is p99.9 here and
  unremarkable in a graph of forty thousand, and the number is what
  travels into a ticket. Eleven entries inside an 8% spread are
  presented as an ordered list of what to do first.
- **`UX-260`** — where else a percentile belongs, argued per quantity
  rather than applied everywhere. Duration, sandbox tax and process
  count yes; share-of-path and run-level singletons no.
- **`UX-261`** — what the first view should lead with instead: longest
  on the critical path, then the graph's density, then what is unusual
  for its kind.
- **`UX-262`** — a 122-deep critical path grows the `signals` section
  from 2.1 to **6.2 screens** on a *smaller* run, because the
  critical-path table defaults to `All rows`.

Order: `UX-258` then `UX-259` — the ranking has to be right before its
scale is worth publishing — then `UX-261` on top of both, `UX-260`
after, and `UX-262` independently.

`UX-258`, `UX-259` and `UX-262` landed in this round; `next_steps[0]`
now reads *"layer00/mod037.bst is the first thing to fix"* and the
deep run's `signals` section is 2.5 screens rather than 6.2.
**`UX-260` and `UX-261` are filed and not implemented** — they were
asked for as brainstorms and are delivered as arguments, and the
first view is worth rebuilding once, on top of a ranking that is
already right, rather than twice.

## UX-263..UX-264: the page's own policy refused its drawings (2026-08-24)

Reported while round 32 was in validation: *"lots of errors from latest
Chrome about applying inline style violates the following content
security policy default-src, pointing to views.js"*. Reproduced on the
golden run served by `bga view` itself, in Chrome 141:

```text
                       violations   wf-fill widths   path-box grow   horizon --w
before                         15   1 distinct       1 distinct      1 distinct
after                           0   4 distinct       3 distinct      5 distinct
```

- **`UX-263`** — a style *attribute* is inline style, so the server's
  own `default-src 'self'` refused all four of the viewer's width
  channels. Console noise was the symptom; four dead drawings were the
  defect. Fixed with CSSOM rather than by relaxing the policy.
- **`UX-264`** — the shim that could not see it is written inline
  twenty-five times, so `UX-263` was a seven-file fix for a one-line
  bug. Filed, not implemented: it is a refactor, and `UX-257` is the
  larger argument it feeds.

A third report followed: the Perfetto hand-off stopped working, with
the same *"no Access-Control-Allow-Origin header is present"* shape.

- **`UX-265`** — `UX-198`'s CORS grant answered the **read** and
  nothing answered the **pre-flight**, so `BaseHTTPRequestHandler`
  replied `501` and a browser read that as the header being missing.
  Reproduced in Chrome 141 against two servers differing only in
  `do_OPTIONS`; a simple `GET` works in both, which is why this sat
  unnoticed until something made the read pre-flight.

## UX-253..UX-264: the thirty-fourth round — instruments and scales (2026-08-24)

Five open items, taken together because two of them are the same
argument: what the guards *measure with*.

- **`UX-264`** — the DOM shim was written inline twenty-five times.
  One `tests/dom_shim.mjs` now; the acceptance mutation reaches three
  files where it used to need twenty-five edits. Consolidating found
  four places the copies disagreed with a browser, including one where
  **every guard had only ever exercised a fallback branch** because no
  shim implemented `after`.
- **`UX-257`** — the geometry instrument, decided and built. The
  premise that a real browser means Playwright turned out to be false:
  node 22's built-in `WebSocket` drives Chrome in forty lines. It found
  two measurement errors of my own on its first run, then zero overlaps
  at three viewports.
- **`UX-260`** — duration, sandbox tax and process count publish
  distributions; the `no` list keeps its arguments where the next round
  will look.
- **`UX-261`** — the first view leads with the longest element on the
  critical path, and states the graph's density in one line. My first
  density rule called a star-shaped graph "spread"; that case is now a
  guard.
- **`UX-253`** — an aggregate names the contract sets it mixes. The
  rule is `UX-250`'s, applied to a set, and argued against `UX-234`'s
  host-class precedent rather than copied from it.

## UX-266..UX-272: the thirty-fifth round — the report is read, not decoded (2026-08-24)

Nine observations from a real run, measured in Chrome 141 before any
were acted on. [Direction 12](../../design/directions.md) argues all of
it, including the three where the measurement disagrees with the
diagnosis.

- **`UX-266`** — **two of the three served pages ran nothing.**
  `default-src 'self'` refuses inline *script* as it refuses inline
  style, and `sql.html` and `perfetto.html` each had one. `sql.html`
  rendered zero children; `perfetto.html`'s button had no listener.
  `UX-263` fixed the style half and checked one page. **Fixed.**
- **`UX-267`** — one line renders every object *and every array* as
  `<details>object</details>` over raw JSON: 34 cells and 32,393
  characters on a 44-element run. Filed with a spike's measurements,
  including the trap: rendering them as tables makes the document
  **2.6x longer** unless the fold is kept and merely labelled.
- **`UX-268`** — six of those maps are the same element list, and the
  seventh is keyed by *task* and shares zero keys with them. Nobody
  asked for this; it is the largest win available.
- **`UX-269`** — field lengths, measured. A flat cap is wrong: a
  `copy_text` paragraph and a caveat sentence want opposite treatment.
- **`UX-270`** — the critical path gets its own section.
- **`UX-271`** — the rail should nest, **not** become a third column:
  a JSON tree makes the document's shape the organising principle, and
  a third column undoes `UX-254`'s reading width.
- **`UX-272`** — the header is 0.1-0.2 screens of a 14-screen
  document. Worth tidying, not where the space is.

## UX-267..UX-272: the thirty-sixth round — the report reads (2026-08-24)

The six filings from round 35, in order. Measured on a served run in
Chrome 141 at every step.

```text
                          before    after
opaque "object" cells         34        0
characters of <pre>       32,393        0
document                13.8 scr  13.6 scr
tables                         6       23
sections inside cells          3        0
```

- **`UX-267`** — one function was the whole fix: `renderTable` returns a
  `<section>`, which is right for a view and wrong for a cell. `buildTable`
  is the same builder without the wrapper, and the spike's 22 phantom
  contents entries disappear with it. The fold stays, labelled
  `Downstream count · 44 entries`.
- **`UX-268`** — six folds became one 44-row, 13-column element table;
  `wall_clock_share` says it is keyed by task.
- **`UX-269`** — a long *value* truncates with the whole thing kept; a
  long *explanation* does not.
- **`UX-270`** — the critical path is its own section, and was the last
  of the sections that had been rendering into `<dd>` elements.
- **`UX-271`** — the rail nests one level, bounded at 8 with the
  remainder counted. The third column stays declined, with its argument
  beside the code that replaced it.
- **`UX-272`** — the header is one row at 1440 and stacked at 390. The
  measurement corrected the request: it is 0.1-0.2 screens, worth doing
  because it is sticky. It also exposed `--head` being one value for
  both widths, which would land an anchor 46px under the heading at
  390px.

Three guards in this round did not discriminate on first write and were
fixed rather than counted; one of them was the eleventh instance of a
grep finding its own argument.

`UX-273` and `UX-274` are what the cadence guard's **second review**
found when 26 rows had closed since the first
([`../../audits/architecture-review.md`](../../audits/architecture-review.md)):
the width-not-depth rule this round built governs every nested value in
the report and is written down in exactly one task file, and the
context map's guard globs `bga/` and `tools/` only, so the half naming
`tests/` has drifted to 5 of 12 entries and every figure in it — 218
files against 240, ~3,100 tests against 3,327, 233 closed rows against
263 — is stale. Both harnesses this axis just built, `tests/dom_shim.mjs`
and `tests/cdp.mjs`, are among the seven entries it does not name.

## UX-242..UX-246 + UX-273/UX-274: the thirty-seventh round — the documentation debt, paid (2026-08-24)

Everything `UX-241`'s two reviews filed, plus round 28's three
`UX-237` instances. Seven items, no feature: this is the round the
process asked for and the two before it deferred.

Three of the seven found their own premise wrong, and each is recorded
rather than quietly worked around:

- **`UX-244`'s measurement was a false negative.** It was filed on
  `git grep -l "upper bound, not a forecast" docs/` returning nothing.
  The guide had carried the sentence since the commit that shipped
  `UX-230`, hard-wrapped between `not a` and `forecast`. `git grep` is
  line-oriented and this repository wraps prose at 72 columns, so any
  phrase worth checking can wrap and read as absent. Every guard written
  this round normalises whitespace before matching, and the hazard
  recurred **twice more** inside the round — once in a `sed` mutation
  that silently failed to apply, once in a second guide.
- **`UX-242`'s clause 2 asked the spec to name an `analyze/v1` key that
  does not exist.** `capacity_recommendation` is computed, rendered in
  full by the text report, and dropped by the JSON renderer, while its
  sibling `memory_envelope` is a published key of `correlate/v1`. The
  guide now says so plainly and the contract gap is
  [`UX-275`](UX-0275-the-capacity-recommendation-is-text-only.md).
- **`UX-246` corrected `UX-244`, an hour after it landed.** The
  architecture chapter written for `UX-244` said summing per-element
  savings errs "in the direction that overstates". On the committed
  `examples/06` run it *understates*: `codegen.bst` is worth 0.000s
  alone and the pair `core.bst` + `codegen.bst` is worth 19.050s against
  12.050s summed, because `codegen.bst` sits on the chain that becomes
  binding the moment `core.bst` is fixed. Both directions are now
  recorded, with a measurement each.

The two guards worth keeping past this round both **recompute** rather
than trust: the journey guide's pasted `whatif` figures and the
capacity/memory chapter's pasted constraint lines are checked against
what the tool produces from the committed runs today, so a pasted number
is a claim the suite can falsify (`UX-132`). `UX-274` closes the other
half of `UX-239`'s guard, so a new file directly under `tests/` that
nobody names now reddens.

Four mutations across the round did not discriminate and were fixed
rather than counted — one of them a guard that matched the sentence
*discussing* a figure instead of the pasted figure itself, which is the
self-matching failure in its subtlest form yet.

One guard reddened on the day its subject was *done* rather than when it
broke: `test_documentation_debt_has_a_door.py` asserted that each of
`UX-237`'s three mechanisms "has a backlog row", and read only
`README.md` — so moving the three rows to `closed.md`, which is what
closing them means since `UX-232` split the index at 234 rows, looked
identical to never having filed them. It reads both halves now, and
deleting a row from either still reddens it.

**The round's own CI caught what its guards did not.** Both new
recompute-the-figures guards were pointed at the `bga snapshot` store
under `examples/06-macro-micro-optimization/.bga/`, which is ignored by
design — `bga snapshot` writes a `.gitignore` of `*` into every store it
creates (`UX-126`, `UX-189`). The full suite passed locally three times;
CI failed on all four Python versions with `FileNotFoundError` before an
assertion ran. That is `UX-213`'s defect in the form its fix did not
cover: `UX-213` made the *environment* portable and said nothing about
the *data*, and its rule — "the real capture stays as extra coverage,
never the only place a mutation would be caught" — was written in a
comment four other test files keep. The run is now committed as a 72 KB
fixture and the rule is mechanical
([`UX-276`](UX-0276-a-guard-can-rest-on-a-path-no-clone-has.md)).

## UX-277..UX-284: reported from a real report, round 38's filings (2026-08-24)

Nine observations from reading the served report, measured against it
rather than argued. Everything below is from the 1,202-element synthetic
run (`bga gen-synthetic /tmp/scale --seed 1`) and the committed
`macro_micro` fixture, in Chrome 141.

**Three of the nine are one line.** `UX-267` built `renderStructured` —
inline / bounded table / fold, by width — and wired it into
`renderPairs`, which draws `<dd>` cells. It was never wired into
`buildTable`, which draws every `<td>` in the report. That leaf
(`bga/viewer/app.js:479`) still does `raw.join(", ")` for arrays and
`JSON.stringify` for objects:

```text
18,415 <td> cells on the 1,202-element run
  raw JSON cells                     6
  joined-array cells over 60 chars  11
  "[object Object]" cells            1
  widest cell                   14,300 characters  (signals / leaves_detail)
```

So `leaves_detail` is 14,300 characters of JSON in one cell
([`UX-277`](UX-0277-every-table-cell-stringifies-its-own-structure.md)),
`CELL_TEXT_CAP` never fires because it lives on the path this one
bypasses, and the bottleneck block's nine choke points are a string
rather than rows — which is why the `structural` section has **zero**
links out of it
([`UX-283`](UX-0283-the-bottleneck-view-names-elements-you-cannot-reach.md)).
The report's "no way to go to detailed info" is not missing data; it is
data rendered as dead text.

**The magnifier is worse than reported.** It was described as working
only for critical-path elements; measured, the mechanism is the detail
cap and the numbers are starker — 1,202 elements, **24** detail blocks,
27 Inspect anchors, **2 of them resolving to nothing**
([`UX-278`](UX-0278-the-magnifier-opens-nothing-for-most-elements.md)).
This is `UX-208`'s dead-anchor defect returning at a scale `UX-216`'s
fix did not cover, and the 11-element fixture cannot see it: there,
30 anchors resolve 30 times.

**Both satellite pages are dead ends**, not just `sql.html`:
`perfetto.html`'s only internal href is `#`
([`UX-281`](UX-0281-the-satellite-pages-are-dead-ends.md)).

**Forty-three copy controls, three vocabularies, no hover text on any of
them** — and the bare `Copy` means one thing in `decision` and another
in `findings`
([`UX-279`](UX-0279-forty-three-copy-controls-and-no-way-to-know-what-they-copy.md),
[`UX-280`](UX-0280-copy-as-markdown.md)).

**Every table control is `position: static`** and 28 of 43 sit below
their own table's top, on a document 18.8 screens tall
([`UX-284`](UX-0284-the-table-tools-are-below-the-table-and-scroll-away.md)).

The Perfetto fallback line is `UX-272`'s move applied to the hand-off
page ([`UX-282`](UX-0282-the-perfetto-fallback-is-below-the-button-that-fails.md)).

**And the page's furniture is in the wrong order.** The three blocks
that answer *which run is this* are split across the document — `summary`
and `run_instance` at 1.3–1.6 screens, `producer` at 10.9 on the
synthetic run and 14.0 on the fixture — while the blast control, an
interactive question rather than a report block, is the **last** thing
on the page at 18.5 and 19.9 screens, eighteen screens from the findings
it would be asked about
([`UX-285`](UX-0285-the-identity-blocks-are-split-and-the-blast-box-is-last.md)).


`UX-286` is what Direction 13 found when the proposal to make every
block one screen was measured instead of argued: 0 of 48 sections are
within a fifth of a screen of that size, 95% are under four-fifths, and
the median is 216 pixels. Padding them would add 31.3 screens. The
report does not have blocks that are too big — it has forty-eight that
are too small and nothing that groups them.


`UX-288`..`UX-290` are what Direction 14 found when "the critical path
is shown three times" was measured instead of agreed with. The page
draws **19 element tables over 13 distinct populations**, seven pairs at
100% overlap — but the duplication is in `analyze/v1`, which publishes
the same leaf membership three times and the same critical path twice,
each a subset of the one 1,202-row element table. The page is faithful;
it renders every copy it is given. So the contract is deduplicated first
(`UX-288`) and the page's nineteen tables become presets over one
(`UX-289`) — which makes `UX-283`, `UX-284`, `UX-286` and `UX-278`
smaller rather than larger. `UX-291` is what `UX-288`'s guard found
one level down while it was being written: a finding carries each of its
numbers in up to three places — `evidence`, `provenance.evidence[].value`
and `copy_text` — each for a stated reason, and with no rule saying they
must agree.
