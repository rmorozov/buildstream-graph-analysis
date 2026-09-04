# UX-636: eighty published keys no document names

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-628 (which measured this and froze it) | **Found by:** round 86, closing UX-628 | **Serves:** anyone reading a payload against the prose that describes it | **Topic:** docs

## Motivation

`UX-628` named the five keys review 15 found and, in doing so, measured
the whole surface for the first time:

```text
consumer surface, printable contracts   199 keys
named in no document outside docs/backlog and docs/audits
  by code-span match                     84  ->  80 after UX-628
  by bare substring                      61
sweep/v1 and whatif/v1                   already complete
```

`UX-628` did not close that. It could not: a clause asserting full
coverage would have been red on arrival by eighty keys, and a guard
that is red on arrival gets silenced rather than satisfied. What it
shipped instead is a **ratchet** — the eighty are a frozen register
that may only shrink and cannot be padded, and a key added after the
row reddens by name.

So the debt is bounded and cannot grow. It is still eighty keys a
reader cannot look up, and the register is the list of them.

## Required Fix

The register empties, contract by contract, and each emptying deletes
its own entries. Order by what a reader reaches for: `analyze/v5` and
`compare/v2` first (`docs/guides/cli.md`'s contract section), the rest
in `docs/design/architecture.md`'s inventory.

Two constraints a track will hit and should be told about rather than
discover:

- `docs/design/architecture.md`'s inventory chapter is at **71 lines
  against a 72-line budget** (`3 × 24`), so prose for a contract goes
  in the guide, not there.
- `run-context/v9` has no JSON Schema in this tool — it is an input
  contract — so `requested_at_us` and `requested_at_source` are outside
  any schema-derived population and reach the register only by hand.

The register is the acceptance criterion: it shrinks to zero, and the
clause that reads it stops being a ratchet and becomes a statement.

## Out of Scope

- Widening the population beyond the printable contracts — declined:
  `UX-628` measured its boundary and stated it, and moving the boundary
  is a different claim from paying the debt inside it.
- The prose *style* of a key's description — the guide's existing rows
  are the pattern; matching them is enough.

## Acceptance Test

The register at zero, and `test_the_documents_keep_up_with_the_contracts.py`
still reddening by name when a key is added to a live schema.
