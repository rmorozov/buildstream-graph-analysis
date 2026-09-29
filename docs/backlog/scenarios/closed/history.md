# Closed scenarios: history

The narrative sections that sat below the closed table, moved verbatim by `UX-1120`. The rows are in the numbered files beside this one.

## UX-207..UX-212: the twenty-third audit round — the report learns to answer first (2026-08-22)

Round 23 verified the sibling's landing of the entire round-22 slate
(UX-198..206) and synthesized the next iteration from a second
external review — this one a Pareto argument: stop adding viewer
architecture, spend the next round on compression and actionability,
because the reader has to read too much before knowing what deserves
attention. Its diagnosis was confirmed against `boot()` (fourteen
sections at one visual level, the product's own "what should I fix
first" answer rendering mid-list) and its shortlist adopted with one
house adjustment — the decision panel's inputs enter `analyze/v1` as
a published `headline` block first, because a viewer that derives
the diagnosis is a second analyzer. Its stat-card dashboard was
declined with its own argument. What it missed, this round filed:
the canned SQL it praised is track-blind
([`UX-210`](../UX-0210-questions-that-know-which-plane-they-are-asking.md)),
its remember-my-state item wants the URL rather than `localStorage`
([`UX-211`](../UX-0211-a-link-that-shows-what-i-was-looking-at.md)),
and it never looked at color-only encodings
([`UX-212`](../UX-0212-verdicts-you-can-see-without-the-palette.md)).
Verification added what no review sees: the landing's named mutation
guards are pinned to a capture that exists on one machine and skip
everywhere else
([`UX-213`](../UX-0213-the-guards-that-only-guard-one-machine.md)), and
the trend's colouring is a second verdict chain that re-litigates
the disputed region
([`UX-214`](../UX-0214-one-verdict-vocabulary.md)).
Full narrative: [`../../audits/round-23.md`](../../../audits/round-23.md).

## UX-198..UX-206: the twenty-second audit round — the viewer learns what it is looking at (2026-08-21)

Round 22 verified the viewer landing — all five items hold, six
mutations re-run red, exit 7 and the export verified live — and then
synthesized the next iteration from two inputs: the user's four field
observations (each ground-truthed to its mechanism: the popup opened
outside the click's activation; the analyze pipeline with zero
tickers and a TTY nobody draws on; no `[all]` extra; a page with no
anchors) and an external review of the shipped viewer whose six code
claims round 22 confirmed line by line. The synthesis is Direction
7's second iteration: the review's thesis adopted (the opportunity
is not more generic rendering — it is the viewer understanding BGA's
relationships and using Perfetto as the microscope), its
architecture trimmed to modules, and its blind spot supplied by the
field (the handoff it praises is popup-blocked by construction).
Verification added what neither saw: two shipped views nobody can
reach ([`UX-203`](../UX-0203-the-views-nobody-can-reach.md)). Full
narrative: [`../../audits/round-22.md`](../../../audits/round-22.md).

**All nine landed.** The round's shape held: every item was reproduced
before it was fixed, and three of the filings turned out to be wrong
about the codebase in ways worth recording. `UX-203`'s proposed
package-data mutation was **refuted** — the files ship anyway.
`UX-206`'s "a `<details>` tree over data `blast/v1` already carries"
was **false** — the payload had two flat lists and no depth, so the
depth had to enter the JSON. And `UX-204`'s library item uncovered a
copy nobody had noticed: `sql.html` spelled out every query a second
time, guarded only by a title comparison.

Three regressions were introduced *by this round* and caught inside it,
which is the part worth reading: `UX-202`'s two-line import
reintroduced `UX-199`'s export defect verbatim (the line-based stripper
matched neither half, and every export died on `ERR_INVALID_URL`
again); `UX-204`'s reveal used `removeAttribute` against a
property-set `hidden` and would never have shown its paste; `UX-206`'s
first depth walk used the transitive closure and produced a flat tree.
Each is now a property assertion rather than a mechanism test.

Two measurements moved a rule rather than a number. The page-size guard
summed a *directory*, counting two served-only pages an export never
carries — it measures the exported file with its data blocks removed
now. And when that honest number crossed 80,000 B, the bytes came from
stripping comments out of the *inlined copy*: they are written for
someone reading the repository, and an attached report carries none of
those readers.

## UX-193..UX-197: the twenty-first audit round — the viewer argued, the field round verified (2026-08-21)

Round 21 verified all ten of round 20's landings — four mutations
re-run by the review, the pip-through-blast and 68-char paste cases
run live, the synthetic budget test timed — and every one holds; the
six seams the verification collected are
[`UX-197`](../UX-0197-six-seams-round-21-verified-into.md), none a
reopening. The round's design work is
[Direction 7](../../../design/directions.md): **the viewer as a thin
window onto the JSON** — the published schemas (UX-190's) are the
entire interface, the page renders the schema rather than the report,
timelines go wholesale to ui.perfetto.dev through the deep-link
handshake, and the same page ships as a served view and an attachable
file. Decomposed as
[`UX-193`](../UX-0193-bga-view-a-thin-window-onto-the-json.md) (the
core), [`UX-194`](../UX-0194-the-perfetto-handoff.md),
[`UX-195`](../UX-0195-the-report-you-can-attach.md) and
[`UX-196`](../UX-0196-the-views-that-make-the-numbers-self-evident.md);
the dependency-DAG view is deliberately deferred in the direction
itself. Full narrative:
[`../../audits/round-21.md`](../../../audits/round-21.md).

## UX-183..UX-192: the twentieth audit round — the field speaks (2026-08-21)

Round 20 verified round 19's landings — all five hold, nine claimed
mutations reproduced by the review, the round-trip re-run live —
and turned the user's first sustained field feedback into ten
filings. The feedback drove the round's shape: each item was
ground-truthed before filing (the inventory does read `import`/
`manual` sources but silently mangles the paths bst would reject;
the hook stamps a clock that stops during suspend while Plane 1's
does not; compare has no host check of any kind; the chrome-trace
merge already exists and is unreachable from a snapshot; the output
JSON has no schema to drift from — this very range renamed a
published field silently). The verification also found the two
defects [`UX-192`](../UX-0192-the-elision-that-reopened-the-round-trip.md)
carries: the table's elision re-opens the round-trip UX-178 closed,
for identities longer than 43 characters — real forge urls — and
blast's keying sentence undoes UX-181 one surface over. Full
narrative: [`../../audits/round-20.md`](../../../audits/round-20.md).

## UX-178..UX-182: the nineteenth audit round — the source axis meets its own output (2026-08-20)

Round 19 verified all of round 18's landings live — the drain fixtures
re-run, the disputed-region band verdicts checked at n=5 *and* n=3,
and the whole source axis exercised end to end on a rewritten-fixture
monorepo: the Shared Sources table, the keying clause, the kind
split, the work-not-wall-clock note, `bga blast` in all three target
shapes, and the pre-inventory run's honest "this capture cannot answer
that". The headline finding came from pasting the tool's own output
into itself: [`UX-178`](../UX-0178-the-tools-own-printed-identity-does-not-round-trip-through-blast.md)
— the table's identity string resolves as a path and answers
"rebuilds nothing here". The review's live mutation proved
[`UX-179`](../UX-0179-the-discriminating-case-that-was-never-built.md)
(the cost-order guard passes with the sorter reverted), and
[`UX-180`](../UX-0180-the-docs-still-assert-what-the-disputed-region-broke.md)..[`UX-182`](../UX-0182-the-inventory-stops-at-the-junction-boundary.md)
carry the docs trail, the identity edges, and the junction boundary —
the last being where the user's real monorepo question most likely
lands next. Full narrative:
[`../../audits/round-19.md`](../../../audits/round-19.md).

## UX-171..UX-177: the eighteenth audit round — the source axis (2026-08-20)

Round 18 verified round 17's landings — all of UX-163..UX-169 hold,
with the review re-running every measured number (the 204 MB peak, the
byte-identical digest, UX-170's −25% band escape) and reproducing each
exactly; the three live interrupt windows, the pasteable extract hint,
and the prune keep-set were exercised end to end. The verification's
own findings became [`UX-175`](../UX-0175-the-grace-window-buys-nothing-while-the-pipe-stays-unread.md)
(the grace window cannot deliver its promise while the pipe stays
unread — demonstrated with a SIGINT-trapping fake bst),
[`UX-176`](../UX-0176-three-guards-that-assert-less-than-their-logs-say-round-three.md)
and [`UX-177`](../UX-0177-five-corners-round-18-verified-its-way-into.md).
Full verdicts in [`../../audits/round-18.md`](../../../audits/round-18.md).

The round then opened the axis the user's monorepo question demands:
[Direction 6](../../../design/directions.md) — **blast analysis by shared
resource**. The argument in one line: a `git` source keys on its ref,
so one url feeding N elements rebuilds all N on any commit regardless
of `directory:`, while a `local` source keys on content — the same
monorepo consumed two ways has order-of-magnitude different blast, the
`.bst` files encode which way, and everything needed to compute it is
already on disk. [`UX-171`](../UX-0171-blast-radius-by-shared-source-the-monorepo-question.md)
builds the inventory and the report table,
[`UX-172`](../UX-0172-bga-blast-what-rebuilds-if-i-touch-this.md) the
query command, [`UX-173`](../UX-0173-a-blast-count-that-counts-stacks-overstates.md)
retrofits kind-awareness into the existing blast surfaces (the user's
literal first sentence), and
[`UX-174`](../UX-0174-the-monorepo-patterns-page.md) documents the
patterns the numbers let a project choose between.

## UX-163..UX-168: the seventeenth audit round — the fixes verified where they will be lived in (2026-08-20)

Round 17 verified all eight round-16 landings live — the refusal
verdict, the walk-back, the gate's exit 6, the mid-build interrupt
salvage (exit 130, both planes kept), the recursive census joining
both planes on a real nested layout, stale-casd detection positive and
negative, the help caps, prune's alias protection, the stderr tee and
`replay-sandbox`'s polite refusal — and every verdict is **holds**,
five with caveats that became this round's filings rather than
reopenings. The two Highs are edges the verification itself walked
into: [`UX-163`](../UX-0163-the-interrupt-contract-covers-the-build-and-not-the-minutes-around-it.md)
(a SIGINT during post-build extraction is still a raw traceback — the
salvage covers the build and not the slow minutes around it) and
[`UX-164`](../UX-0164-the-walk-backs-replay-hint-reproduces-the-comparison-it-just-refused.md)
(the walk-back's own replay hint reproduces the wreckage comparison it
just refused). [`UX-165`](../UX-0165-seven-help-strings-end-mid-sentence.md)..[`UX-168`](../UX-0168-analysis-holds-the-whole-trace-in-memory-and-other-round-17-leftovers.md)
carry the truncated help sentences, the casd config divergence, the
prune-vs-walk-back contradiction, and the big-project capacity list.
Full narrative: [`../../audits/round-17.md`](../../../audits/round-17.md).

## UX-156..UX-162: the sixteenth audit round — the tool meets a big project (2026-08-20)

Round 16 verified the diagnosability round's landings (UX-147,
149..155 — all hold, three with caveats now carried by `UX-161` and
`UX-162`; UX-148 deferred cleanly, nothing half-landed) and then ran
the polish lens where the user now lives: **a multi-hour capture on a
project with thousands of elements**. Live experiments on a sabotaged
`examples/06` produced the round's headline — a snapshot of a build
that *failed* ends `Verdict: IMPROVED (-65.6%)`
([`UX-156`](../UX-0156-a-build-that-did-not-finish-must-not-verdict-as-if-it-did.md)),
and Ctrl-C mid-capture destroys the Plane 2 trace it already has
([`UX-157`](../UX-0157-ctrl-c-on-an-hours-long-capture-destroys-the-trace-it-already-has.md)).
The review's sweep added the structural pair:
[`UX-160`](../UX-0160-the-census-reads-only-the-top-of-the-element-tree-and-auto-spine-bills-the-difference.md)
— non-recursive element discovery silently turns auto-spine into
full-build ptrace on real layouts — and
[`UX-161`](../UX-0161-the-stale-casd-everyone-suspects-is-checkable-before-the-build-and-nobody-looks.md)
— the field failure's live suspect is checkable before the build and
nobody looks. [`UX-158`](../UX-0158-help-is-a-design-history-lecture.md)
(the `--help` surface the docs concision pass never reached),
[`UX-159`](../UX-0159-the-quiet-minutes-and-growing-gigabytes-of-a-big-project-snapshot.md)
(silent phases, unsized store, no prune) and
[`UX-162`](../UX-0162-small-debts-of-the-diagnosability-round.md) round
out the batch. Full narrative:
[`../../audits/round-16.md`](../../../audits/round-16.md).

## UX-147..UX-154: the fifteenth audit round — a field failure the tool cannot see (2026-08-20)

Round 15 chased the first real external deployment's failure (`bst
build` works, `bga snapshot` dies with `buildbox-run failed with
returncode 1` on Ubuntu 24.04) by rebuilding the user's exact shape on
this container — wheel → fresh foreign venv with its own bst → project
copy outside the checkout → snapshot from a third directory — and it
**worked**, falsifying the packaging hypothesis: the failing link is
environment-specific and *earlier than the shim*, precisely the region
UX-146's shim-side record cannot see. The first four filings close
that region: [`UX-147`](../UX-0147-zero-shim-invocations-has-three-causes-and-diagnose-asserts-the-benign-one.md)
makes the zero-invocation verdict honest (self-probe, absolute
shebang, stale-daemon check, guarded environ),
[`UX-148`](../UX-0148-a-failed-sandbox-should-leave-its-argv-and-its-stderr-behind.md)
preserves the dying sandbox's stderr and argv and replays them,
[`UX-149`](../UX-0149-doctor-checks-the-parts-and-nothing-checks-the-chain.md)
composes everything into a canned whole-chain probe, and
[`UX-150`](../UX-0150-the-shape-real-users-install-in-has-zero-capture-coverage.md)
puts the deployed install shape under CI so it stays working.

The round's code review over `0acaff5..dcdd402` then produced the
second batch: [`UX-151`](../UX-0151-the-arity-table-is-the-likeliest-field-failure-and-nothing-records-the-version-that-breaks-it.md)
— the arity table against post-0.9.0 bubblewrap, now the **strongest
remaining hypothesis** for the field failure and invisible to the
mis-split detector; [`UX-152`](../UX-0152-ux-143s-group-stop-fix-has-the-bug-it-was-filed-against.md)
— UX-143's group-stop fix re-verified by hand and found to contain the
bug it was filed against, on all three detach paths;
[`UX-153`](../UX-0153-ux-142-fixed-the-headline-and-left-its-principle-half-applied.md)
and [`UX-154`](../UX-0154-four-claims-that-outran-their-commits.md) — the
half-applied doctor principle and four claims that outran their
commits. Everything else verified: UX-140/141/144/145/146 hold in
full, UX-135..139's corpus arithmetic checks to the line. Full
narrative: [`../../audits/round-15.md`](../../../audits/round-15.md).

## UX-135..UX-145: the fourteenth audit round — docs made simple, concise, consistent (2026-08-19)

Round 14 verified round 13's polish fixes hands-on (the two-snapshot
loop ran with zero user-invented paths and auto-compared IMPROVED
−25.8%; doctor, the cache-logs front door and `@last` aliases all
behaved as filed; suite 1689 green with live bst) and ran the round's
named lens: a fresh-eyes read of the whole 3,094-line user-facing
corpus for simplicity, concision and consistency. Full narrative:
[`../../audits/round-14.md`](../../../audits/round-14.md).

Two threads of filings. **Docs** (`UX-135`..`UX-139`): first-value
ordering, the superseded flows still taught in the two most-read docs,
eleven duplicate clusters, the terminology table, and journey B's
missing page. **Verification findings** (`UX-140`..`UX-145`): the
SEIZE fallback breaks the exit-status contract its own file teaches,
the failure-injection lists test a deleted site and miss the
most-executed one, doctor false-FAILs every project without an
`all.bst`, plus the degrade/drain edges and the convention that
proved too narrow for its own worked example within one range.

## UX-125..UX-133: the thirteenth audit round, and the polish direction (2026-08-19)

Round 13 re-verified round 12's thirteen fixes (full narrative:
[`../../audits/round-13.md`](../../../audits/round-13.md)) and opened the
post-MVP axis the MVP verdict pointed at: **simplify the user
scenarios**. Two threads:

- **Verification**: nine of thirteen hold outright — UX-114/116/120
  are model work (UX-116 ran its acceptance, got the *opposite* answer,
  and reworded the claim rather than the test; UX-120's projection
  missed reality and ships as an explicit floor), UX-115's CI comment
  was re-verified live on the retained pairs, and UX-118's SIGSTOP
  diagnosis was confirmed 0/3 → 3/3. The failures repeat two known
  classes: a guard that covers one of four identical sites (`UX-128`),
  a headline number its own inputs don't support (`UX-129` — which
  also, honestly, records that round 12's +31-44% was a warm-up
  artifact, refuted twice and confirmed by this round's interleaved
  re-measurement at ~0.85 ms/process), and the third round running of
  status-table drift (`UX-131`).
- **Polish** (`UX-125`..`UX-127`): the MVP bar was "following only the
  documentation"; these three attack what documentation cannot smooth —
  the environment (`bga doctor`), the loop's clerical overhead (one
  command, run twice, with a project-local run store), and Plane 3's
  name-vs-path front door. Each filed from friction this audit
  personally hit, with the failing commands pasted.

## UX-105..UX-108: Direction 4 — seeing every process (2026-08-18)

The one deliberate limitation Plane 2 has carried since `UX-11` chose
`LD_PRELOAD`: a fully static executable never invokes the dynamic
linker, so it produces no record and no error — and this repo's own
`examples/01`/`02` busybox elements are invisible to Plane 2 today.
[`design/directions.md`](../../../design/directions.md) Direction 4
carries the argument: the existing shim → argv-rewrite → in-sandbox
env chain is kept (it is validated and the opens-tracking genuinely
needs in-process interposition), and the complement is a **ptrace
process-event spine** — chosen over acct(2), netlink CN_PROC, eBPF,
`/proc` polling and fanotify because it alone sees statics with full
argv/CPU/RSS, needs no privileges (tracees are its own descendants),
and pays per *process*, not per syscall.

Order: `UX-105` (measure the blind spot itself, pre-build, from the
staged roots — small and independently shippable) → `UX-106` (the
tracer) → `UX-107` (join/dedupe/provenance — without it the spine
*corrupts* CPU accounting instead of completing it) → `UX-108`
(validation on both build classes decides the default by measurement).

## UX-41..UX-48: the second audit round (2026-08-16)

Filed from a round that did exactly what the first round's own
[`docs/design/directions.md`](../../../design/directions.md) told it to: it took
the three "what the next audit round should probe" items that were
actionable in one session - **scale**, **a real CPU measurement**, and
**declared-vs-used dependencies** - and probed them against real data
instead of re-reading the code.

**Scale was the productive one.** Every finding in the first round came
from projects of 8-13 elements. A 1202-element run - a toolchain import
everything depends on, twelve layers of 100 modules with real fan-out and
fan-in between adjacent layers, and a stack on top, scheduled onto 16
builders by a real dependency-respecting greedy pass - broke four things
at once (`UX-41`..`UX-44`), and `UX-47` fell out of timing the same run.

Three of those four are the **same failure mode**: a placeholder that was
plausible at 11 elements and is obviously wrong at 1200. `_compute_all_slacks`
returns `duration * 0.5` with the comment *"In full implementation, would
use forward/backward pass"*; the choke-point test is `in_degree >= 2 and
out_degree >= 2` under a comment naming the dominator approach; the level
decomposition is a BFS whose first-visit-wins semantics were never the
intended ones. Each is a few lines, each ships under a name that promises
a real computation, and none of them announces itself as provisional in
any output a user sees. That pattern - **not the individual bugs** - is
this round's main finding.

So the round then grepped for the rest of the pattern rather than leaving
it to the next scale probe, and `UX-48` is what that sweep found outside
`bga/structural/`: `IDLE_UNDERPARALLEL` is declared, read, and never
assigned, so the bucket meaning "raise `--builders`" reads 0.00s on every
run and its time is booked to the bucket meaning "restructure your
graph". That one needs no scale at all - it is wrong on an eleven-element
project, and it sends a user to the wrong half of the optimization cycle.

`UX-44` is the one to fix first. It is the tool's answer to the only
question a user actually arrives with - *what should I optimize?* - and
on a real capture of `examples/06` it omits the element that is 35% of the
build and names five interchangeable ones instead.

The other two probes produced one filing each and were both worth doing
for what they *settled*: `UX-45` confirmed by reading the real hook that
per-process CPU time is two `getrusage` calls away, and `UX-46` **refuted**
the cheap approach to declared-vs-used detection with real trace data -
the hypothesis was formed from reading the hook and killed by measuring
the output, which is recorded in that doc so the next attempt does not
re-derive it. Recording the refutation is the point; had it been filed as
"match staged paths against traced cmdlines", it would have been an
implementable-looking task that could not work.

### All of the above are now implemented (2026-08-17)

Every item in this round shipped, each verified against a real capture
rather than a fixture. Three results are worth knowing without reading
eight docs:

- **`UX-44` was the highest-value fix**, as predicted. "Slack" was never
  computed - it was `duration × 0.5` - so the improvement ranking was a
  strictly *inverted* duration sort. It now names `core.bst` first at up
  to 10.00s off the finish, independently reproducing the ~10s `UX-09`
  had measured by hand.
- **`UX-42` was 30x** (95.5s → 3.2s on the 1202-element fixture), and
  `UX-47` took `bga graph` from 117s to 0.99s across both fixes.
- **`UX-46` proved `examples/06`'s own documentation wrong.** The
  detector found 24 unused declared edges and confirmed `toolchain.bst`
  as the only dependency any element actually reads - so the project's
  comment that "only `lib-f` consumes `codegen.bst`" was false, and its
  *entire* cross-element dependency structure is decorative. The element
  files now say what was measured.

Two method notes carried forward into `docs/design/directions.md`:
byte-identical output on real fixtures did not establish `UX-42`'s
correctness (an oracle test found two bugs it had hidden), and five filed
acceptance criteria across the two rounds turned out to be wrong with the
measurement right - each corrected in place in its own doc rather than
quietly dropped.

## UX-27..UX-40: the 2026-08-16 audit round

Filed together from one real, hands-on session that did two things the
earlier rounds had not: it **audited what the tool claims against what it
does**, and it **walked a genuinely mis-optimized real project through a
full macro-then-micro optimization cycle** rather than a `sleep N` proxy.
`examples/06-macro-micro-optimization` was built for that walkthrough and
is part of this round - eleven real CMake/C++ elements, deliberately
broken in three independent, one-line ways (a six-deep chain that should
be a fan-out, an over-declared build dep, and `notparallel: True` on the
heaviest element), with an `optimized/` sibling that fixes exactly those
three and nothing else.

The full transcript with every real command and output is
[`docs/audits/case-study-06-macro-micro.md`](../../../audits/case-study-06-macro-micro.md);
the argument about which of these items are load-bearing and which are
polish, for each of the tool's two real usage scenarios, is
[`docs/design/directions.md`](../../../design/directions.md).

The headline result, and the reason `UX-27` is the anchor of this round:
fixing all three problems made the build **30.5% faster** (39.57s ->
27.50s) while `bga`'s own `efficiency_score` moved **1.00 -> 0.83** and
its `certified_headroom` moved **0.00s -> 4.05s**. Both moved backwards
because every certified floor is derived from the run's own observed
graph - a chain-shaped graph has a critical path equal to its own total
work, so the scheduler is tautologically perfect. Nothing in `bga` asks
whether the graph was worth packing.

Two of these items revise earlier decisions, both with new evidence rather
than on re-argument. `UX-29` reopens the "`native_max_jobs` isn't
auto-extracted" claim that an earlier review round triaged as not worth a
task: that triage was about `bst show` (where it genuinely is not
exposed), and the wrapped log's own first line does carry it, with five
shipped features inert on the documented happy path as the consequence.
`UX-31` corrects `UX-22`'s identification of BuildStream's per-element
parallelism mechanism - `public: bst: max-jobs` is inert metadata in
2.7.0; `notparallel` is the real control, confirmed by a real trace
showing `core.bst` running `make -j1` while every sibling ran `make -j4`.


`UX-08` was never used - no scenario was ever filed under that number, it isn't a lost/missing file. Numbering otherwise continues sequentially from whatever the next unused ID is at filing time.

## Why these five (plus five bugs/design docs found along the way)

Grounded in a real, hands-on walkthrough of the current CLI against `tests/fixtures/synthetic_multi_subproject` (not a hypothetical brainstorm) - `bga analyze`, `bga sweep`, `bga floors --cold`, `bga graph --by-kind` were all run for real to check what already works well (the Key Findings block, blast-radius ranking, and `bga sweep`'s knee-point detection are all already genuinely useful decision support) versus what's actually missing. `UX-01`/`UX-02` are the two gaps that most directly block the specific next-session goal: iteratively optimizing example projects using `bga`'s own output to guide each step, until reaching a "good enough" bar the tool itself can name. `UX-03`/`UX-04`/`UX-05` are natural extensions once those two exist.

## Recommended implementation order (open items, assuming full correct closure)

Built by pulling each open item's real cross-dependencies - both declared "Depends on" fields and *practical* implementation-order dependencies (touching the same function/file, one task's output making another cheaper) found by re-reading every open doc together, not just each in isolation. All hard "Depends on" prerequisites for the items below (`UX-09`, `UX-12`, `UX-15`, `P1-31`/`P1-39`/`P1-30`) are already done.

**Phase A - small, foundational, unblock everything else cleanly:**

1. **`UX-16`** (max-jobs=0 truthiness fix) - small, no blockers, and the base every other capacity-check task below either extends (`UX-21`) or delegates through (`UX-17`). Do first so nothing downstream inherits a known bug.
2. **`UX-18`** (canonical run-context builder, `bst_run_context.py` parity) - no blockers. Extracting one canonical manifest/run-context-builder function here is real prep work for `UX-07` below - do this first and `UX-07` only has to touch it once instead of twice.

**Phase B - build directly on Phase A:**

3. **`UX-07`** (run-identity collision fix) - do after `UX-18` for the reason above; otherwise fully independent.
4. **`UX-17`** (`UtilizationAnalyzer` consolidation) - scope now decided (delegates to `_check_process_oversubscription`); do after `UX-16` so it delegates to an already-fixed base, not one that still needs the truthiness fix.
5. **`UX-21`** (memory/swap oversubscription guard) - hard-depends on `UX-16` (mirrors its now-fixed governing-ceiling pattern for a new resource dimension); natural next pick while that pattern is fresh.

**Phase C - independent tracks, any order, safe to parallelize across sessions/contributors:**

6. **`UX-22`** (per-element `max-jobs` + serialization-point detection) - deliberately additive/decoupled from `UX-16`/`UX-17`/`UX-21`'s aggregate checks (confirmed in its own "Out of Scope" - not a replacement), so it doesn't force rework if done before *or* after them. Larger and more novel than the others (new per-element `bst show` capture).
7. **`UX-20`** (batch/map-reduce reporting) - zero dependencies, reporting-layer only, doesn't touch the capacity-check cluster at all. Good filler for a narrower-context session, same role `UX-04` played earlier.
8. **`UX-19`** (resource/scheduler-wait re-saturation + retry-gap decomposition) - zero dependencies on anything above, deep attribution-engine work, fully self-contained. Substantial; a good pick for a session with room for real design work.

**Phase D - large, higher-risk, most speculative (do last, and do the spike before committing):**

9. **`UX-11` risk-reduction spike** (not full implementation yet) - verify the two load-bearing, currently-unverified assumptions in its own leading candidate design before committing further work: does PATH-shadowing `bwrap` actually survive BuildStream's cache-key computation unchanged (real risk of silently invalidating caches, contradicting the design's own stated constraint), and how much real coverage is lost to statically-linked binaries in a real toolchain. A small real prototype against a live BuildStream sandbox answers both cheaply, before investing in the rest.
10. **`UX-11` full implementation** - only once the spike confirms the leading candidate design is viable (or a different option is chosen instead).
11. **`UX-14` tier 2** (contention-aware duration model) - explicitly gated on `UX-11` existing first per its own doc; needs real per-task CPU-vs-wall-clock data `UX-11` would supply to have any honest grounding.

## Decisions made during housekeeping (2026-08-16)

- **`UX-17` scope**: three options were presented (minimal wiring-only fix that stays practically inert per `P1-33`'s own gating; wire `effective_cpus` from `host_cpu_count`/`cpu_budget` but keep Part 30.3's check as a genuinely separate formula; or the same wiring plus delegating fully to `UX-12`'s already-correct `_check_process_oversubscription` logic). **Decided: delegate to `UX-12`'s check** - the two checks would otherwise compare the same real inputs via two independently-derived threshold formulas, risking divergent verdicts for the same real condition. `UX-17`'s own doc updated with the resolved Required Fix.
- **`UX-22` vs. the aggregate checks (`UX-16`/`UX-17`/`UX-21`)**: no live decision was actually needed here - re-reading `UX-22`'s own filed doc found it had already committed to staying additive/decoupled (its own "Out of Scope": *"The aggregate, single-global-value oversubscription check `UX-12`/`UX-16` already implement - this task is additive... not a replacement"*), consistent with the recommended order above. Noted, not re-litigated.
- **"Does `bga`'s analysis flow try to fully utilize `builders x native_max_jobs`?"** - checked directly (zero references to `native_max_jobs` in `bga/floors/` or `bga/replay/`) and found **false**: `LB`/`efficiency_score`/replay use `builders` alone, per `UX-13`'s own deliberate Part-16 scoping. Not a gap, so not a task - if a fuller CPU-utilization-targeting mode is ever wanted, that would be a real, separate design discussion that would contradict this existing, deliberate scoping and needs to be opened explicitly, not folded into any currently-filed item.

## Filing history (why each item was filed, in the order it was filed)

1. ~~`UX-01` and `UX-02` first, in either order~~ - **both done.** `bga compare BASELINE CANDIDATE` and `efficiency_score` are now real; the next optimization-iteration work session can lean on the tool instead of manual eyeballing.
2. `UX-04` is independent and small - good filler for a narrower-context session.
3. `UX-03` is now unblocked (depends on `UX-01`/`UX-02`, both done) - a natural next pick.
4. `UX-05` is in progress, written from a real optimization transcript (`examples/04-critical-path-optimization` + its `optimized/` variant) rather than a hypothetical one.
5. `UX-06` and `UX-07` were found *while doing* `UX-05`'s real optimization work - both are correctness bugs (not UX-flow gaps) discovered via real `bst build` + `bga analyze`/`bga compare` runs, deferred to backlog per this session's scope rather than fixed inline since both touch widely-referenced code (the core extraction pipeline's timestamp reconstruction, and run-identity's manifest shape referenced across ~20 files). `UX-06` is the higher-priority pick next since it likely affects every example project's CI-reported numbers, not just the new one.
6. `UX-09`/`UX-10`/`UX-11` came from a second, more realistic round of `UX-05` (`examples/05-cmake-cpp-toolchain` - real CMake/C++ builds, not `sleep N`), directly testing the user's own hypothesis that `--builders` and native `max-jobs` compete for the same CPU cores. `UX-09` is done (confirmed with real evidence); `UX-10` is done (`total_duration_us` now prefers real wall-clock); `UX-11` is a design brainstorm for a substantial future tool, not attempted yet.
7. `UX-12`/`UX-13`/`UX-14` are a follow-up brainstorm asking, once `UX-09`'s finding was confirmed and `UX-06`/`UX-10` were fixed, "does `bga`'s own measurement/report model actually reflect the builders×max-jobs contention effect, or is it still invisible to the tool?" - answer: still invisible, on three distinct fronts. `UX-12` is the cheapest, highest-leverage pick (pure capture/instrumentation, no math change) and directly supplies the real numbers `UX-13`'s report caveat and `UX-14`'s sweep caveat would want to cite. `UX-13` is a report-honesty-only fix (no math change, small). `UX-14`'s tier-1 minimum acceptance bar (an honest caveat in the actual CLI output, not just the spec doc) is now done; its full fix (a contention-aware duration model) is real, hard design work still likely gated on `UX-11` existing first.
8. `UX-15` came from the user directly challenging `UX-12`'s design once it shipped - a real, evidenced correction (cgroup CFS CPU quotas are invisible to `os.sched_getaffinity`, `UX-12`'s own detection method) rather than a hypothetical preference, folded into the same round as `UX-14` since both touch the same capacity-checking code path.
9. `UX-16`-`UX-19` came from an external review of the merged `UX-12`-`UX-15` work, triaged by independently re-verifying each claim against the real code before filing (not taken on the review's word) - two claims turned out to already be known, previously-documented, deliberately-deferred limitations (`UX-19`, reconfirming `P1-39`'s own explicit invitation to file the deferred consolidation separately), one was a real, reproduced bug in the new code (`UX-16`, a truthiness-vs-`is None` gap on BuildStream's real `max-jobs=0` sentinel), and one was a real, previously-undiscovered bug found by verifying the review's general architectural concern against the actual codebase rather than just the two examples the review itself cited (`UX-17` - `UtilizationAnalyzer`'s own oversubscription check has been dead code all along, and is the concrete case the review's abstract "naming trap" concern warned about). `UX-18` closes a real, concrete consistency gap the review surfaced between `bga`'s two documented run-context.json producers. Several other review claims (that `native_max_jobs` isn't auto-extracted from `bst show`/the log; that a `max_jobs`-vs-`native_max_jobs` internal rename is warranted on its own; that current report wording conflates "potential" with "observed" CPU usage) were checked and found to be either already-correct, already-deliberate, or not worth a dedicated task on their own - not filed.
10. `UX-20`-`UX-22` came from a further round of user brainstorming on top of `UX-12`-`UX-19`, each independently checked against the real code (not filed on the idea's own merits alone): `UX-20` (large-graph batching) confirmed a real, existing-but-invisible `sensitivity.top_opportunities` signal and a real absence of any multi-element batch simulation; `UX-21` (memory/swap oversubscription) confirmed zero memory accounting exists anywhere in `bga` today, a genuinely new gap, not an incomplete existing feature; `UX-22` (per-element `max-jobs`/serialization-point detection) elaborates a limitation `UX-12`'s own doc had already named and declined for a first pass, with a real, compelling motivating scenario (a large single-synchronization-point element like an LLVM build). A separate claim - "does `bga`'s analysis flow try to fully utilize `builders x native_max_jobs` as its scheduling-capacity target?" - was checked directly (`bga/floors/`, `bga/replay/`: zero references to `native_max_jobs` in either) and found **false**: `LB`/`efficiency_score`/replay all use `builders` alone, per `UX-13`'s own deliberate Part-16 scoping - not filed as a task since it's a factual question, not a gap, and reopening that scoping would be a real, separate design discussion if ever wanted. A concrete external design proposal for `UX-11` (`LD_PRELOAD` + `bwrap` PATH-shadowing process-lifecycle tracing) was evaluated and incorporated into `UX-11`'s own doc as its current leading candidate design, with real open risks (static-binary coverage gaps, an unverified BuildStream cache-invalidation assumption, musl/non-glibc `LD_PRELOAD` support) flagged for whoever picks it up.

11. `UX-71`-`UX-76` came from a user brainstorm after round 9's MVP verdict, asking two things: whether the report could be **more concise, actionable, and able to enable parallel optimization workstreams**, and whether **every valuable finding actually reaches the JSON report** or only a cut of the text one. Each was checked against round 9's real published capture (`5eda28a`) rather than filed on the idea's merits: the concision question surfaced a live regression (`UX-76` - `UX-70` re-sorted a shared helper and quietly changed what "Where the time is" means) and three overlapping headline rankings; the parallelism question surfaced that the tool already owns the machinery (`compute_realizable_savings`, `batching.py`) but points it at a saturated candidate score, so it returned **0 groups on real data** while two of the build's six heaviest elements sit unmentioned two fixes away (`UX-74`); and the JSON question turned out to cut **both ways** - JSON has no conclusions, text has no `aggregating_dependencies` (`UX-75`). Investigating what the join *could* say then produced the two sharpest items: `UX-71` (the join's headline verdict is unreachable on real data because its ranking metric is a constant) and `UX-72` (three of Plane 2's findings are read, the rest are dropped), plus `UX-73`, a producer-side false-positive rate that would be inherited the moment `UX-72` wires redundancy into the join. Ordering: `UX-71` then `UX-72` (both correct the join, and `UX-73` gates the redundancy half of `UX-72`), `UX-76` is a small independent fix worth taking in the same pass, `UX-74` is the largest and most valuable, and `UX-75` is deliberately last because it should serialize whatever conclusions the others settle on.

## UX-215..UX-226: the twenty-fourth audit round — the relationship layer already exists (2026-08-22)

Round 24 evaluated a third external review of the shipped viewer, the
same way as the previous two: claim by claim, against the code, every
premise checked before any of it was agreed to. Its direction is right
and its diagnosis — *the missing thing is relationships between
existing information* — is correct. Its cost model is wrong in three
places, and once in the cheap direction.

The finding is that the relationship layer **is already computed and is
not published**. `bga/correlate.py:141` assembles an `ElementJoin` per
element — Plane 1's path share, saving and blast radius beside Plane
2's achieved parallelism, CPU coverage, peak RSS and dominant binary —
and `bga correlate --format json` emits it, correctly and
completely, as an **unversioned blob nothing can consume**: no `schema`
stamp, no view-hints, not served by `payloads()`, and
`correlate --schema` answering *"correlate produces no versioned JSON
output"*. So what the review proposed building as a viewer feature, and
separately as a new "three-plane investigation ladder", is one
already-computed join missing a contract — `UX-206`'s pattern for the
fourth time ([`UX-215`](../UX-0215-publish-the-join-the-tool-already-computes.md)).

Verification added what no review sees: **round 23 shipped nineteen
links to nowhere.** `UX-208`'s Inspect anchors at `#${cssId(uid)}` and
nothing ever sets that id — measured on `examples/06`, 11 of 11
distinct targets unresolvable, while the guards asserted the affordance
existed rather than that it arrived
([`UX-216`](../UX-0216-every-element-is-one-object.md)).

Three of the review's premises did not hold: the schema does **not**
already describe the metrics that need describing (`floors` is 0 of 0)
([`UX-220`](../UX-0220-the-numbers-that-need-a-sentence-have-one.md));
`compare/v1` carries **no** per-element deltas, so the culprit strip is
a payload item first
([`UX-221`](../UX-0221-which-elements-caused-the-regression.md)); and its
element-inspector *drawer* was declined in that shape — overlay
machinery is the one part of this page that would not survive an
export, a print, `filter: grayscale` or a pasted anchor, and a section
gets the same value while making `UX-208`'s dead anchor resolve as a
side effect. Its "resist adding more charts" was agreed and not filed:
that is Direction 7's standing position already.

What the review did not look at is the **loop** rather than the report —
every item it proposed improves one reading of one report, while the
repetition lives in capture → analyze → read → change → capture again.
Three items came from walking that instead: the next three commands are
always retyped and can be published and rendered
([`UX-218`](../UX-0218-the-next-step-is-a-command-you-can-run.md)), the
investigation is not resumable because the *decision* is nowhere
([`UX-225`](../UX-0225-the-working-set-travels-in-the-link.md)), and
"did my fix work?" is answered by opening two reports side by side
([`UX-226`](../UX-0226-what-happened-to-this-element-since-last-time.md)).
Full narrative: [`../../audits/round-24.md`](../../../audits/round-24.md).
