# UX-306: the visual contract joins the tree it governs

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** styleguide (the document), UX-231 (the traceability pattern) | **Serves:** the maintainers | **Topic:** docs

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
