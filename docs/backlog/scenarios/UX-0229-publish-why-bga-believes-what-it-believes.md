# UX-229: publish why bga believes what it believes

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-207 (the claims), UX-190 (the contract discipline), UX-215 (the precedent) | **Serves:** R1, R4, R8 — and every secondhand reader | **Topic:** contracts

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

## Outcome (round 28)

The chain is a published object, `bga/provenance.py`, attached to every
claim in `analyze/v1`:

```text
claim -> evidence (field refs) -> rule -> trace query
```

On the golden run 8 claims carry one and on the 1,202-element synthetic
10 do, with **no dangling reference on either**. Every quoted value is
re-resolved against the document and compared, which is the half a
resolve-only check cannot see: a record built against one document and
shipped inside another still resolves and still quotes the wrong number.

```text
bga analyze tests/fixtures/golden/mixed_task_kinds --explain

  This build is scheduler-bound, not chain-bound: the critical path is
  88% of wall-clock, so the time is going somewhere other than the chain.
    why: The critical path is 87.5% of wall-clock, which is < the 90% at
         which the chain rather than the scheduler is called the
         constraint - so scheduler_bound.
    rule: CHAIN_BOUND_RATIO = 0.9 (<, bga/findings.py)
      floors.t_infinity_observed = 14000
      total_duration_us = 16000
      headline.chain_ratio = 0.875
    deeper: trace query `element-time`
```

Four consumers, one object: `--explain` prints it, the page draws it
folded under each claim, `compare/v1` carries the candidate run's chain
at `candidate_diagnosis` and the CI comment cites it, and the JSON
publishes it under a declared schema.

### What the item was really about, found while doing it

**A rule whose threshold has no name cannot be published as one.** The
mesh-graph finding gated on a bare `>= 0.5` written into the `if`. It is
`MESH_ZERO_SLACK_SHARE` now — the item's premise ("the thresholds are
real and unpublished") turned out to be optimistic about one of them.

**The finding → trace-query table lived in the viewer.**
`bga/viewer/trace_context.js` held `FINDING_QUERIES`, which made the page
the only surface that knew which question deepens which finding: the
terminal could not print it and the CI comment could not cite it. It is
`provenance.TRACE_QUERIES` now and the page reads the published field —
the same move `UX-207` made for the diagnosis. The coverage guard is now
the useful one: it reads the pipeline's table against the library the
page ships, asserting across the boundary the mapping crossed rather
than inside the one file that held both halves.

**Two claims are drawn from fields this document does not carry.**
`capacity_recommendation` and `memory_envelope` are computed, are what
their findings assert, and reach no consumer. They are named in
`unpublished_inputs` rather than referenced or omitted: a reference that
resolved to nothing would read as a published field, and silence would
read as no gap. That is a filing waiting to happen, stated in the
payload instead of in a comment.

**My first draft copied where the code it was documenting referenced.**
`_top_actions` is references-not-copies by construction — its docstring
says so — and the first provenance draft copied the whole record into
each action, restating one chain four times in a document whose subject
is not restating things. A top action's record is now
`see: findings[id=…].provenance`, a path in the module's own grammar,
and the pointer is checked to resolve. It also took the payload from
18,455 B back to 17,288 B, which is how the export stayed under its
backstop without the backstop moving.

### Two budgets, measured rather than raised

```text
analyze payload (golden)      13,722 ->  17,288 B   (+3,566)
analyze payload (1,202 el.)  619,717 -> 624,500 B   (+4,783, +0.77%)
golden export                195,190 -> 198,756 B   (+3,566, +1.83%)
                             backstop 200,000, margin 1,244 B
```

The **CI comment's 40-line budget** did move, and the guard it moved to
is a better one. The budget exists because *a comment that needs
scrolling gets collapsed* — and a `<details>` is one line until a
reviewer opens it, which is the opposite of scroll. The guard now counts
what the sidebar shows (everything outside a fold, plus one line for the
fold) and keeps a looser cap on the raw total, so folded material cannot
grow without bound either.

**Two mutations did not discriminate and were not counted.** Quoting an
unresolved value as `0` changed nothing, because nothing is unresolved
on either run; it was redone as a resolved value quoted off by one.
Printing `` `0.9` `` as a literal in the CI comment passed every
assertion, because 0.9 is what the constant holds today — the guard was
too weak, and the repair is a test that moves `CHAIN_BOUND_RATIO` to
0.42 and asserts the comment moves with it. That is the same test the
analyze side already had, and its absence on the CI side was found only
by trying to falsify.

**Mutations verified red and reverted (10):** the diagnosis threshold
copied as a literal; one evidence path misspelled; a resolved value
quoted off by one; a finding's table entry deleted; the page wording its
own sentence instead of drawing `rule.sentence`; the terminal wording
its own chain instead of calling `provenance.render`; a top action
copying the record instead of pointing at it; the CI comment printing a
literal threshold (against the moved-constant guard); the page guessing
`element-time` for a payload that carries no query; and the path grammar
reading `[key=value]` as an index.

**Deviation from the Required Fix:** none, with one clause interpreted
narrowly and said out loud. "The CI comment cites it" is the *candidate
run's diagnosis chain*, not a chain behind the regression verdict —
`compare/v1`'s own claims have no provenance records, which Direction 8
lists as later work ("the explain-path for compare"). The viewer retires
its query table here; retiring its `SOURCES` element composition is
`UX-227`/`UX-228`'s clause, which this object now exists for.

Full suite: `3033 passed, 3 skipped in 311.32s`.
