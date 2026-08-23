# UX-233: the architecture document meets the viewer axis

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-190 (the contracts it inventories), UX-232 (the hygiene sibling) | **Serves:** the maintainers; R8 when the big refactor is priced | **Topic:** docs

## Motivation

The user's observation: *we frequently forget to update architecture
and specification documentation, which later increases the cost of
big refactoring.* Measured: `design/architecture.md` still describes
three analysis planes and their extensions — it predates the entire
viewer axis (rounds 21-26: the server, the schema-driven page, the
export) and the contract wave (`headline`, `next_steps`,
`correlate/v1`, the store rows, culprits, provenance when `UX-229`
lands). The published-payload inventory — the tool's actual external
surface — exists only as the sum of `--schema` outputs and backlog
logs. Direction 8 and 9 both build on contracts; pricing that work
against an architecture document that stops at round 20 is exactly
the increased-cost failure the user names.

## Required Fix

1. `architecture.md` gains the two missing chapters, at its existing
   altitude: the viewer axis (server, schema dispatch, export, the
   no-arithmetic boundary) and the **published-contract inventory**
   (every `schema:` stamp, one line each, linking to `--schema` as
   the source of truth rather than duplicating it).
2. The spec's output-schema part names every published schema id
   (`analyze/v1`, `compare/v1`, `blast/v1`, `store/v1`, `host/v1`,
   `correlate/v1`, and successors).
3. The fixing-guide checklist gains: *does this change what
   `architecture.md` or the spec says is true? Same commit.*
4. The drift guard: a test extracts the schema ids the code emits
   and asserts each appears in the spec and the architecture
   inventory — a new payload without documentation reddens.

## Out of Scope

- Rewriting `architecture.md`'s existing chapters — they describe
  planes that have not changed, and a rewrite would lose the review
  history attached to text that is still true. Two chapters are
  *added*.
- Documenting viewer internals beyond the architecture altitude
  (module-level truth lives in the code and its guards).

## Acceptance Test

The drift guard is red on this tree the moment it is written (the
inventory is missing today — the guard's first run proves the gap),
green after the chapters land; mutation: emitting a new schema id
without touching the docs reddens it. The fixing-guide line exists.
