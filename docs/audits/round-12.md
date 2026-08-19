# Audit round 12: the verification round, and the MVP verdict

Run on 2026-08-19, same 4-core / 16 GB environment as rounds 10-11,
with every capture and log tree from both prior rounds retained and
reused. The sibling session landed fifteen backlog items in ~28
commits — the whole of Direction 3 (UX-99..UX-104), the whole of
Direction 4 (UX-105..UX-108, including a 501-line ptrace tracer),
UX-60 (the last open pre-round-10 item), UX-93/95/96, UX-80's real
acceptance, and three self-filed-and-fixed items (UX-109..UX-111).
This round re-verified all of it — filed acceptances re-run on the
data they named, a line-level code review of `spine.c`, live exercise
of the new `bga baseline`/`bga cache-trend`/census/spine machinery —
and closes with the verdict this session was asked for: **has the tool
reached MVP?**

## The scoreboard

Fifteen items: **ten VERIFIED**, three PARTIAL (verification-discipline
notes now recorded in their files), **two reopened**.

Highlights among the verified, each re-run here:

- **UX-93** — churn conditioning survived every live case: the cold
  pair now reads *"not assessed: the candidate is a caches-off run …
  intended behaviour, not waste"*; the true-positive invalidation-root
  case is byte-identical; the fdsdk warm/cut pairs read as retention.
  The round-11 High is genuinely closed.
- **UX-105/106/107, the value case** — a live spine capture of
  `examples/01` produced the first Plane 2 records those elements have
  ever had: 24 static busybox processes, all `spine-only`, per-element
  attribution, and the known-answer test exact (`sleep 3` = **3.0016s
  wall, 0 CPU, rss 1528 kB**). The dual capture of `examples/06`
  joined 822 of 822 processes `spine+hook` with no double-counted CPU.
- **UX-95/96/103/104** — the compare header now distinguishes two
  same-config fdsdk captures by instance (19:43 vs 06:34 UTC);
  `bga baseline` really is one command from bare refs to band verdict
  (with a bga-revision drift warning); `cache-trend` renders five real
  runs flat and refuses mixed series with exit 6; the memory envelope
  on the new fdsdk capture reads *"4 builders of this shape peak at
  ~4.0 GB of 15.6 GB (25%); 11 would still fit … memory is not what
  binds first here"*.
- **UX-108's discipline is the round's model**: decision rule stated
  before measurement, 30 real builds, the default followed the number
  (opt-in), and the clause it missed became a filing (UX-110) instead
  of a smoothing.
- **UX-102's cross-check earned its keep**: measuring the configure
  tax from both planes disagreed 43×, which caught a real
  classification bug — the UX-53 pattern paying out again.
- `make test` with live bst: **1428 passed, 0 failed**. Main's CI is
  green across all eight jobs, including a spine capture step.

## The two reopenings

- **UX-100**: the merge candidate has never fired on real data — the
  acceptance's positive case (fine-grained fixture, fired candidate,
  projection vs a real merged rebuild) was never run, and unlike the
  task's two recorded deviations, this omission went unrecorded.
  Reopened; `UX-120` carries the work.
- **UX-106**: a filed acceptance clause — *the tracer's own crash
  leaves the build to finish normally* — was **measured failing** and
  shipped under 🟢, attributed to ptrace in general. The code review
  says otherwise: the degrade path detaches one tracee and strands
  every other at its next stop, waiting for an `ECHILD` that cannot
  come (`UX-117`); every auto-attached child's attach-SIGSTOP is
  re-injected as a real group stop, which is both a per-process cost
  and — via the kernel's group-stop reinstatement on tracer death —
  the likely mechanism of the failed clause itself (`UX-118`); and the
  signal model was written for a pid-1 configuration BuildStream never
  runs (`UX-119`). The spine's *data* is verified; its *failure
  behavior* is not, and the opt-in default is currently the only thing
  standing between that and a hung build.

## What this round's own hands found

- **UX-112** — the overhead matrix has a missing cell, and it is the
  deployed one: spine alone ≈ free (41s, matching UX-108's +2.7%),
  opens alone ≈ free (41-45s), **spine × opens = 59s (+31-44%)** — and
  `trace_opens=true` is the capture workflow's default, so the one
  real fdsdk spine capture ran exactly the pairing whose price was
  never measured (it passed the band only because the band is ±643s).
- **UX-114** — the baseline set's edges, each hit live: the
  homogeneity check skips absent fields, so the spine capture joined a
  five-run hook-only band **with no warning**; `fdsdk-latest` now
  points at that differently-instrumented capture; a cross-mode
  candidate exits 2 where the contract says 6.
- **UX-121/122** — two recurrences of named prior patterns: compare
  still prints `Execution On Chain Us` (UX-111's own item, guarded by
  a test bound to the helper instead of the surface — the UX-85
  pattern), and the capture guide's ref globs went stale again two
  days after UX-97 fixed them, in the same file (this time the fix
  includes the automation that was skipped).

## The MVP verdict

The bar, assembled from what this project has said it is since round 9:
a build owner can, **following only the documentation**, (1) capture a
real project locally, get correct, ranked, actionable findings across
the macro and micro levels, act on them, and prove the result; and
(2) run it in CI to gather analytics over time, highlight problems by
name, and stop efficiency regressions under the rule *adding work is
allowed; adding it inefficiently is not*.

**Verdict: yes — the MVP bar is met**, on evidence rather than
optimism:

- **Scenario 1 is closed.** Rounds 10-12 walked it three times from a
  fresh environment. The documented path works from a clean install
  (wheel-tested in CI) through capture (defaults produce the join,
  verified on a `build-root`-overriding fixture) to findings that were
  *acted on* for a measured −39%, with projections that land on
  measured reality (11.1s projected vs 11.05s measured) and refusals
  where the data cannot support an answer. The tool out-reasons its
  own walkthrough's gold standard.
- **Scenario 2 is closed at its core.** Analytics: per-run immutable
  refs, weekly + monthly-cold schedules, one-command baseline
  assembly, a cache trend, all exercised live this round. Problems by
  name: findings with stable ids across three planes, cache
  effectiveness with honest labels, the developer tax, the memory
  envelope. Regression stopping: the duration gate, the whole-build
  efficiency gate, and the **marginal gate** — which expresses the
  owner's rule exactly, verified on real builds at two scales with the
  dilution claim pinned as a test — over a measured noise band instead
  of a guessed threshold, with gates that refuse mismatched inputs and
  say so when they cannot run.
- **What keeps the verdict honest.** Three planes and 127k-process
  real-project scale are *capabilities past* the MVP bar, and the
  newest of them is not yet trustworthy in failure: the spine's hang
  paths (`UX-117`..`UX-119`) and unmeasured combination cost
  (`UX-112`) mean Direction 4 is *demonstrated*, not *done* — bounded
  today by its opt-in default. The CI story's last inch is rendering
  (`UX-115`): the gates decide correctly, and a reviewer still has to
  read JSON to learn why. And the trend/tax layers are observational
  by explicit, evidenced deferral. None of these is between the tool
  and its MVP claims; all of them are between the MVP and the product
  it is becoming.

Post-MVP order, argued in Direction 5: `UX-117`/`UX-118` (make the
spine as unbreakable as its header claims), `UX-115` (the CI comment),
`UX-112`→`UX-113` (price, then target, universal coverage), `UX-116`
(the founding question's answer), with remote execution still parked —
deliberately — until there is a real deployment to measure against.

## The process, at three rounds' distance

Rounds 10-12 form a loop this repository should keep: an audit round
files with evidence; a fix round implements at remarkable speed; the
next audit re-runs every filed acceptance *on the data it named*. What
the loop keeps catching is stable across all three iterations —
almost never arithmetic, almost always **the gap between what was
verified and what was claimed verified**: the fixture that stood in
for the named capture, the guard bound to the helper instead of the
surface, the acceptance clause that failed and shipped anyway, the
measurement matrix with the deployed cell missing. The single biggest
process win available now is the one UX-122 automates for ref globs
and UX-121 demands for rendered surfaces: **when a claim can be
checked mechanically, check it mechanically** — every hand-maintained
correspondence in this repository has drifted within days, and every
automated one has held.
