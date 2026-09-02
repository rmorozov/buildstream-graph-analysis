# UX-500: the batch gate, measured against the per-item suite

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-426 (the loop that admits it is unmeasured), UX-498 (the batch plan that names the items) | **Serves:** the implementing session's wall clock; the maintainer's subscription | **Topic:** docs

## Motivation

`UX-426` wrote the per-item loop and refused to promote it because
nobody measured it. The cost it did not measure is the gate itself:
fixing guide §3 runs the whole suite before *any* item is marked done,
so a round of eight items runs it eight times.

```text
make test at -n auto, this container, round 74       SUITE_TIME
items closed in rounds 66-73                         77
suite runs implied by §3 for those items             ≥ 77
CI: pull_request only — one run per push, batched    (UX-426)
```

The suite is the right gate for a *batch*: a wrong item is found the
same run either way, and the seven runs in between find only what
`make test-touching` plus the item's own mutations already found — if
that is true. It is a claim, and this repository's rule is that a
process claim is measured before it is a rule.

## Required Fix

Run three rounds under each regime and record, per round, in the round
document: wall clock of gates, number of suite runs, defects the
batch gate caught that `test-touching` missed (the number that decides),
and commits per task. Regime A: §3 as written. Regime B: per item
`test-touching` + falsify + commit; one `make test` per batch of
independent items (`decompose` §3 says which), one PR opened first.

If B's missed-defect count is zero across three rounds, §3 changes to
name the batch as the unit the suite gates and the verify skill's §7
loop loses its "in addition" clause. If not, the number is the reason
§3 stays, written where `UX-426` wrote its refusal.

## Out of Scope

- Making the suite faster — `UX-336` did the parallel half; the
  question here is how often it runs, not how long.
- Any regime that skips `make test` before a *PR* merges — the PR is
  the batch's gate under both regimes.

## Progress

**Round 75 — Regime A, round 1 of 3.** Figures in
[`docs/audits/round-75.md`](../../audits/round-75.md): 7 items, 15
suite runs, ~80 min of gate, 1.0 commits per task, and the number that
decides — **2 of 5** defects the per-item suite caught would not have
been in `test-touching`'s set at all (measured with
`dev_touching.select` over each commit's own diff, not argued).

Regime B has not been run. This round's plan said the batch gate would
be *in addition* until this item decides, and that is what happened, so
labelling it B would have been the mistake this item exists to prevent.

## Acceptance Test

Three rounds' figures pasted under the two regimes; the §3 sentence
changed or the refusal written, with the count that decided it.
