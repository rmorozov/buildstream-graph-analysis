# UX-500: the batch gate, measured against the per-item suite

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-426 (the loop that admits it is unmeasured), UX-498 (the batch plan that names the items) | **Serves:** the implementing session's wall clock; the maintainer's subscription | **Topic:** docs

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

**Round 80 — Regime B, and the decision.** Figures in [`docs/audits/round-80.md`](../../audits/round-80.md): 24 items, 6 suite runs, ~63 min of gate, 1.83 commits per task, and **4 of 9** — non-zero, so the condition this item set can no longer be met and §3 stays. Written into fixing guide §3 item 4.

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The two regimes, measured

| | round 75 (A) | round 80 (B) |
|---|---|---|
| items closed | 7 | 24 |
| suite runs | 15 | 6 |
| gate wall clock | ~80 min | ~63 min |
| commits per task | 1.0 | 1.83 (44 / 24; 1.46 less 9 merges) |
| defects the batch gate caught | 5 | 9 |
| **outside `test-touching`'s set** | **2 of 5** | **4 of 9** |

Regime A over 24 items implies ≥24 suite runs — ~3.5 h at this round's
527 s — against B's six. That is the saving the item was weighing, and
it is real; it is not what decides.

### The decision, and why one more round would not change it

The item's rule is *"if B's missed-defect count is zero across three
rounds, §3 changes"*. B's count is **4 of 9** on its first round, so
the antecedent is already false and a second and third Regime B round
cannot make it true. §3 stays, and the number is written where the
sentence is — fixing guide §3 item 4, with both rounds' figures and
the link to [`round-80.md`](../../audits/round-80.md).

Measured with `dev_touching.select` over each responsible commit's own
diff (pasted in the audit), not argued.

### What the four misses have in common

Three of the four are guards that read a **consequence** of the change
rather than the code it touched: `bundle-manifest/v1` joining
`producer.contracts` and so every committed fixture (`test_golden`,
`test_the_contract_inventory_is_derived`); `UX-536`'s reworded
empty-section sentence, which another file greps for a phrase of
(`test_the_journey_has_an_answer_key`); and `UX-528` making its own
file slower (`test_the_tiers_are_a_partition`). The selector maps a
diff to the guards that *name* what it touched. No grep over a diff
reaches any of these — this is what `make test-touching` **is**, not a
defect in it, and it is the reason the suite is still the gate.

### What Regime B produced that A cannot

Three cross-track collisions, each green inside its own worktree and
red only at the merge: two independent row selectors in `tables.js`,
`UX-523`'s settle condition keyed on the wrong page, and two tracks
half-updating one contract count in `docs/README.md`. Not an argument
for A — A runs no parallel tracks — but the reason the batch gate is
mandatory under B, which §3 already says.

### Deviation from the Required Fix

**Yes, and stated.** The Required Fix asks for three rounds under each
regime. Two were run — A once, B once — and the item closes on one B
round because its own decision rule is decided by it: the rule is a
conjunction over three rounds, and one non-zero count falsifies it.
Running two more rounds of B to confirm a decision already made would
be the unmeasured-process cost this item exists to refuse.

### Verification

```text
make lint                                    clean
test_docs_links_and_commands.py              39 passed in 13.14s
```
