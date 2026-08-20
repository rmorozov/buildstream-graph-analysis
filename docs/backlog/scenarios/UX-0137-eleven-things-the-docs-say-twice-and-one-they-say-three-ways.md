# UX-137: eleven things the docs say twice, and one they say three ways

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-135, UX-136 (land the reorder and the era fixes first, so the dedup doesn't move stale text)

Docs polish round (round 14); the full duplicate-cluster table with
locations is in [`round-14`](../../audits/round-14.md).

## Motivation

A fresh-eyes read of the 3,094-line user-facing corpus found **eleven
duplicate clusters** — content stated in two to four places, each copy
drifting on its own schedule. The three worst:

- the **efficiency-gate comparison table** (+2.5%/+44%/+19%/noise) is
  pasted near-identically in README, cli.md and real-project.md, and
  the marginal gate's −14.6pp/−0.5pp evidence three times besides;
- the **cmake-stage1 correlate block** exists in three copies that have
  *already drifted* (UX-136's stale-output finding is one of them);
- the **noise-band lesson** is taught with two different noise figures
  for the same project (5.8% in README, 2.9% in the walkthrough and
  capture guide) — the same lesson, inconsistent evidence.

Plus: the three-command capture in seven places, spine pricing in four,
plane descriptions in five, doctor described four times, `@last`
grammar in three, the exit-6 refusal in six. Every cluster is a future
UX-97/UX-122-class drift waiting to be found by an audit instead of
prevented.

## Required Fix

For each cluster in the round-14 table: pick the canonical home (the
table proposes one per cluster — reference material → cli.md, worked
output → real-project.md, the plane table → docs/README), reduce every
other copy to at most one sentence plus a link, and where two copies
disagree (the noise figures, the drifted correlate block) resolve to
the one that is measured and current, naming its provenance. cli.md's
front matter loses the dispatch-alias table and "74 occurrences"
history to a footnote in the same pass — archaeology, not reference.

## Out of Scope

- New enforcement (the correlate-output staleness is already caught by
  UX-136's re-generation; a paste-detector test is not worth its
  false positives).
- Terminology (`UX-138`).

## Acceptance Test

Each of the eleven clusters has exactly one full statement in the
corpus (spot-grep per cluster pasted in the log); the two noise
figures become one with provenance; total user-facing line count drops
by ≥400 lines against the round-14 baseline of 3,094 with no evidence
deleted (relocations named); links and docs tests pass.


---

## What was built

Canonical homes, then one sentence plus a link everywhere else.

| cluster | canonical home |
|---|---|
| efficiency-gate comparison table | `cli.md` (reference) |
| the correlate output block | `real-project.md` (worked output), with a small real one in `cli.md` from `examples/06` |
| noise-band lesson | `real-project.md`, single figure (below) |
| exit-6 refusal | `cli.md`'s Exit Codes |
| spine pricing | `architecture.md`, which holds the measurement history |
| plane descriptions | `docs/README`'s plane table |
| the three-command capture | `cli.md`, as what `snapshot` composes |

### The two noise figures are now one

README taught **5.8%** (three captures of the same freedesktop-sdk
commit: 3614.2s, 3434.4s, 3405.8s) and the walkthrough **2.9%** (two of
those three) — the same lesson with two different numbers. Resolved to
5.8% with its provenance stated, because it is the larger sample and
shows more of the real spread; the capture workflow's own doc keeps
2.9% annotated as superseded, per `UX-132`/`UX-144`'s convention.

### Line count

The user-facing set went **3,128 → 2,203 lines**. Of the 925, **884 is
relocation** — `real-project-capture.md` (277) to `design/`, the two
walkthroughs (607) to `audits/`, per `UX-139` — and `cli.md` and
`ci-comment.md` *grew* by 40 and 44 absorbing the canonical copies. The
remainder is duplicate prose removed with its content still reachable
one link away. No evidence was deleted.
