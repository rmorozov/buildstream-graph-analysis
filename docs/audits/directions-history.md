# Design directions: the history

The round, status and verification chapters [`directions.md`](../design/directions.md) carried between its
Directions, moved here verbatim by `UX-1293` so that page reads as the
argument it is. Each chapter is a dated record, not current state.

## Implementation status (updated 2026-08-16, round complete)

**All fourteen items of the `UX-27`..`UX-40` round are done.** What
follows below is the argument that produced them, kept because the
reasoning is still the reasoning - but several of its complaints are now
historical, and are marked where they are.

Four of the round's own filings were corrected during implementation
rather than implemented as written. That is worth more than the fixes
themselves as a signal about how the next round should be run:

- **`UX-28`'s evidence did not support its claim.** It cited an 81%
  per-element contention increase as proof the oversubscription check
  could not fire. The two runs were not comparable and the costlier one
  was 30.5% *faster* overall - beneficial parallelism, not harm. The real
  defect (a bar whose ratio-to-cores collapses as the host grows) was
  different, provable, and only found by checking the fix against
  `UX-09`'s existing measurements instead of against the intuition that
  produced the filing.
- **`UX-32`'s proposed headline metric was backwards.** Achieved-vs-requested
  scores a `-j1`-pinned element at 200% of what it asked for; being pinned
  *is* the problem.
- **`UX-30` and `UX-40` each carried a secondary claim that was already
  implemented** (monotonicity violations are shown; the fail-open does
  warn). Both were pinned by tests rather than "fixed".

The rate is roughly one filing in four. A round of audit findings written
from a single hands-on session should be treated as *hypotheses with
evidence attached*, not as a work list - and the cheapest way to catch
the bad ones is to re-check each against measurements the repo already
has before writing any code.

## Round 24: publish the relationship, then navigate it

A third external review, evaluated the same way as the first two. Its
one-line statement of where the tool is, adopted:

> the next improvements should not make the page prettier; they should
> turn existing BGA facts into stronger navigation and investigation
> primitives.

**The finding that reframes it.** `bga/correlate.py:141` already
assembles the relationship layer — one `ElementJoin` per element,
Plane 1's path share, saving and blast radius beside Plane 2's
achieved parallelism, CPU coverage, peak RSS and dominant binary. `bga correlate --format json`
emits it, correctly and completely — and unversioned: no `schema`
stamp, so `UX-190`'s contract does not cover it; no view-hints, so the
viewer could not render it generically; and `payloads()` does not serve
it. `correlate --schema` says so itself: *"correlate produces no
versioned JSON output"*. So the "element inspector" and the "three-plane
investigation ladder" the review proposed as new work are one
already-computed join missing a contract.
That is this project's oldest pattern, on its fourth occurrence after
`blast_tree`, `headline` and the compare payload the band needed: **the
analysis knows, and the published schema does not say.** Direction 7's
rule is what makes the fix cheap and the shortcut expensive — a viewer
that assembled the join itself would be the second analyzer the whole
architecture exists to prevent.

**And the correction to round 23's own work.** `UX-208` shipped a
generic Inspect on every element row, anchored at a fragment nothing in
the page sets: 19 links, 11 distinct targets, 11 unresolvable. The
guards asserted the affordance existed, not that it arrived. Same
failure class this project keeps finding, in the round that was about
finding it — which is the argument for `UX-216` naming resolution, not
presence, as its acceptance.

**Declined, with the reasons recorded:** the element inspector as a
*drawer*. Overlay machinery is the one part of this page that would not
survive an export opened from a downloads folder, a print,
`filter: grayscale`, or a pasted anchor — and a section gets the same
cross-reference value while making the dead anchor resolve as a side
effect. "Resist adding more charts" was agreed rather than filed: it is
this document's standing position already.

**What the review did not look at: the loop.** Every item it proposed
improves one reading of one report. The friction this tool is built
around is `capture → analyze → read → change → capture again`, and that
is where the repetition is. Three items came from walking it — the next
three commands are always retyped and can be *published* (so the
terminal, CI and the page agree on the next step rather than the viewer
deciding), the investigation is not resumable because `UX-211` carried
the view and not the decision, and "did my fix work?" is still answered
by opening two reports side by side.

## Round 25: the first four, executed

Round 24's argument, executed. Four items, in the order the audit
recommended, and the order mattered: nothing after the first is honest
without it.

**`UX-215` was a stamp, a schema and thirty lines of wiring**, and it
is the one that made the rest cheap. `correlate/v1` publishes the
`ElementJoin` that `bga/correlate.py` had been computing since `UX-51`
and emitting unversioned. Then the viewer needed **no change at all**
to draw it: measured on `examples/06`, an eleven-row `element_join`
table under its declared question, with the element role earning every
row an Inspect. That is `UX-193`'s schema dispatch paying for itself,
five rounds after it was built — and the clearest argument yet for the
rule that a field enters the published contract first.

**`UX-216` fixed the round-23 defect and was the reason to look.**
Nineteen Inspect affordances resolving to nothing, because the guard
asserted the affordance *existed*. The acceptance is resolution now,
and the fix is one expression rather than two: `cssId` delegates to
`elementAnchor`, because a link and its target spelling drifting apart
*is* the defect. The mutation that proves it is not renaming the anchor
— it is duplicating the expression with a different character class,
which is exactly how it would recur.

**The drawer was declined and the reasons recorded**: overlay machinery
is the one part of this page that would not survive an export from a
downloads folder, a print, `filter: grayscale`, or a pasted anchor. A
section is linkable, printable, collapsible by machinery that exists,
and it makes the dead anchor resolve as a side effect.

**A guard stopped being about the calendar.** The page-size ceiling was
crossed by ordinary feature work in three consecutive rounds and raised
twice. A number that moves whenever a feature lands is measuring the
calendar, so the third time the *measurement* changed: composition (the
page **is** the checked-in modules plus the stylesheet — the only check
that can tell 6 KB of feature from 6 KB of vendored library),
Direction 7's ratio at the scale the rule names (1,000 elements:
691,401 B of data against a 97,488 B page, **7.1x**), and a loose
structural backstop. The small fixtures invert the ratio and always
did; that is a property of small reports, not of the viewer, and it is
why the absolute was the wrong instrument all along.

**`UX-218` is the first item aimed at the loop rather than the
report.** `next_steps` is published, so the terminal, CI and the page
give the same next command — and the branch that chooses it stays in
the pipeline, because a viewer that picked the next command from
`chain_share` would be the second decision-maker `UX-207` exists to
prevent. The acceptance is not "a command is shown" but "the command
runs": every published `argv` is executed against the fixture. What is
*absent* is asserted too — a chain-bound build is not told to add
builders, a run outside a store is not told to compare.

## Round 26: the eight that were left

Round 24 filed twelve items; round 25 took the first four. These are the
other eight, and the pattern across them is one thing said three ways.

**Twice a task file was wrong about the code, and both errors were worth
finding.** `floors.certified_us` — named in UX-220 as "the most
misreadable number this tool publishes" — has never existed; the
certified floor is `floors.lb`. And UX-221 said no element appears in
`compare/v1` anywhere, when in fact `element_diff` has carried
*appearance and removal* since UX-79 — the two cases the file predicted
a naive join would drop were the two already present, and the elements
in **both** runs, which is what "because of what?" actually asks about,
were the ones missing. An audit is a hypothesis. Reproducing it first is
not ceremony.

**Twice a mutation a task file specified could not fail.** UX-219's
"re-add the savings instead of reading `cumulative_saving_us`" cannot
discriminate on any real report, because the two are equal by
construction. UX-221's "sort the strip by its own computed delta" passed
because the four-case fixture puts exactly one element in each group and
no assertion about the order of a one-element list can fail. Neither was
counted. One was replaced with a synthetic payload where the two values
differ; the other with a three-regression fixture. A mutation that
cannot redden is not evidence, and writing it down as though it were is
the failure this discipline exists to prevent.

**Three times a guard had to change, and each change is recorded as a
decision rather than absorbed.** UX-201's fixtures were pinned to three
`utilisation` keys no code path emits — re-pointed at published fields
rather than deleted, and they still catch the original renderer bug.
UX-196's "only two custom drawings" asserted a count while its docstring
stated the rule; it holds the named set now, which also catches a
drawing being moved or removed. And the page-size backstop was crossed
for the fourth round running.

### The backstop, and what a number cannot measure

UX-218 replaced an absolute page ceiling with composition + ratio + a
loose absolute, having watched the old ceiling get raised twice, and
wrote the reason down: *a number that moves whenever a feature lands is
measuring the calendar*. Round 26 crossed the new absolute too.
Measured at the crossing:

```text
page (data removed)   123,785 B
  modules             109,913 B
  style.css            12,552 B
  index.html            1,433 B
  accounted           123,898 B   = 100.1% of the page
export total          184,934 B   = 2.20% of the 8 MiB attachment budget
```

Every byte is a checked-in module. So the backstop did its job — it made
someone look — and the answer was "a round landed", for the fourth time.
The stated purpose was to catch *something structural*, and a byte count
cannot tell a feature from a library.

It is raised to 200,000 and now stands beside a guard that measures the
thing directly: no module may look like vendored or minified code — a
few enormous lines, almost no comments. That guard catches a 12 KB
minified blob which **both** the byte ceiling and the composition guard
let through. If the absolute fires again it should be because that one
is silent and something genuinely odd is happening.

### What the round added to the loop

The first five rounds of the viewer made the report readable. This one
made it *resumable*: the horizon is a plan rather than a table, an
element can be focused, the reader's own marks travel in the link, and
each element carries what it cost across the snapshots. Round three of
an optimization no longer reads exactly like round one — which was
UX-225's complaint, and is the closing of the loop UX-126 opened.

Two clauses were declined and recorded rather than quietly dropped: a
global key to open the palette (it needs a decision about the table
filters UX-205 put everywhere), and markdown detection for the copied
finding (a button claiming to know what a paste target accepts would be
guessing).

## Round history

This document used to carry the findings of rounds 2-6 inline, which
made it an argument about direction *and* a changelog. They live with
the other rounds now. A row does not type a verifier count: round
142's said "seven" when nothing read `agent-runs.md` to check it, and
by review time the round document itself said seven too — the count
lives in `agent-runs.md`'s rows, counted per round from there.

| round | what it found |
|---|---|
| [2](round-2.md) | scale probe — the tool at 1200 elements |
| [3](round-3.md) | cross-checking quantities that ought to agree, and did not |
| [4](round-4.md) | the plane seam, settled by measurement |
| [5](round-5.md) | the structural plane against a real project's graph |
| [6](round-6.md) | every real CI build is incremental |
| [7](round-7.md) | plus the planning notes this document used to carry |
| [8](round-8.md) | element attribution, 14.9% -> 86.1% |
| [9](round-9.md) | the first real freedesktop-sdk capture |
| [10](round-10.md) | both usage scenarios walked end to end |
| [11](round-11.md) | round 10's fixes re-verified; verification discipline is where the defects were |
| [12](round-12.md) | directions 3-4 re-verified; the MVP verdict: met |
| [13](round-13.md) | round 12's fixes re-verified; the polish direction opened (`UX-125`..`UX-127`) |
| [14](round-14.md) | the polish verified as a user; the docs read as a stranger (`UX-135`..`UX-145`) |
| [15](round-15.md) | a real field failure the tool cannot see; the diagnosability chain filed and the fix claims re-verified (`UX-147`..`UX-154`) |
| [16](round-16.md) | the tool meets a big project: a failed build verdicts IMPROVED, Ctrl-C destroys the trace, auto-spine bills every nested layout (`UX-156`..`UX-162`) |
| [17](round-17.md) | all eight round-16 landings verified live and holding; the new findings are seams between verified features (`UX-163`..`UX-168`, plus `UX-169` from fixing them) |
| [18](round-18.md) | every measured number reproduced exactly — the clean audit's tail is guards weaker than their prose; Direction 6 opened from the user's monorepo question (`UX-171`..`UX-177`) |
| [19](round-19.md) | the source axis landed and met its own output: the printed identity does not round-trip, and one guard passes with its sorter reverted (`UX-178`..`UX-182`) |
| [20](round-20.md) | the field speaks: nine usage observations ground-truthed into ten filings, and the elision that reopened the round-trip (`UX-183`..`UX-192`) |
| [21](round-21.md) | all ten field landings verified holding; Direction 7 argued — the viewer as a thin window onto the JSON, timelines to Perfetto (`UX-193`..`UX-197`) |
| [22](round-22.md) | the viewer landing verified; the field and an external review synthesized into Direction 7's second iteration, plus two shipped views nobody can reach (`UX-198`..`UX-206`) |
| [23](round-23.md) | eight of nine round-22 landings hold; the ninth's guards only guard one machine. A second external review's Pareto turn adopted — decision first, everything an action — and its blind spots filed with it (`UX-207`..`UX-214`) |
| [24](round-24.md) | the relationship layer the third external review asked for is already computed in `correlate.py` and published nowhere; round 23's own Inspect anchors resolve to nothing; three of the review's premises corrected, and the loop it did not look at filed (`UX-215`..`UX-226`) |
| 25 | round 24's first four executed: `correlate/v1` published and the viewer drew it with no change; the dead anchors resolve; findings show their evidence; the next command is published rather than derived. The page-size ceiling stopped being a number and became a ratio (`UX-215`..`UX-218`) |
| 26 | round 24's remaining eight executed: the schema learned to say what its numbers mean, `compare/v1` learned which elements changed, the store learned to remember one, and the page learned to draw a plan, focus one element and carry the reader's own marks in the link. Two task premises corrected and two mutations rejected for not discriminating (`UX-219`..`UX-226`) |
| [27](round-27.md) | twenty for twenty on the eighteen-commit landing, two hollow guards filed. The role model written: four roles served, four unserved; Direction 8 (provenance) adopted from the fourth review, its workspace declined; Direction 9 (the team axis) opened from the user's positioning (`UX-227`..`UX-235`) |
| 28-39 | the sibling's execution rounds: UX-236..295 landed, Directions 10-14 argued — recorded in each direction's section and the backlog's round sections rather than as audit files |
| [40](round-40.md) | the field's first architectural showstopper: a 2 GB dual-plane snapshot OOMs `bga view` — every load path measured, ~95 % of the monolith unread, the streaming fix on the wrong path; Direction 15 argued (events as a Perfetto TrackEvent stream, capture computes / view serves) and the rounds 28-39 sample verified six for six (`UX-296`..`UX-301`) |
| [41](round-41.md) | a design round while Direction 15 executes: the user's brainstorm became the visual contract (`styleguide.md`) — shape→control mapping, sparklines and density strips, a measured-and-budgeted palette (two validator failures found), dark first with print kept honest (`UX-302`..`UX-306`, Direction 16) |
| [43](round-43.md) | Direction 15 and the visual contract verified eleven for eleven, fourteen mutations discriminating; then the user's question answered by inventory — the trace speaks Perfetto's format and none of its vocabulary, while the capture holds the content for all of it (`UX-308`..`UX-312`, Direction 15's second iteration) |
| [44](round-44.md) | the trace vocabulary verified seven for seven with one dead question surviving its own class's purge; the user's thirteen readability observations became four visual-contract sections — drawing grades, apparatus placement, the depth budget and table focus, the click budget (`UX-316`..`UX-321`) |
| [45](round-45.md) | the guides walked by a stranger: four bugs forty-four feature rounds never saw — the no-bst traceback, the user-install crash, the self-crashing printed command, the ghost invocations — plus the round-44 landing verified with one cascade evasion (`UX-324`..`UX-332`) |
| [46](round-46.md) | three field errors measured to mechanisms — the trim that interns 3,000 compiles to two names, the CSP that silently breaks tick labels on served pages, the TypeError that was never bga's — and the implementation loop re-tooled with a measured 2.5× (`UX-333`..`UX-336`) |
| [63](round-63.md) | seventeen implementation rounds (47-62) recorded in the backlog's own sections, then the sibling's outsider walk run twice: six populations vanish between a cold and an incremental run, fourteen Plane 2 blocks reach no browser, and the Tabulator question filed as a product decision (`UX-388`..`UX-397`) |
| [64](round-64.md) | the walk that judged the answers: against example 06's `optimized/` answer key, Plane 2 names every intended fix and correlate compresses them into one 12.9 s paragraph that reaches no page; the rounds 47-63 landing held eleven-of-twelve under falsification; the library question answered with a factory measurement, and the test plan built from the escape ledger (`UX-398`..`UX-410`) |
| [64 · the guard census](guard-census-round-64.md) | the falsify ritual run as a sweep rather than the per-round sample it had been since round 18: eleven guard families, one mechanism-revert mutation each, so that a family with no discriminating guard is found rather than a file (`UX-403`) |
| [72 · the planted-defect walk](planted-defect-walk-round-72.md) | three defects **chosen first**, generated into real BuildStream projects with `tools/bga_gen_project.py` and built by a real `bst`, recording how far the front door gets each reader towards the answer that was planted (`UX-468`) |
| [74](round-74.md) | rounds 65-73 reviewed as a workflow and measured — a 5m30s suite gated per item, 60 KB read before every task file, Outcomes at a median 114 lines, 12 % of commits housekeeping; a Register section and its guard, the `decompose` and `orient` skills landed, and the lifecycle's remaining steps filed (`UX-497`..`UX-506`) |
| [75](round-75.md) | the round-74 slate closed under its own decomposition — three implementer tracks in worktrees (943-1,174 s, 81k-131k tokens each), `UX-500`'s first count (Regime A: 15 suite runs, two misses outside the selector's set), the rules card, the derived index, the self-recording CI reference (`UX-500`..`UX-510`) |
| [76](round-76.md) | the tail closed, and `main` found red from CI's own adopt commit — the batch gate cannot assume a green base (`UX-511`..`UX-517`) |
| [77](round-77.md) | three field reports about waiting, measured and filed — the `bst show` tail on big projects, a run bundle to carry, a Perfetto button silent for minutes (`UX-518`..`UX-521`) |
| [78](round-78.md) | the three field reports implemented under a decomposition, everything shipping in the bundle by default (`UX-518`..`UX-521` closed) |
| [79](round-79.md) | the controls walked on a two-plane page (782 in 193 classes): the "All rows" table is nested rows migrating into their parent; the served page is the capture-time analysis; the volume budget breached at the top of its own class; the suite weighed — forty browser files are half its seconds (`UX-522`..`UX-536`) |
| [80](round-80.md) | the round-79 slate closed in six worktree tracks: `UX-500`'s second regime measured and refused — **4 of 9** defects the batch gate caught were outside `test-touching`'s set, so fixing guide §3 stays; a run bundle you can carry, `analyze/v5`, the export's data half bounded and compacted, and three cross-track collisions only a merge could see (`UX-514`, `UX-516`..`UX-539`, `UX-92`) |
| [81](round-81.md) | twenty-two rows, seven premises falsified by measuring — the drift gate's cause filter, a stale base under both tracks, the suite line that was not the run's (`UX-538`..`UX-562`) |
| [82](round-82.md) | every document read against the tool by five researchers: a sentence a guard reads is exact, a sentence no guard reads has drifted — twenty-four filings asking for derivation and dating, and the `review` skill (`UX-563`..`UX-586`) |
| [83](round-83.md) | round 82's twenty-four rows executed, most of them not "correct a sentence" but "give the sentence a guard and let the correction follow" — the `UX-549` shape (a figure the guard derives) and the `UX-511` shape (a block labelled with its date and its cuts), extended to where round 82 found them missing (`UX-563`..`UX-586`) |
| [84](round-84.md) | the fifteen rows round 83 filed rather than fixed, seven tracks wide — and the round where a filed premise is re-measured before it is implemented, because `UX-589`'s was false and `UX-592` had already refuted it (`UX-589`..`UX-604`) |
| [85](round-85.md) | the rows round 84 left, plus the seven the round filed against its own work and six from architecture review 15 — and the round where a premise **carried forward** is a sentence again: seven of nineteen moved under re-measurement, five of them written by the orchestrating session from another track's report (`UX-604`..`UX-627`) |
| [86](round-86.md) | the rows round 85 left and the three this round filed — and the round where every item turned out to be one shape: **a guard's population is bounded by a rule somebody typed**, and where that rule is wider than the claim the guard goes quiet rather than failing. Six of eight, plus the session's own undeclared skip reason (`UX-597`..`UX-635`) |
| [87](round-87.md) | the `bga view` walk that began with pressing Expand twice — four tracks on disjoint modules, and the round where **three of six filings were corrected by the measurement that implemented them**: `UX-638`'s mechanism needed a scroll inside focus, `UX-640`'s not-a-defect held only where the listener runs, `UX-642`'s broken population was the smaller half. All three shared-value merge hazards fired and each merged cleanly into a wrong number (`UX-638`..`UX-649`) |
| [88](round-88.md) | round 87's eight open rows, five tracks wide, plus the review the cadence guard called due — and the round where **four rows were closed by disproving their own premise**, three of them the orchestrating session's: settling was not the geometry gap, the shallow-clone sweep was already closed, the reader map was derivable, and nine page-built sections were thirteen (`UX-636`..`UX-656`) |
| [89](round-89.md) | round 88's five open rows in three parallel tracks, and the round where **every closed row was the same defect at a different scale**: a fact written twice, one copy guarded and exact, the other drifted — plus three more found while working, one of them two rows round 88 wrote by hand (`UX-651`..`UX-659`) |
| [90](round-90.md) | the process given a ledger — reporters on `sonnet`, the walk and the design review as skills, a run ledger — and the page looked at through seven screenshots: the rail as a source list, a reader as a shape not a hue, a runbook as a shape, a rail click that overshoots (`UX-663`..`UX-674`) |
| [91](round-91.md) | a design round: whose question utilization is — the tool counts processes where the CI owner needs cores, computes idle intervals it never publishes, exempts foundations by kind so a toolchain is not exempt, and has no change frequency; Direction 17 argues the envelope, the jobserver, priced remote execution and expected rebuild cost (`UX-675`..`UX-684`) |
| [92](round-92.md) | a design round on the test workflow: the suite verifies what was built and the walk what was promised — exploration as a seeded scenario that grows the answer key, a release that waits for the walk, the impact set derived, areas as a view, the architecture prose moved one area at a time, a shape budget, a flake ledger, the invariants for any shape (`UX-685`..`UX-692`) |
| [93](round-93.md) | a design round on the development workflow: the gate holds the numbers and the review holds the design — the rule set widened by layer and pinned, a finding baseline that is zero-tolerance for new findings and a size ledger that queues the refactor stream, a burn-down on the reporters' model, the register's unguarded rows, a type baseline, a gate-only shelf on GitHub, the viewer linted, an AST symbol index in place of CodeQL for navigation, a `self-review` skill, a performance ratchet, a weekly mutation run (`UX-693`..`UX-705`) |
| [94](round-94.md) | a process round on the pipeline: a task's shape derived from its text names the model that runs it, the implementer on `sonnet` for mechanical and bounded shapes, the orchestrator's cost measured as its live context at each rebuild (73 %), one task per track rather than per session; the rebuild count, a priced first batch, a batch close, a derived ledger row and a screen-long tool result filed (`UX-706`..`UX-711`) |
| [95](round-95.md) | the first batch under the pipeline: the rule set widened by layer in one auto-fix commit with the tool pinned (`UX-693`), three bounded tracks on `sonnet` each read by a verifier — the symbol index, a batch `--move`, a session's rebuilds priced, a ledger row derived, the finding baseline (`UX-700`, `UX-707`, `UX-709`, `UX-710`, `UX-694`); eleven defects found by the verifiers, none by the tracks; three tracks lost to an interrupt and the rule that follows |
| [99](round-99.md) | three judgements closed by direct commit and no track dispatched — `UX-729`'s rename guarded across all 22 modules, `UX-733`'s two fan averages named equal by construction, `UX-732`'s merge test replaced with a combined diff; `review 18` ran in the same window and filed the three ids round 100 closes (`UX-734`..`UX-736`) |
| [100](round-100.md) | five ledger rows — two for `UX-732`'s reworked track, one each for `UX-734`'s three counted figures, `UX-735`'s export size and `UX-736`'s status table — plus `UX-731` and `UX-730` closed directly; zero verifier runs, the first of three rounds in a row with none |
| [101](round-101.md) | seven ids closed by a track merge each (`UX-728`, `UX-737`, `UX-738`, `UX-717`, `UX-716`, `UX-692`, `UX-677`) and the ledger prices none of them; `UX-703`'s own closing commit names four lost transcripts and declines to guess a row, without saying which four of the seven it meant — an unresolved fact of the record, not this round's to settle |
| [102](round-102.md) | five ledger rows (`UX-667`, `UX-691`, `UX-702`, `UX-712`, `UX-703`) around a mid-round gate, `af56022`, that found three guards `UX-667`'s own track moved and did not visit — the gate a checkpoint inside the round the ledger names, not its edge |
| [103](round-103.md) | the guard whose population is narrower than its sentence, five times: four `implementer` tracks on `sonnet` each read by a `verifier` before merge (`UX-746`, `UX-749`, `UX-748`, `UX-674`), six rows closed by the session before them; the verifiers found four defects the tracks' own reports did not, two of which would have merged — an acceptance test that did not survive being committed, and a budget claim off by 524px; seven rows filed (`UX-750`..`UX-756`), two of them closed in the same round, and three CI reds all the session's own |
| [104](round-104.md) | the verifier earned the round: six `judgement` rows as `implementer` tracks on `sonnet`, each read by a `verifier` before merge, and three held — `UX-753`'s guard stayed green when the rule it checked was deleted outright, and `UX-744` claimed an independence that a mutation one function down disproved twice; five closed (`UX-750`, `UX-751`, `UX-753`, `UX-755`, `UX-756`), `UX-744` reverted after CI falsified a derivation no worktree could test, four filed (`UX-757`..`UX-760`); the gate itself was wrong — BuildStream sizes its 5% cache reserve against nominal disk, not free, which round 103 misdiagnosed as contention |
| [105](round-105.md) | the two rules the pipeline never wrote down: the verifier mandate moved out of `decompose/SKILL.md` — its only statement, in the document the guide outranks and never mentioned — into `fixing-guide.md` §3, with a guard pairing every merged `implementer` ledger row to a `verifier` row; and the gate bound to the commit that gets pushed, by a marker `make test` writes and a hook that reads it. Both rows held by their verifier: a pasted `grep` that did not reproduce, a skill line still restating the rule its commit message said it had stopped restating, and a hook an ordinary `git status && git push` walked straight past. Three filed (`UX-766`, `UX-767`, and the ordering into `UX-763`) |
| [106](round-106.md) | the agent workflow's own loop, and the guards that read a citation: four `implementer` tracks each read by a `verifier`, every track held at least once and every hold on a claim its own commands disproved — a `--force` that silently erased the previous one, a boundary sentence reversed with its `UX-767` citation intact that both new guards still passed, and a 10-line commit body visible only by running `tools/dev_commit_bodies.py`. Eight closed (`UX-757`, `UX-763`, `UX-765`, `UX-766`, `UX-767`, `UX-768`, `UX-769`, `UX-770`), one filed (`UX-771`). Two of the eight CI filed: a count guard matching `UX-503`, the id it names in its own failure message, and a cost-row median that sat on a 37/38 tie so this container wrote 38 where CI computed 37 on the same commit |
| [107](round-107.md) | a fix that retired a filed row, and a conclusion that outran its measurement: `UX-744`'s register landed as `{round, date}` with no ids column, which left `UX-759` — filed against that column's silent partial loss — with nothing to check and no runnable acceptance test, so it closed as a decline; the annotation was owed by `UX-744`'s own commit under the guide's item 6, which has no guard. Round 106 had recorded `UX-760`'s reserve as why `make test` could not pass; the spend was real and the conclusion was not — the margin was thin because the suite's own leavings had eaten it, which is `UX-773`. `UX-760`'s verifier found its population derivation cited two files that are not in the sweep it describes, and that the two files it deferred still redden at a negative margin (`UX-775`). Three closed (`UX-744`, `UX-759`, `UX-760`; `UX-764`'s track landed but the row stays open, which this row said wrongly until review 20), four filed (`UX-772`, `UX-773`, `UX-774`, `UX-775`) |
| [108](round-108.md) | three planned tracks and a fourth the round found under them. `UX-771` derives the section-numbering population, `UX-772` makes the register read a dateline rather than a document's first date — its verifier caught the first pass filtering the population on `document_date() is not None`, the same silent skip moved one layer down — and `UX-773` sweeps the browser and profile a `SIGKILL`ed worker leaves. `UX-781` is why CI was red while the tree was green here: `ci.yml`'s base-diff step ran `git fetch --depth=200` on a `fetch-depth: 0` checkout, which grafts a boundary (1,541 commits to 855, measured), so every step after it read a cut history. `UX-776`'s detector, two commits old, missed it — no parent object is absent when nothing was deleted — which is the third proxy for one question. It reads the traversal now. `UX-773` merged without a verifier; the run happened late, returned HOLD, and found three defects including one this session made while closing the round — moving a browser guard out of `MEDIUM` on the duration rule when that file is placed by construction (`UX-783`). Then `bst-tests` reddened on the push: it runs the whole `make test` on a default-depth checkout, and the guard for that asserted `"fetch-depth: 0"` appeared *somewhere* in the file, so the `test` matrix covered for it (`UX-784`) — the same population defect a third time in one round. Six closed (`UX-771`, `UX-772`, `UX-773`, `UX-781`, `UX-783`, `UX-784`), four filed (`UX-781`, `UX-782`, `UX-783`, `UX-784`) |
| [109](round-109.md) | the ten tracks rounds 100 and 102 merged unread, read: nine retrospective verifiers found eight code or guard defects and four false pastes against zero in the tracks' own tables (`UX-785`..`UX-793` filed). Then the open tasks the same way: `UX-698`'s GitHub shelf (CodeQL, pip-audit, a lock, Dependabot), `UX-682` and `UX-697` split into two tracks each against a session contract, seven filings in four tracks, `UX-778` — every track merged behind a verifier, and eight of nine verifiers returned a fix that landed before the merge. The `sizes` shelf reddened on the round's own head and was re-adopted once at the close. Worktrees open at `origin/main`'s old tip, a clean stop removes them, a verifier's editable install repointed the shared environment, and the hundredth ledger row raised `IndexError` (`UX-794`). Thirteen closed, eleven filed |
| [110](round-110.md) | the fifteen open tasks that fit a track, in three batches and two serial chains, every merge behind a verifier: `UX-744`'s register, four bounded rows, four rows behind one fix each, the spine guard reading what contention cannot move (`UX-741`), the guide's size figure derived (`UX-774`), the reader as a shape in the header (`UX-668`), the suite's shape table with a browser ratchet at 50.5 % (`UX-690`), a declared foundation tier (`UX-683`), the jump box writing its anchor (`UX-671`). Nine of fifteen verifiers returned a hold or a fix; four PASS verdicts carried a finding the track's table could not see. Review 21 at 30 closes found two records no guard reads. Six filed (`UX-796`..`UX-801`). Fifteen closed, eight filed |
| [111](round-111.md) | round 110's eight filings and the round-sized rows behind them, in parallel tracks behind verifiers: three renderers split behind a walked list each (`UX-695`), memory in the sweep (`UX-678`), the cached-build verdict (`UX-684`), remote execution priced two ways and never summed (`UX-680`), the viewer and Plane 2 chapters into area pages (`UX-689`, `UX-806`). Eleven of nineteen verifiers returned a hold. The gate reddened three times on findings nobody's diff touched — two of them filed and closed (`UX-804`, `UX-805`). Sixteen closed, three filed |
| [112](round-112.md) | the last three open rows, in parallel tracks behind verifiers, after one probe capture of `examples/06` the session took first: the max-jobs advice priced by replay as a stated floor (`UX-739`), its rows one per built element (`UX-808`, found by the probe), the jobserver spike measured — under-utilised share 0.857 → 0.214 at an unchanged wall, not a mode yet (`UX-679`) — and the projection chapter into its area page (`UX-807`). Three verifiers, three PASS, each with a finding the track's table could not see. Four closed, three filed |
| [113](round-113.md) | the two rows left, in tracks behind verifiers — the price's assumptions rendered in the text (`UX-809`), the Plane 3 chapter into the tools area page (`UX-810`) — and the shelf's two Dependabot pull requests unblocked: `UX-696`'s commit-body gate read Dependabot's generated 75-line body, so no shelf pull request could ever merge (`UX-811`); both branches brought to main, the fix ported, locks and ledgers refreshed, gated and pushed; review 22 at 808 closes found two records whose guard's population cancelled its own errors (`UX-813`, `UX-814`), closed in-round with the impact guard's (`UX-812`). Six closed, five filed |
| [114](round-114.md) | `UX-689`'s last two chapters, each its own row in a serial track behind a verifier: the ingestion path into the tools area page (`UX-815`), the `bga` area's chapters into a page of their own (`UX-816`), `architecture.md` 1044 → 490 lines outside the log and the series closed; walk seed 3 (the process storm, spine on) found three rows carried into the release (`UX-817`, `UX-818`, `UX-819`); 0.4.1 cut as a patch, the contract state 0.4.0's; after the merge, main's three adopt jobs found red since 2026-09-08 on a bare interpreter (`UX-821`). Four closed, seven filed |
| [115](round-115.md) | the owner's twelve considerations on the 0.4.1 page, each measured on the all-planes walk capture and the 1,202-element export and challenged against the guide: nine agreed, two declined as designed (filters under the cap, the run chapter as reference), one whose premise the page no longer shows (the twin is a toggle); a design review found eight more — a monotonic base rendered as "497003.7 h", five bare task ids, 47 visible payload keys, five joined fields with no column, the header's 149-char path. Four styleguide sections (§2f, §3i, §4g, §5b) and fifteen filings, `UX-822` to `UX-836`; none closed |
| [116](round-116.md) | the nineteen open rows in three waves of `implementer` tracks behind `verifier`s, judgement shapes with the decision in the brief: the header is identity only, the readers table gone, the From column an offset, the twin draws fifteen marks, the max-jobs advice one flat table, every joined field a column, the serial chains ranked, a declared source-kind map, and a guard that reads both exports for the register. Nine of seventeen verifier runs held, four on a guard that could not fail; `UX-817` to `UX-837` closed, the last filed at the gate for `structured.js`'s ceiling; review 23 at the gate, three filings open |
| [117](round-117.md) | a design round on the jobserver as a mode, on `UX-679`'s spike: a pin read from BuildStream's own argv is never joined, the pool follows busy cores and PSI rather than the load average by being a client of its own pipe, the key is safe by construction and guarded by `%{full-key}` both ways, tools that will not read the pipe hold tokens through a bind-mounted wrapper, and the analysis feeds the scheduler — priority by slack, memory from the plan, a token ledger in Plane 2. Direction 20; twelve filings, `UX-841` to `UX-852`; none closed |
| [118](round-118.md) | the fifteen open rows closed - review 23's three and Direction 20's twelve, the jobserver's three stages - as fifteen `implementer` tracks behind sixteen `verifier` reads on `sonnet`, the pull request open from the first commit; CI found three defects no local run could (the runner's PSI files, the read-only sandbox root), one track fork-bombed the box, and the evaluation example read the mode slower at every stage |
| [119](round-119.md) | the jobserver's value: round 118's verifier gaps closed (`UX-853` to `UX-855`), the snapshot switch (`UX-856`) and `examples/11-serial-giant` (`UX-857`) - one long element under a `max-jobs` below the core count, the server's shape on four cores; five `implementer` tracks behind five `verifier` reads on `sonnet`; the quiet-box pair the session ran read `auto` IMPROVED -10.6 % (286.53 s to 256.06 s, the giant's peak 2 to 3) where two loaded pairs had read it REGRESSED |
| [120](round-120.md) | a 16-core field capture read eight things off the page and eight rows closed - the pool that never grew past its opening seed (`UX-858`), manual recipes that never joined (`UX-859`), swap unpublished (`UX-860`), the capacity figure unclamped (`UX-861`), the twin's CSS (`UX-862`), the strip's ticks (`UX-863`), maps as pairs (`UX-864`), relative opens dropped (`UX-865`) - seven `implementer` tracks behind seven `verifier` reads on `sonnet`, four `researcher` reads before the filings; the pair the round was for, `examples/11` with builders equal to the cores, read `auto` IMPROVED -13.4 % (296.26 s to 256.47 s, the giant's width 2 to 4) where the same command opened at ceiling 1 before |
| [121](round-121.md) | the first day on a real project, eight rows closed - the jobserver FIFO no longer bound onto its own host path under a read-only root, named under `bind_dst` (`UX-869`), the kinds read carrying the user's own global options with a reason and `kinds_read.json` on every failure (`UX-870`), a junctioned name stored under both spellings with `junctions`/`collisions` in the record (`UX-871`), `examples/12-junctioned` under `bga snapshot --jobserver auto` in CI (`UX-872`), the target read past `--deps all` (`UX-873`, filed and closed in the round), plus review 24's three rows (`UX-866` to `UX-868`) - eight `implementer` tracks behind eight `verifier` reads on `sonnet`, two `researcher` reads before the filings; the fifo-auth pair on `examples/11` opened its sandbox clean and this box's GNU Make 4.3 refused the auth string, so the timing waits for a 4.4 host |
| [122](round-122.md) | the jobserver auth style the sandbox make refused - `auto` picked `fifo` from the host's GNU Make 4.4, but a `kind: make` element's own `tar` staged an older make that rejects `fifo:`, so the style must follow the make that consumes it, not the host's (`UX-874`), and `bga snapshot` gains the `--jobserver-auth` passthrough `capture run` already has (`UX-875`) |
| [123](round-123.md) | the jobserver auth autodetect picks the style that always works - `--jobserver auto` resolves to `fd`, which every GNU Make from 4.2 up accepts, rather than `fifo` from the host make (`UX-876`), after a `kind: cmake` element's sandbox-built make below 4.4 rejected `fifo:` that round 122's probe never saw; and the sandbox-make downgrade for an explicit `fifo` now covers every kind that injects `MAKEFLAGS`, not only make/autotools (`UX-877`) |
| [125](round-125.md) | a per-element switch for the jobserver auth style - a mixed-make project (some elements pinned to GNU Make ≤4.2.1, others migrating to 4.4) forces `fd` on a named element so it fills the pool via the fd jobserver, or `off`/`fifo`, overriding the auto/scrub decision UX-878 makes from the make probe; `--jobserver-auth-override 'style:glob'` threaded to the shim, resolved against the element name (`UX-879`) |
| [126](round-126.md) | a compiler-LTO shim fills the box without the gcc-13 ICE - a forced-`fd` element that *does* GCC LTO still crashed lto-wrapper on the invalid fd, so a new `flto` override style keeps `fd` for make (compiles fill the pool) but mounts a reference shim over the GCC driver that strips the auth and passes a static `-flto=N`, only when `-flto` is already present, and is not scrubbed because the shim keeps it safe (`UX-880`); a preflight warns when an LTO element meets a sub-4.4 make and names the make-4.4 remedy (`UX-883`); the `--wrapper-dir` override, the `public: bga.jobserver-auth` surface, the make/autotools LTO gap, and two process rows filed for later (`UX-881`, `UX-882`, `UX-884`, `UX-885`, `UX-886`) |
| [127](round-127.md) | the two operator surfaces for a custom-prefix shim - `bga capture run --wrapper-dir <path>` (augment, or `--replace`) lets an operator ship their own shim matching bga's published contract for a compiler PATH-shadowing cannot reach (`UX-881`), and a `public: { bga: { jobserver-auth: fd\|fifo\|off\|flto } }` element annotation, read via a second `bst show %{public}` and resolved after the command-line override, carries the per-element style in the project instead of the invocation (`UX-882`); advisory input, no contract version bump |
| [128](round-128.md) | the ninja wrapper owns ninja's `-j` - a `kind: cmake`/`meson` recipe of the shape `ninja -j ${JOBS}` (the `-j` literal, `JOBS` a bare count) crashed `invalid -j parameter` under `--jobserver auto`, because bga empties `JOBS` and stranded the flag; the UX-846 ninja wrapper now strips the recipe's own `-jN`/`--jobs=N`/dangling-`-j` before prepending its token-held `-j<width>`, so it is ninja's single source of parallelism whatever shape the recipe writes (`UX-888`) |
| [129](round-129.md) | the four deferred rows cleared - the token-refill guard polls for the reap instead of a fixed 2s window so its refill+naming claim gates and the wall-clock does not (`UX-886`), `make lint` folds into the push gate on CI's pinned versions so a lint-red blob is caught before the push (`UX-885`), the `implementer` brief no longer names the dev-deps command that repoints the shared editable install (`UX-887`), and the jobserver policy's `make`-kind LTO exclusion is settled by measurement (`UX-884`) |
| [130](round-130.md) | the control-growth review: the 12-run store window holds, while the finding fold leaves hidden controls materialised (`UX-921`); snapshot-management placement remains a proposal, not a filed defect |
| [131](round-131.md) | a rising ratio that was a stale record - `UX-908`'s three excursions are one step (26 -> 36 tests on 2026-09-15) and then a band spanning 6%, not a rise, so both records were re-recorded (`tiers.py` 3.1s -> 8.7s, `ci_reference.json` 6.47 -> 13.86); the round's finding is why neither moved on its own, filed as `UX-924` - `adopt` reads the candidate's `files`, already the median of that candidate's own samples, so a full flat window feeds the committed value back to itself and 37 adopt commits never moved a 2.1x-stale entry |
| [134](round-134.md) | the examples stage their own make - the host's `make` was copied verbatim into every sysroot, below `UX-841`'s cutoff, so `style_for_make_version` read `fd` on every host this repository has run on; `UX-915` pins GNU Make 4.4.1 from `cache.nixos.org` (keyed on `platform.machine()`, one relative interpreter symlink, no glibc closure) and `UX-916` stages 4.2.1 beside it behind a `/usr/lib/bga-make/<series>` PATH alias, so one `bst-examples` capture crosses the version switch both ways - written retroactively in round 135 from this round's own records |
| [135](round-135.md) | the sysroot was the host's and nothing said which host - `UX-914`'s four base candidates all need a mirror refused at CONNECT, so the pick dissolves into per-package nix pinning and a declaration: `tools/sysroot_manifest.py` names one row per package over two axes (runtime, toolchain) and probes **every** owned binary, 23 over 21 staged names, because a package-level probe is a proxy for its own members - a pinned divergence exits 1 and a host divergence warns and reddens a guard; the toolchain axis is filed as `UX-925` |
| [136](round-136.md) | three rows in three concurrent threads and a document none of them wrote - `UX-924`'s `adopt` took the candidate's committed median rather than its newest reading, so 367 flat windows fed a value back onto itself; `UX-927` found a pin stages 1 store path of 5 (and would stage 1 of 15 for gcc), so `tools/nix_closure.py` walks the narinfos transitively and gates on `NarHash` because a recompressed `glibc-2.40-224` disagrees on `FileHash`; and `UX-930` measured `-B` as three directories rather than one, with a `-B` at a directory holding no `cc1` compiling against the host at exit 0 and no stderr - written retroactively in round 137 from the three task files and the ledger, and `UX-926` is the row for why none of the three wrote it |
| [137](round-137.md) | a prefix this repository can name - `UX-925` predicted that gcc's compiled-in search paths meant a second `arch=` variant needed a second machine, and the pin falsifies it: the stock nix gcc closure staged at its own `/nix/store/<hash>` is already configured where it stands, so `tools/nix_toolchain.py` pins gcc 14.3.0, binutils 2.44 and cmake 4.1.2 (37 store paths, 420 MiB) and `UX-930`'s parameters read **five** `-B` prefixes off it rather than three - the assembler and the linker are classes only once a pin takes them off `PATH` - with the C++ headers flipped to toolchain-owned (`argv[0]` relocation, no flag) and the closure's own glibc declared as `glibc-pinned` so the runtime rows stay byte-identical |
| [138](round-138.md) | eighteen rows and one closing PR - the review cadence (25 closed rows) stood at 914 against review 25's 889, so review 26 ran first and every row moved in `#277`; `dev_sizes.py --adopt --force` was refused as a CI bypass and two tracks cut `tools/_close_task_checks.py` and `tools/_record_readers.py` instead; six concurrent local suites on four cores read 43 false reds at load about 400, so `UX-948` makes `make push-check` the push gate and CI's matrix the merge gate; the last eight PRs landed as a stacked chain, which found a census guard undeclared (31 -> 32), a guard's inner make inheriting `MAKELEVEL`, and a ceiling 164 -> 167 read green through a pipe without `pipefail`; and this closing PR is the first docs-only lane run (`UX-956`) |
| [139](round-139.md) | the workflow review's first rows - process was 87% of filings and 40 of 47 catch-up conflict paths were registers, so an `architect` shapes rows under a 40% bookkeeping cap (`UX-993`, `UX-994`), derived figures are printed rather than committed (`UX-996`), a pull request runs the newest Python alone (`UX-995`) and CI's records publish to a `records` branch (`UX-997` T1); every track's verifier held once, each on a real defect |
| [140](round-140.md) | the workflow batch in parallel - nine rows under the architect's Decisions: the push gate reads the payload's tree (`UX-992`), a bookkeeping finding is one line (`UX-998`), a weekly `retro` (`UX-999`), the records leave main (`UX-997` T2) and area pages name each row's guard, `covered 366 / 567 (declared 121, inferred 245)`, published by CI (`UX-1000`); seven of nine verifications held, each on a real defect |
| [141](round-141.md) | the jobserver batch on a real project - fdsdk's LTO links hung because gcc's `lto1` deadlocks on a blocking raw fd pair, so every compiler-facing policy hands `fifo:` (`UX-1001`, `UX-1006`); a shared build root hid 12 make sandboxes (`UX-1003`); the CI runner is two SMT cores and its VMs span two CPU generations, so no wall verdict is possible there (`UX-1002`, `UX-1004`) |
| [142](round-142.md) | the styleguide audit's 22 rows and `UX-921` in nine parallel tracks - controls meet 24x24/44x44 (`UX-1022`), find-in-page opens folded chapters through `hidden="until-found"` (`UX-1015`), one `?` door per block, 191 -> 39 (`UX-1021`), spacing, fonts and sizes from tokens (`UX-1026`, `UX-1033`, `UX-1035`), every step past a bound bounded (`UX-1028`-`UX-1032`); the merged tree moved the landed bound 7,300 -> 7,600 px and split `pairs.js` and `schema_hints.py` out at their ceilings; held `UX-1018`, whose guard now reddens |
| [143](round-143.md) | every agent names its model and effort - architect opus high, verifier sonnet high, researcher sonnet low; implementer tracks go to opus when architect-shaped from judgement or over 150 code lines, which were held 53% on sonnet; `integrator`, `walker` and `closer` own the merge, the page and the close (`UX-1039`) |
| [144](round-144.md) | the second styleguide audit's rows, viewer tracks in parallel - one accent guard per grade's sentinel, one resting rule for select and text, the viewer JS ships gzipped, one landed-height bound per size class with the chapter distance kept separate, the rail discloses the current chapter and the first Tab starts at the top, copy-rows/top-n moved in the DOM rather than on screen (`UX-1042`-`UX-1055`, `UX-1045` still open); the walk found three pre-existing gaps (`UX-1056`-`UX-1058`) |
| [145](round-145.md) | the anonymized-bundle rows close - disclosure classes for every exported value path, keyed shape-preserving pseudonyms, a bundle that exports anonymized and refuses a leftover name, analysis commutes with anonymization, pseudonym text resolves back via `bga bundle --resolve`, a declared public junction keeps its public names, the archive and its gzip header carry no original metadata (`UX-1060`-`UX-1065`, `UX-1067`; `UX-1066` still open); verification found the length band, gzip FNAME, a long-flag leak, the epoch-0 start and a split table, and a `plural()` fix landed after |
| [146](round-146.md) | the #298 review rows close - a command-line credential drops to `<dropped>` and never enters the pseudonym map, the anonymized export streams in bounded memory to a 0600 archive, the disclosure policy names what the producer writes (gaps 10 -> 0), the residue scan runs 0.22 -> 4.04 MB/s (`UX-1068`-`UX-1071`); verification found four credential leaks, an F-classed `"None"` key and a non-integer C key |
| [147](round-147.md) | the #298 re-review rows close - a numeric option value pseudonymizes by default, keyed safe on (binary, option); the residue scan is Unicode-aware with NFC folding after casefold; the pseudonym map saves atomically before the archive publishes; the bounded-memory measurement now varies distinct identifiers, about 1.3 KB/identifier (`UX-1084`-`UX-1087`); verification found `gcc -l1234`/`curl -O 12345` leaks and the map-write temp-file/existing-destination defects |
| [148](round-148.md) | the #298 review's third pass closes - an unrecognized numeric value (`--otp`/`--pin`/...) drops to `<dropped>` instead of pseudonymizing into the reversible map, and the glued `-j<digits>` shortcut is keyed to make-like binaries same as the other forms (`UX-1088`, `UX-1089`); a verifier ran and found a further leak, the glued `-j=N` form |
| [149](round-149.md) | a housekeeping round on Ruslan's ask, the 40% bookkeeping cap lifted for it, 11 parallel tracks off the 2026-09-28 retro's proposals and filed guard gaps - a reading's environment now takes it (`UX-938`), the flake census counts a multi-file run once (`UX-950`), a population entry keeps its tree size (`UX-955`), a linked worktree cannot repoint the shared install or the sweep (`UX-1041`), the retro keys a finding by its own class (`UX-1090`), the records writers queue instead of cancelling (`UX-1091`), every scenario declares its guard in one field, 1021 files backfilled (`UX-1092`), the Enter-on-a-reached-fold race (inferred, not reproduced) closed by a bounded Tab walk (`UX-1093`); load average 50-63 from 11 parallel tracks made every gate a 10-25 minute wait, and `merge=union` on the bookkeeping ledger reopened 12 swept lines across two merges |
| [124](round-124.md) | the LTO link survives the jobserver - `fd`-style auth in `MAKEFLAGS` is read directly by an unwrapped `gcc -flto`/`lto-wrapper` whose fd is invalid inside the sandbox, so a `kind: cmake` element's GCC-13 LTO link ICEs; the injected auth for gcc-lto-driving kinds (`cmake`/`meson`/`jobs_env`, cargo) is rewritten `fd → fifo:` (path-based, valid across the boundary for gcc-13 and modern LLVM) or scrubbed when a sub-4.4 make shares the string, at the one channel that reaches an absolute-path custom-prefix compiler (`UX-878`) |
| [150](round-150.md) | bga's own cost, from the snapshot tail through the view - the tail reuses `_analyze`'s slice and one bitset reachability closure (`UX-1072`, `UX-1074`), compare reads each side's published analysis under a full fingerprint (`UX-1073`), the raw log gzips at level 6 and its opened paths are interned (`UX-1075`, `UX-1076`), every phase is announced and timed into `tail.json` (`UX-1077`, `UX-1078`), capture report reads a gzipped log and BuildStream calls are timed (`UX-1079`, `UX-1080`), export renders once and the cache key set reads the build's own log, reusing the graph on an equal fingerprint (`UX-1081`-`UX-1083`); the Verification Log re-grounds at both merge seams and the selector ceiling takes #298's merge (`UX-1101`, `UX-1103`) - fourteen closed, six filed |
| [151](round-151.md) | the quality gates, audited and batched - CI cancels a superseded PR run and stops chaining the bst jobs behind the suite (`UX-1108`-`UX-1111`, `UX-1115`, `UX-1121`), push-check lints changed markdown and runs the locked tools (`UX-1112`, `UX-1113`), a SessionStart hook unshallows and locks (`UX-1114`), the hook builds warning-clean and the Plane 1 reader has property tests (`UX-1116`, `UX-1117`), docstrings follow Google convention and `closed.md` is chunked (`UX-1119`, `UX-1120`), the retro prices its guards (`UX-1122`), the Verification Log re-grounds (`UX-1123`), the tree is formatted (`UX-1118`) and the size ledger reads one order (`UX-1126`), two CodeQL findings fixed (`UX-1127`) - eighteen closed, five filed |
| [152](round-152.md) | the open rows closed - blast radius off the bitset (`UX-1106`), the export, stamp and env fixes (`UX-1107`, `UX-1124`, `UX-1007`, `UX-1057`), raw logs travel tokenized (`UX-1066`), the jobserver verdict table (`UX-1012`, `UX-1008`), a tree of bundles as a store (`UX-900`), `bga junction-cost` (`UX-904`), the guard and doc rows (`UX-975`, `UX-976`, `UX-1125`, `UX-1129`-`UX-1131`, `UX-1133`), the rail toggle and back re-fold (`UX-1058`, `UX-1056`), the Graviton reading (`UX-1010`) - twenty-one closed |
| [153](round-153.md) | the view page on a two-plane capture, reviewed - no "null" in a finding card (`UX-1136`), the `?` door off the first term's cell (`UX-1137`), pinned from the resolved width rather than `make -j1 install` (`UX-1138`), the costliest pins named first (`UX-1139`); the review's 25 findings filed as `UX-1140`-`UX-1153` - four closed |
| [154](round-154.md) | the review's fourteen rows fixed - `UX-1140`-`UX-1153`, seven tracks merged (30 then 7 merged-tree reds to 0), five verifier holds closed by a residue pass; the walk's 14 defect classes filed as `UX-1154`-`UX-1160` |
| [155](round-155.md) | the round-154 walk's seven rows fixed - `UX-1154`-`UX-1160`, seven tracks merged (34 B over the page budget recovered to 255 B under, 6 reds fixed), one verifier hold recorded; the walk's residue filed as `UX-1161`-`UX-1167`, the last asking the owner about the 150,000 B budget |
| [156](round-156.md) | the round-155 walk's seven rows fixed - `UX-1161`-`UX-1167`, seven tracks merged, the page budget raised to 160,000 B on the owner's call, one suite flake traced and fixed as `UX-1168`; the walk's residue filed as `UX-1169`-`UX-1175` |
| [157](round-157.md) | the round-156 walk's seven rows fixed - `UX-1169`-`UX-1175`, seven tracks merged (8 merged-tree reds fixed in a four-commit pass, the page half 151,228 B to 144,196 B), a chapter-row press at 390 keeps the rail open for J2; the walk's residue filed as `UX-1176`-`UX-1181` |
| [158](round-158.md) | the data-exploration review and round 157's residue - `UX-1176`-`UX-1193`, eighteen rows in three waves (a container restart mid-integration, a verifier FAIL on `UX-1179` fixed in a residue pass, 18 of 18 guards red on undo); the review's five tasks now 3 answered, 1 half, 1 wrong; the walk's residue filed as `UX-1194`-`UX-1205` |
| [159](round-159.md) | round 158's walk residue - `UX-1194`-`UX-1205`, twelve rows in two waves (owner: full Blocks lists with bounds raised by the measured delta, `UX-1205` rides bst-tests); 12/12 verified PASS; the review's five tasks all answered; walk N1-N8 fixed in three residue tracks; the residue filed as `UX-1206`-`UX-1217` |
| [160](round-160.md) | round 159's walk residue - `UX-1206`-`UX-1217`, twelve rows in two architect waves (owner: `UX-1214` publishes every direct list, `depends_on:` and `blocks:` exact, the transitive `downstream:` dropped); verifiers 10 PASS and `UX-1208` FAIL (fixed); the review's five tasks all answered; walk N1-N8 fixed in five residue tracks; the residue filed as `UX-1219`-`UX-1232` |
| [161](round-161.md) | round 160's walk residue - `UX-1219`-`UX-1232` in four tracks, with the owner's `UX-1233` (page budget 165,000 B) and `UX-1234` (shared titles); verifiers 15 PASS; the residue filed as `UX-1235`, `UX-1236` |
| [163](round-163.md) | the round-162 review's rows - `UX-1235`, `UX-1236`, `UX-1244`-`UX-1257` in eleven opus and two sonnet tracks (a capacity-bound run reads `capacity_bound`, `analyze/v7`'s per-binary totals, Plane 2 findings, the sizing card, the compare lead); three owner calls pending (`UX-1254` 872 controls, `UX-1249` 13,500 words, `UX-1244` the host-core cap); the residue filed as `UX-1258`-`UX-1267` |
| [165](round-165.md) | the round-163 residue and the round-164 review's rows - `UX-1258`, `UX-1260`-`UX-1277` in six opus tracks (a finding's Why #1 from its own step, `analyze/v7` `findings_diff` and `blocked_unparented`, the capacity page's `counts`, the replayed sweep knee, a comparison page guarded); owner-call defaults taken for the `xl_both`/`macro_micro` budgets, `joint-saving`, `builds_per_day`; the log re-grounded as `UX-1278` |
| [166](round-166.md) | the memory-bound giant and two closes - `UX-902` (the serial-giant case, two Graviton cases), `UX-1279` (a sort button names its next press), `UX-1134` (the no-plan memory gate, autocap completes at 10 jobs); `UX-1280`, `UX-1281` filed |
| [168](round-168.md) | the per-element jobserver switches and a docs gap audit - `UX-1300` (the jobserver guide names all four switches and the four styles); `UX-1301`..`UX-1308` filed from the audit |
| [169](round-169.md) | the bookkeeping sweep - 22 ledger lines resolved under `UX-998` (12 swept in four tracks, 1 promoted as `UX-1314`, 6 dropped as fixed); every browser guard cites a styleguide § or is named in `UNCITED`; the exported page at 166,249 of 166,250 B |

## Verification Log

Written 2026-08-16 from a real session: BuildStream 2.7.0 with
`buildstream-plugins`, real `bwrap` sandboxes, real `gcc 13`/`cmake 3.28`
staged by `examples/stage_cpp_toolchain.sh`, on a 4-core / 16GB Linux
host. Every number quoted is from a real build and a real `bga`
invocation in that session, recorded in
[`case-study-06-macro-micro.md`](case-study-06-macro-micro.md); every
claim about what the code does was checked against the source rather than
inferred from output. The proposed report and CI-comment layouts are
illustrations of intent, not implemented output.
