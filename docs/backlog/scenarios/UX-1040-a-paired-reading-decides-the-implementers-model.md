# UX-1040: a paired reading decides the implementers' model, and where Haiku 5.5 reads

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1039, UX-1351 | **Found by:** round 143 — the workflow review Ruslan accepted 2026-09-27 07:53; widened by the Haiku 5.5 review he accepted 2026-10-10 15:45 | **Serves:** every round's implementer spend | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1039` kept mechanical and bounded tracks on sonnet at `medium`
because opus at `low` breaks even only at half sonnet's tokens or a
matching cut in holds, and neither is measured. Over the 180 ledger rows
with both an implementer and a verifier row (rounds 95-142), rows over
150 lines of code were held 53% and re-run 23%, against 31% and 2% at
20 lines or fewer.

## Required Fix

In the next round with four or more tracks, run four rows twice each, in
separate worktrees from one brief: `implementer` as filed (sonnet,
`medium`) and `implementer` launched with `model: opus` at `effort: low`
(a copy of the file differing only in those two lines). One of the four
is over 150 lines. A blind verifier per arm. Record price-weighted fresh
tokens (opus x2), wall, holds and post-merge reds per arm.

**Widened 2026-10-10 (Haiku 5.5).** Haiku is $0.10/$0.50 per MTok up
to a 100K-token prompt and $0.50/$2.50 above; Sonnet 5.5 reads cache at
$0.10, so on a long track Haiku's reads are only 2x cheaper. A probe the
same day (`claude -p --agent <role>`, one run each) priced a verifier on
a planted vacuous guard at $0.017 on Haiku against $0.164 on Sonnet, both
HOLD for the right reason; a researcher at $0.012 against $0.144, both
four of four. The same round also runs:

- a third implementer arm, `model: haiku` at `effort: medium`, on the
  same four rows;
- a Haiku verifier (`effort: high`) beside every track's sonnet
  verifier, in its own worktree, blind to the other; each hold scored
  real or false;
- the round's `researcher` and `closer` runs on Haiku at `medium`
  (never `low`: its long-prompt early stop).

Every arm is priced by `UX-1351`'s cost cell, launched through the
Agent tool (`claude -p` refuses pytest).

## Out of Scope

The architect, the integrator. Fable as an advisor, unless Ruslan adds
it as an arm on the large row.

## Acceptance Test

The four rows' arms are rows in `docs/audits/agent-runs.md` with a cost
cell, and the Outcome states the rules: opus at `low` is adopted for
implementers when its cost per merged, unheld row is within 10% of
sonnet's; Haiku for rows of 20 code lines or fewer when its cost per
merged, unheld row is below sonnet's and it holds at most one more of
four. The Haiku verifier replaces sonnet if it catches every real hold
sonnet does, stays beside it if it adds one sonnet missed, and is
dropped otherwise. Researcher and closer move to Haiku if no answer or
close has to be redone.

## Outcome
