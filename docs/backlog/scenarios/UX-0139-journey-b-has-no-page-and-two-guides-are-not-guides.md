# UX-139: journey B has no page, and two "guides" are not guides

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-136 (ci-comment's YAML must teach the current flow before it becomes the landing page)

Docs polish round (round 14); full navigation assessment in
[`round-14`](../../audits/round-14.md).

## Motivation

Journey A (local optimizer) has one obvious page — `real-project.md`,
answer-first — and both entry points send readers there. Journey B (the
CI owner) has **none**: gates live in cli.md across three sections, the
comment rendering in ci-comment.md, baseline-set mechanics split
between the capture guide and cli.md, and README carries its own
summary. A CI owner assembles their journey from four documents.

Meanwhile two files listed under "guides — the documents that tell you
what to type" are not that: `optimization-walkthrough.md` is a
happy-path transcript on a `sleep N` proxy from the wrap/extract era
whose lessons real-project.md now teaches with real output (its unique
residual value is bug provenance that belongs with the scenarios that
cite it), and `optimization-walkthrough-06.md` is — by its own framing
— *evidence*, a documented failure case with a "what has closed since"
ledger. Neither mentions `snapshot`, `doctor` or `@last`, and neither
should be modernized: one should retire, the other be filed as what it
is. `real-project-capture.md` is similarly mislabeled: a design/ops
record of this repo's own capture workflow, listed as a usage guide;
a journey-B reader needs only its ref scheme and `bga baseline` section.
And docs/README's guides table lists the reference (cli.md) above the
walkthrough.

## Required Fix

1. **Make ci-comment.md the journey-B page**: absorb a short
   gates-plus-baseline-set sequence (one screen: capture in CI →
   `bga baseline --candidate` → gate flags → post the comment), and
   point README's CI section and docs/README at it first.
2. **Retire `optimization-walkthrough.md`** to a stub pointing at
   real-project.md, moving its bug-provenance notes into the UX
   scenarios that already reference them; **reclassify
   `optimization-walkthrough-06.md`** as a case study (kept verbatim,
   linked from audits/design, no longer listed as a typing guide).
3. **Split `real-project-capture.md`**: ref scheme + baseline usage
   stay in guides; the egress-failure transcripts and workflow history
   move to design/ or audits (they are the workflow's own round-6/7
   story).
4. docs/README's guides table: walkthrough first, reference second,
   journey-B page third; the two case studies under their own heading.

## Out of Scope

- Content rewrites inside the moved material (relocation, not
  revision).

## Acceptance Test

A CI owner's path is one page: ci-comment.md covers capture → baseline
→ gates → comment with current commands, and both entry points point
CI readers there. `docs/guides/` lists only documents that tell a
reader what to type today; the link test passes across every move; the
two case studies remain reachable and byte-preserved.
