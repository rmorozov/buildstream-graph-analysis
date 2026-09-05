# UX-253: the aggregate mixes contract sets without saying so

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-250 (the two-run case, done) | **Serves:** R7 and R5 — the two who read a distribution rather than a pair | **Topic:** contracts | **Area:** bga

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

## Outcome

**Decided, and the decision is the argument this item asked for.**

`UX-234` refuses to blend across host classes and publishes per-class
figures. A contract set is **not** that kind of thing, and treating it
the same way would have shipped a rule nobody argued:

- A host class partitions runs into populations that must not be
  pooled — durations from a fast machine and a slow one are
  incomparable, so a blended number would mean nothing.
- A moved read-contract makes a run's fields *absent or differently
  defined*. The run cannot be **read**, rather than being read and
  meaning something else. That is an exclusion, not an
  incomparability.

So the many-run rule is `UX-250`'s two-run rule applied to a set, and
the three questions the item posed are answered:

1. **One distribution with a caveat, or two?** One — over the runs
   whose read-contracts agree — plus the composition, published either
   way. A contract set is not a population.
2. **What is the minority?** Whatever disagrees with the **newest**
   state. Not "fewer runs" and not "older": the newest is the one the
   reader is holding, and the sets are published commonest-first so a
   reader can see which is which.
3. **Host-class exclusion, or `MIN_BASELINE_RUNS` refusal?** The
   exclusion's *mechanism* — counted, named, with a reason — and not
   the host class's refusal, because the runs are not incomparable.

**Shipped.** `store-aggregate/v1` carries `contract_composition`:

```text
sets            each distinct contract set found, with its run count,
                commonest first
unstamped_runs  runs whose producer recorded no contracts - every
                artifact predating UX-249, an explicit unknown and
                never read as agreement
reads           the contracts this document itself reads
                ("analyze/v1", "store/v1") - `whatif/v1` moving changes
                nothing about a duration distribution, and a composition
                that did not say which contracts matter would imply it did
mixed           whether more than one set is present
```

The schema declares all four with their sentences, so the viewer can
render them and a reader can look them up (`UX-201`).

**The discriminating case is built rather than assumed**: a store of
nine runs where two carry `analyze/v1` and seven carry `analyze/v2`
reports both sets with counts `[7, 2]` and `mixed: true`. An unstamped
run does **not** count as a second set — counting it would make the
stamp's arrival delete the history it protects.

**Guards on the rule itself**, not just the output: one fails if the
composition ever reads the producer's *version* (which is what `UX-250`
settled against — refusing on the number would fire on every upgrade,
including the thirty rounds that moved no contract), and one fails if
the code stops citing the two precedents it was argued against.

**Not done:** `cache-trend`, which the Required Fix also names, still
reports no composition. It reads a series rather than a distribution
and its rule is the same one, but the field belongs beside its own
verdict rather than copied from here; stated as remaining work rather
than quietly dropped.
