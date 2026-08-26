# UX-295: `whatif/v1` is published, and named in no guide

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-230 | **Serves:** R5 and R7 — the payload consumers | **Topic:** docs

## Motivation

Found by review 3, checklist item 2 — *does every published contract
have a home?* Measured across the seven published contracts:

```text
contract              named in architecture.md   named in a guide
analyze/v2                     4                        2
blast/v1                       1                        1
compare/v1                     1                        1
correlate/v1                   1                        1
store-aggregate/v1             1                        1
store/v1                       1                        1
whatif/v1                      3                        0
```

`bga whatif` the *command* is documented — `docs/guides/cli.md:667`
and four places in the real-project guide, which is what `UX-246`
fixed. The *contract* is not: a consumer who receives a payload
stamped `"schema": "whatif/v1"` and greps the guides finds the command
that produces it and nothing about the document itself.

The same shape as `UX-242` one level over: the block was computed and
documented nowhere, and here the contract is published and documented
only where a maintainer looks (the spec, the architecture, a
direction).

## Required Fix

1. `whatif/v1` is named in the guide that documents `bga whatif`, with
   what its keys mean — the treatment `store-aggregate/v1` and
   `blast/v1` already have in `docs/guides/cli.md`.
2. The mechanical half is guarded: `test_the_documents_keep_up_with_
   the_contracts.py` already checks that every contract has a home;
   the review found this by counting *guides* rather than documents, so
   the guard's notion of "home" is what needs the widening, if the
   answer is that a guide is where a consumer looks.

## Out of Scope

- What `whatif` computes (`UX-219`, `UX-230`) or its convention
  (`UX-244`).
- Documenting every key of every contract in prose. The schema
  describes itself (`UX-201`); this is about the *entry point* a
  reader has when the schema is not what they are holding.

## Acceptance Test

A reader who greps `docs/guides/` for `whatif/v1` finds the document
that explains it, and a guard fails when a published contract is
absent from the guides.

## Outcome

🟢 **Done.** `whatif/v1` is in `docs/guides/cli.md` twice: in the list
of outputs that declare their own shape, and as a key table beside the
command that produces it — the treatment `blast/v1` and
`store-aggregate/v1` already had.

**The guard's notion of home widened, as the item asked.**
`test_every_printable_contract_has_a_home_in_the_guides` asks the
*reader's* question rather than the maintainer's. Scoped to the
printable contracts: `bga.contracts.unprintable()` names the four
run-directory shapes (`host/v1`, `sources/v1`, `plane2/*`) that no
`--format json` hands to anybody, and requiring a CLI-guide entry for
those would ask the wrong document to explain them. The exemption is
asserted rather than assumed, so emptying `unprintable()` cannot
silently widen the clause into something nobody chose.

**The keys were read from a payload, and the first draft was wrong** —
which is the argument for the rule rather than an aside. It invented
`selection`, `baseline_makespan_us` at the top level, `saving_us` and
a singular `refusal`. The shape is:

```text
selected              the uids, as given
total_duration_us     the run's wall-clock, for scale
convention            the sentence every figure depends on (UX-244)
refusals              [{check, elements, sentence}]
projected             null when refusals is non-empty, else:
  baseline_makespan_us / makespan_after_us
  joint_saving_us      the answer
  sum_of_individual_us published because it can differ
```

Measured on the golden fixture for `base.bst`: 14,000 → 8,000 µs,
joint saving 6,000, sum of individuals 6,000 — equal there because one
element cannot disagree with itself, and the guide says so rather than
letting the example imply the two are always the same.

**Falsification.** Two mutations against the committed tree:

```text
W1  whatif/v1 leaves the guides          1 guard red
W2  unprintable() empties, widening the
    clause unasked                       2 red
```

