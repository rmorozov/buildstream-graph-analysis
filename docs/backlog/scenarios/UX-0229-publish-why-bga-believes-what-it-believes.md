# UX-229: publish why bga believes what it believes

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-207 (the claims), UX-190 (the contract discipline), UX-215 (the precedent) | **Serves:** R1, R4, R8 — and every secondhand reader

## Motivation

Direction 8's anchor. The pattern round 24 named — *the analysis
knows, and the published schema does not say* — holds one level
above the facts. The headline claims `execution-bound`; the
attribution fields that fired that diagnosis, the threshold they
crossed (`CHAIN_BOUND_RATIO` at `bga/findings.py`), and the canned
query that would prove it deeper are all real and all unpublished as
a chain. Findings assert; their `evidence` dicts are ad-hoc grab
bags no schema describes. The viewer composes fragments of the
missing object (`elementFacts()` walking five sources was the
review's tell before `correlate/v1` absorbed part of it); the CI
comment states verdicts without grounds; and "why do you say this?"
— the question every skeptical teammate asks first — has no
published answer.

Round 27's verification pinned the current seam precisely: the
element-centric picture is a client-side merge — `SOURCES`
(`bga/viewer/views.js:1094-1112`) walks `headline.top_actions`,
`critical_path_detail`, `optimization_horizon`, `latent_heavies`
and `element_join`, plus a findings pass. No arithmetic, pure
selection — and still: if "one element = one published object" is
wanted, that object does not exist in the JSON today; `SOURCES` is
where it is assembled. The claim-level chain this task publishes is
the same repair one level up.

## Required Fix

Each claim — the diagnosis, each finding, each top action — carries
a provenance record in the published payload: the evidence as
**references into the same document** (field paths plus the values
read), the rule that fired (name and threshold), and the trace query
id (`questions.js` id) that deepens it. Schema-described, versioned
under the UX-190 rules. The text renderer prints the chain on
demand; the viewer renders it (UX-227/228 re-plumb onto it) and
retires its own composition; the CI comment cites it.

## Out of Scope

- New analysis: provenance records *existing* derivations; it does
  not add any.
- A causal-graph drawing (the object first; any drawing faces the
  standing graph bar separately).
- Workspace/IDE presentation (declined in Direction 8).

## Acceptance Test

Round-trip: every claim's evidence references resolve within the
same payload (a dangling path reddens the schema guard); the values
quoted equal the fields they cite on the golden run and the
1,202-element synthetic. The diagnosis's record names the ratio and
threshold that fired (mutation: change the threshold constant → the
published record changes with it, asserted). The viewer renders a
claim's chain with zero new derivation (no-arithmetic guard
extended); the text renderer prints the same chain from the same
object.
