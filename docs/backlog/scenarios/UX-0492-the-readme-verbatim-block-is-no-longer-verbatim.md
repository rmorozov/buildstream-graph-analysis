# UX-492: the README's "verbatim" real-project block prints a sentence the tool can no longer produce

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** `UX-475` changed the sentence | **Found by:** architecture review 10 | **Serves:** the outside reader whose first sight of `bga` is a block that says "verbatim" and is not | **Topic:** docs

## Motivation

`README.md`'s **On a real project** section introduces its block as

> Below is `bga analyze` on a real 3614-second `freedesktop-sdk` build
> (4-core runner, `--builders 4 --max-jobs 4`), **verbatim**

and the block contains, at `README.md:170`:

```text
    Note: 77% of elements have zero slack - this graph is a mesh of near-equal chains, so
    savings on one element are often capped by the next chain rather than by its own duration
```

`UX-475` closed this round and changed that sentence. Today
`bga/findings.py` can emit exactly two things in that slot, and neither
is the line above:

```python
f"Note: {density:.0%} of elements have zero slack, "
f"{off_path} of them off the critical path - this graph is "
"a mesh of near-equal chains, so savings on one element are "
"often capped by the next chain rather than by its own duration"
```

```python
f"Note: {density:.0%} of elements have zero slack, all on "
"the critical path - no second chain of equal length, so a "
"saving on any of them is worth its own duration"
```

`UX-326` made the tool's printed sentences contracts. This is one of
them, quoted in the front door as evidence, and it is stale — the
`UX-132` defect in the file an outside reader meets first. `UX-331` is
the precedent: the README excerpt drifting from what the tool prints.

Two things make it worse than an ordinary stale quote:

- The block says **verbatim**, which is a claim about provenance, not
  a hedge. A reader who diffs it against their own run finds the tool
  wrong rather than the document.
- The build it came from is a real 3614-second `freedesktop-sdk` run
  that no guard can re-run, which is why nothing caught it and why the
  fix has to decide what a stale-but-unreproducible sample is for.

## Required Fix

- The block prints what today's code prints, or the section says
  plainly which release produced it and stops claiming to be current.
- Whichever is chosen, the *rest* of the block is checked against the
  same standard in the same pass — this review checked one sentence,
  not fifty lines.
- If the answer is "re-run it", the run has to be a real one; a
  synthesized stand-in relabelled as freedesktop-sdk would be worse
  than the stale line.

## Out of Scope

- `docs/backlog/scenarios/UX-0075-*.md` and `UX-0076-*.md`, which
  quote the same old sentence inside closed Outcome sections. Those
  are history and are correct as history — fixing guide §3.6 is about
  a *figure a document presents as current*, and an Outcome does not.
- `docs/audits/planted-defect-walk-round-72.md`, which quotes the line
  as the defect it was reporting — also history, and `UX-475` is the
  row that acted on it.
- Whether `mesh-graph` or `chain-graph` is the right verdict for that
  build: `UX-475` settled the rule, and this row is about the document.

## Acceptance Test

```bash
grep -n "zero slack" README.md
```

showing a line that today's `bga/findings.py` can produce, with the
command and run that produced it named; or a README that no longer
claims the block is current output.

## Outcome

_Not started._
