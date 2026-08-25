# UX-306: the visual contract joins the tree it governs

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** styleguide (the document), UX-231 (the traceability pattern) | **Serves:** the maintainers | **Topic:** docs

## Motivation

A style guide nobody is routed to governs nothing. The document
exists (`docs/design/styleguide.md`, round 41); this task wires it
in: the docs index, the contributing path, and the schema
documentation that the new hints (`bga:series`,
`bga:distribution`) must join so the contract stays in the schemas
rather than in prose.

## Required Fix

`docs/README.md`'s design table rows it (done in round 41's
commit — verify, and keep); the fixing guide's checklist gains
"touches the page? conform to styleguide §1/§4, or amend the guide
in the same commit"; the style-guide-for-docs
(`contributing/style-guide.md`) cross-references it so the two
guides name each other's scope; the hint vocabulary section of the
schema docs documents the two new hints when `UX-303` lands them.

## Out of Scope

- Enforcement guards (they live with `UX-302`/`UX-304`/`UX-305`,
  beside the mechanisms they hold).

## Acceptance Test

The fixing-guide checklist line exists; both style guides
cross-reference each other; every `bga:` hint the schemas emit is
documented in exactly one place (grep-guard: emitted set ==
documented set — reddens today if UX-303's hints land
undocumented).

## Outcome

🟢 **Done.** The contract is routed to from three places, and its
vocabulary is written down once and guarded in both directions.

**§1a, the hint vocabulary.** Eleven `bga:` hints, each with what a
schema declares by it and which control reads it. Before this the
architecture named five and trailed off in an ellipsis, so the meaning
of the other six lived only in `bga/schemas.py` — and the hints are
precisely the seam an external consumer reads (Direction 7's whole
argument for not blessing a frontend stack is that a tool reading JSON
Schema gets everything `bga view` gets, which is only true if the
vocabulary is legible).

```text
bga:columns  bga:direction  bga:distribution  bga:markers
bga:presets  bga:quantity   bga:question      bga:rail
bga:role     bga:series     bga:severity
```

**The guard holds the two sets equal both ways.** An undocumented hint
reddens; so does a documented hint nothing emits, because a table
naming a hint that does not exist is worse than no table. And each row
must fill all three cells — a row with an empty cell is a hint
*listed* rather than documented. The repository has been bitten twice
by a vocabulary kept in two places (`UX-214`'s verdict kinds re-listed
in JavaScript, `UX-273`'s threshold living in a task file), which is
why this is guarded rather than reviewed.

**The two guides name each other.** `contributing/style-guide.md`
governs the documents; `design/styleguide.md` governs the page.
Neither decides the other's medium, and each says so in its opening —
which is what stops a contributor reading the wrong one and concluding
the rules do not apply.

**Verified rather than assumed:** the docs-index row (round 41's
commit) and the fixing-guide checklist (landed with `UX-305`) both
exist and both are asserted here. The index clause matches the **link
target**, not the display text — a mutation that repointed the link
while leaving the words passed the first draft, which is the same
class of defect as `UX-281`'s dead ends.

**The falsification round**, six mutations, all discriminating:

```text
V1  a new hint lands undocumented              1 clause red
V2  a documented hint is emitted by nothing    1 red
V3  the table loses a row                      1 red
V4  a row loses a cell                         1 red
V5  the guides stop naming each other          1 red
V6  the docs index link is repointed           1 red  (green until the
                                               clause read the target)
```

**Out of scope, held.** No enforcement guard for §1/§4 lives here —
those are with `UX-302`, `UX-304` and `UX-305`, beside the mechanisms
they hold.
