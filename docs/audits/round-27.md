# Audit round 27: the map is bigger than the page

Run on 2026-08-23, same retained environment as rounds 10-26. Three
inputs this time: the sibling's eighteen-commit landing (the
round-23 slate UX-207..214, then its own rounds 24-26 landing
UX-215..226), a fourth external review of the viewer, and — the
round's real subject — the user's positioning statement: bga as the
fact-based entry point for build-efficiency analysis **for a team
whose interests partly contradict each other**.

## The landing, verified

The review agent ran twenty-two mutations across all twenty
landings from a set-aside tree with **no `.bga` captures anywhere**
— the fresh-clone shape UX-213 was filed about. Twenty reddened
their guards, including the ones this audit cared most about:
uniform widths and flattened depth now fail on **committed**
fixtures (UX-213's fix is real — captures are in git, a meta-guard
asserts the guarded matrix entry is tracked); the store emitting
`within_band` fails three guards (one verdict chain now, and the
disputed region colours as compare answers); stripped track scoping
fails both SQL guards; a headline-free payload renders no panel;
summed savings have no green path through the what-if drawing; a
disappeared element scored as an improvement fails four guards.
Suite: **2,908 passed, 0 failed**, lint clean, all twenty
backlog rows agreeing with their markers. The page-size ceiling
was replaced in round 26 by instruments rather than raised again —
composition, the data-to-page ratio (7.1× measured at 1,000
elements), and a loose 200,000 B backstop, each raise argued in the
guard's own docstring; the page stands at 123,785 B.

The two mutations that stayed green are the round's guard findings,
filed as **UX-235**: the decision panel's "DOM order asserted"
guard is a tautology (it hardcodes the expected order over three
separately invoked renderers, so `prepend` mutated to `append`
stays green — and UX-221's "culprits above the band" has the same
unguarded-page-order shape), and the anchor-equality probe set
contains no underscore, so a re-duplicated `cssId` differing only
on `_` survives while `my_lib.bst` misses its target. A third seam
rides along: the jsonschema-guarded test files module-skip on a
plain editable install, so "runs on a fresh clone" quietly means
"plus dev extras".

Two answers the next design depended on were pinned. The
element-centric picture is still a **client-side merge**:
`SOURCES` (`views.js:1094`) assembles five published arrays plus a
findings pass — selection without arithmetic, but the "one element,
one published object" contract does not exist, which is `UX-229`'s
motivation verified. And the what-if drawing does no projection
arithmetic — every bar reads the published
`makespan_after_us`/`cumulative_saving_us` sequence — which is what
makes `UX-230`'s constrained selection honest to build.

## The role model, written

The positioning statement became
[`design/roles.md`](../design/roles.md), and writing it produced the
round's central finding, which no feature-level audit could have:
**twenty-six rounds served four roles thoroughly and four almost not
at all — invisibly.** The local optimizer, the recipe author, the
graph owner and the CI gatekeeper (R1-R4) have the entire macro→micro
cycle, the element object, the source axis and the gate grammar. The
capacity operator, the CI user, the release manager and the
engineering lead (R5-R8) have at most a trend line — and R5 and R6
carry the tool's sharpest unmodelled contradiction: the CI owner
wants machines full, the CI user wants queues empty, and these are
one curve read from opposite ends. The house already knows the answer
shape: the noise band made the gate-strictness trade-off a number
instead of an argument, and Direction 9 commits to doing the same for
throughput-versus-latency — measured build profiles as service-time
distributions, a queueing model with printed assumptions, both
readouts published. Explicit non-goals recorded: not monitoring, not
a scheduler, not Perfetto-for-fleets.

The model comes with tracing rules (directions and new filings name
the roles they serve; the guides name theirs; `roles.md` changes in
the same commit as the coverage it describes), filed as `UX-231`.

## The fourth review, challenged and synthesized

Its verdict — *the presentation-layer Pareto is exhausted; the next
gains need new analytical objects* — was checked and split:

- **Accepted where it looked.** For R1's journey the exhaustion is
  real, and this audit's own trajectory agrees (round 23 was already
  compression, not features).
- **Challenged as a map error.** The review reached the end of one
  role's journey and mistook it for the end of the tool. Every
  enabler it proposes — causal graph, workspace, IDE — deepens the
  same single reader's session. The role model says the larger gap
  is *width*: entire roles with no answers at all. Both are real;
  only one was visible from inside the page.
- **Its strongest idea, adopted as Direction 8.** The
  claim→evidence→query chain is the house pattern one level up: the
  analysis knows why it believes the diagnosis, and no published
  contract says so. `UX-229` publishes the provenance object; the
  page, the text renderer and the CI comment consume one chain. The
  review's own observation that `elementFacts()` was reconstructing
  a semantic model in JavaScript was the correct tell, and
  `correlate/v1` (round 25) answered only the factual half of it.
- **Declined, with recorded reasons:** the workspace and the
  build-performance IDE — round 24's export-survivability argument
  against the drawer applies to panes wholesale, and the positioning
  says entry point, not destination. The causal-graph *drawing*
  waits behind the same bar every graph here has faced; the causal
  *object* is Direction 8 itself.
- **Adopted small:** `UX-227` (why is this ranked first) and
  `UX-228` (focus as investigation) — its two cheap items, both
  constrained to published fields. `UX-230` takes the what-if
  checkboxes minus the client-side simulator the review itself
  warned against: subsets are answered by the pipeline (blast's
  transport pattern), never by page arithmetic.

## The repository itself

The user's third strand, filed as three tasks with the measurements
that motivate them: the backlog at 226 rows in an ~890-line README
with closed history interleaved and out-of-scope ideas already lost
once (`UX-232`: split by liveness, one-line rows, topic taxonomy,
out-of-scope mining rule, guards moved with the split — no
renumbering, ever); `architecture.md` predating the entire viewer
axis and contract wave, which is precisely how the next big refactor
gets expensive (`UX-233`: two chapters, a published-contract
inventory, and a drift guard that is red the day it is written); and
the traceability rules above (`UX-231`). One drift was fixed inline
rather than filed: `directions.md` had grown two sections titled
"Round 25: publish the relationship, then navigate it" and a Round
26 section stranded below the round-history table — retitled and
moved, since a document about direction should not itself need an
audit to navigate.

## Standing

The verdict on the landing is the strongest any round has returned:
twenty for twenty, two hollow guards, no over-claims beyond
generous mutation counts in three logs. What changes standing is
the map. The role model makes the next moves legible in a way
twenty-six feature rounds could not: Direction 8 deepens trust for
the roles already served (UX-229 first — the contract, then
UX-227/228/230 consuming it), Direction 9 opens the half of the
table that has nothing (UX-234 first — the aggregate fact-base,
then the queue seam and the capacity model in argued order), and
the repository work (UX-231/232/233, UX-235) is what keeps a
235-item backlog and a two-axis roadmap navigable at all. Priority
for the sibling: **UX-235 and UX-231/232** (guards honest, backlog
navigable — cheap and enabling), then **UX-229**, then **UX-234**,
with UX-227/228/230 following UX-229's contract and UX-233's drift
guard landing with whichever contract change comes first. The
fourth review asked "what's the next game changer inside the page";
the round's answer is that the next one is not inside the page.
