# UX-1040: a paired reading decides the implementers' model, and where Haiku 5.5 reads

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1039, UX-1351 | **Found by:** round 143 — the workflow review Ruslan accepted 2026-09-27 07:53; widened by the Haiku 5.5 review he accepted 2026-10-10 15:45 | **Serves:** every round's implementer spend | **Topic:** guards | **Area:** unassigned | **Shape:** judgement | **Reading:** container

**Guard:** none — a reading of the run ledger, not code

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

Round 173, 2026-10-10. Four rows, three implementer arms each from one
brief, a blind sonnet and a blind Haiku verifier per arm. Costs are
`UX-1351`'s cell, `grep '^| 173 |' docs/audits/agent-runs.md`:

```text
row      code lines   sonnet   opus-low   haiku    every arm
UX-1309  53           $0.26    $0.47      $0.03    held (the --max-store budget)
UX-1353  43           $0.11    $0.37      $0.02    held (REPORTERS unpinned)
UX-1342  12           $0.59    $0.86      $0.13    held (the first step's cause)
UX-1349  ~220 tests/  $1.80    $6.09      $2.42    held (cleanup, sites)
total                 $2.76    $7.79      $2.60
dev_process_bands.py --runs 53: implementer haiku 204k median $0.08,
  opus 101k $0.67, sonnet 64k $0.23; verifier haiku 196k $0.07, sonnet 63k $0.18
```

No arm merged a row unheld: every hold was in the Decision the arms shared,
so "cost per merged, unheld row" is undefined for all three and the rules
are read on cost at equal holds (four of four each).

- **Opus at `low`: not adopted.** $7.79 against $2.76, +182%; +77%
  without `UX-1349`. The 10% rule fails on every row.
- **Haiku implementer: adopted for rows of 20 code lines or fewer.** One
  row qualifies (`UX-1342`, 12 lines): $0.13 against $0.59, holds equal.
  At 43-53 lines it was 8-13x cheaper again at equal holds; at ~220 it cost
  more than sonnet ($2.42, 2979k tokens, 165 min). The cap stays at 20 until
  a second row reads.
- **Haiku verifier: stays beside sonnet.** Haiku held on real defects sonnet
  passed: the `--max-store` budget on 3 of 3 arms (sonnet 0 of 3), the
  frontmatter proxy and inverted rule on `UX-1353`, the first step's false
  cause twice and the off-path cause on `UX-1342`, `name=` dropped on
  `UX-1349`. Sonnet's one real hold Haiku did not reproduce: the xdist cache
  leak (Haiku called the cleanup unguarded). False holds: Haiku 3, sonnet 1.
  14 Haiku runs $1.43 against 11 sonnet $2.54; Haiku is slower (median
  28.9 m) and crosses its 100K card on most runs.
- **Neither verifier caught the two post-merge reds** — `UX-1342`'s element
  named twice (`test_findings_say_each_thing_once[macro_micro]`) and a nested
  pytest deleting `UX-1349`'s cache; the integrator's full suite did.
- **Closer: moves to Haiku at `medium`.** One run, 53 ledger rows, three row
  moves, the round document; no close redone. It asked back once, on a range
  in its brief that was wrong — the right call. No `researcher` question arose,
  so the researcher has no reading and stays on sonnet.

Mutation table: none - a ledger reading changes no code; the four rows'
own mutation tables are in their Outcomes.

Deviation: the merged-unheld measure cannot separate arms when the Decision
holds; scored on cost at equal holds instead.
