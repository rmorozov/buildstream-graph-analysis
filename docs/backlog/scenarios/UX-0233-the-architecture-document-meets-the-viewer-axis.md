# UX-233: the architecture document meets the viewer axis

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-190 (the contracts it inventories), UX-232 (the hygiene sibling) | **Serves:** the maintainers; R8 when the big refactor is priced | **Topic:** docs

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

## Outcome (round 28)

The guard was written first, and it was red on the tree it was written
against — which is what the acceptance asks for, and what makes the
number below a measurement rather than a claim:

```text
$ python -m pytest tests/unit/test_the_documents_keep_up_with_the_contracts.py -q
5 failed, 1 passed

$ python - <<'PY'
  ... schemas.names() | {hostinfo.SCHEMA} against the two documents ...
all: ['analyze/v1', 'blast/v1', 'compare/v1', 'correlate/v1', 'host/v1',
      'store-aggregate/v1', 'store/v1', 'whatif/v1']
missing from spec: ['correlate/v1', 'host/v1', 'store-aggregate/v1',
                    'store/v1', 'whatif/v1']
missing from architecture: all eight
```

**Five of eight published schemas were in no spec table, and the
architecture document named none of them at all.** It also still stopped
at round 20: three analysis planes and their extensions, written before
the server, the schema-driven page and the export existed.

Two chapters were *added* — the existing ones describe planes that have
not changed, and rewriting them would lose the review history attached
to text that is still true:

- **The viewer axis** at the document's existing altitude: the server
  and its two parameterised endpoints, the schema-driven page (view
  hints, no build step, no framework), `--export`, and the
  **no-arithmetic boundary** — a viewer that derives a conclusion is a
  second analyzer, so where a question needs a number the payload does
  not carry, the page asks the server.
- **The published contracts**: eight rows, one line each, with
  `--schema` named as the source of truth rather than the schemas
  reproduced.

The spec's Part 32.5 went from three rows to eight, and Part 32's
opening block lists them.

### Two guards that passed for the wrong reason, found by falsifying

Both were mine, both written minutes earlier, and both were caught only
because the mutation refused to redden:

- **"every schema is named in the spec"** matched anywhere in the file.
  Deleting `correlate/v1`'s row from Part 32.5 left it green, because
  the id also appears in Part 32's opening block. Scoped to 32.5's own
  section, the deletion reddens.
- **"the inventory points at `--schema` rather than copying it"** asked
  whether the string `--schema` appeared, which every table row contains
  anyway. Rewording the sentence that makes the claim changed nothing.
  It now also asserts the chapter contains no `"properties"`, `$schema`
  or `"type":` — the actual failure is somebody pasting the schemas in,
  and that is what it looks like.

**Mutations verified red and reverted (5):** a new schema id registered
in `bga/schemas.py` with no documentation (reddens both the spec and the
architecture guard); an inventory row for a schema nothing emits; the
viewer chapter losing the boundary it is about; the chapter pasting a
schema fragment in; Part 32.5 dropping a row. The last two are the
redone ones.

**The fixing guide gains item 9**, mechanical half guarded and judgment
half stated: *does this change what `architecture.md` or the spec says
is true? Same commit.*

**Deviation from the Required Fix:** none. Two chapters added, nothing
rewritten, and the inventory links rather than duplicates.

Full suite: `3100 passed, 3 skipped`.
