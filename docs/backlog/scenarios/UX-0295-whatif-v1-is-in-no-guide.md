# UX-295: `whatif/v1` is published, and named in no guide

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-230 | **Serves:** R5 and R7 — the payload consumers | **Topic:** docs

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
