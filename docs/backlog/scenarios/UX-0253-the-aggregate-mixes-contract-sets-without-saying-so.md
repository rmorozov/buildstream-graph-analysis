# UX-253: the aggregate mixes contract sets without saying so

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-250 (the two-run case, done) | **Serves:** R7 and R5 — the two who read a distribution rather than a pair | **Topic:** contracts

## Motivation

`UX-250` gave the two-run case its answer: `bga compare` refuses when a
contract the comparison reads moved between the two producers. Its
clause 2 asked for the many-run case as well —
`bga snapshot --aggregate` and `bga cache-trend` — and that half was
**not implemented**, deliberately rather than by omission.

The two-run rule does not generalise. With two runs there is a
baseline and a candidate, so "these disagree" has an obvious shape.
With thirty runs there can be three contract sets, and the questions
that follow have no default answer:

- is a distribution over two definitions one distribution with a
  caveat, or two?
- if the minority is excluded, what is the minority — fewer runs, or
  the older contract set?
- `store-aggregate/v1` already excludes a host class and says so
  (`UX-234`). Is a contract set the same kind of exclusion, or is it
  more like the `MIN_BASELINE_RUNS` refusal?

Guessing would ship a rule nobody argued, in the command whose whole
job is to say what a body of history means.

## Required Fix

1. A decision, argued: what an aggregate does when its runs carry more
   than one contract set. `UX-234`'s host-class exclusion and its
   `--blend` opt-in are the precedent to argue for or against.
2. `store-aggregate/v1` reports the contract sets present, whichever
   way the decision goes — a reader cannot evaluate an aggregate whose
   composition is invisible.
3. The same for `cache-trend`, which reads a series.

## Out of Scope

- Re-deciding the two-run rule. `UX-250` settled it and it is guarded.
- Migration between contract versions. Still its own decision with its
  own evidence, as `UX-250` said.

## Acceptance Test

An aggregate over runs carrying two contract sets says so in its
payload and in its text, and the rule it applies is the one the
argument settled on — with the discriminating case (a minority set that
would change the median) built rather than assumed.
