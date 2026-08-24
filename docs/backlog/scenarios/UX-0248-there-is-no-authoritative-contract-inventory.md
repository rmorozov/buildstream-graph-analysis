# UX-248: there is no authoritative contract inventory

**Priority:** High | **Status:** 🟢 Fixed & Verified | **Depends on:** — | **Serves:** R4 and R8, who pin a document; and every guard that thinks it covers "every contract" | **Topic:** contracts

## Motivation

Direction 10 needs one thing before anything else: a list of what this
tool publishes that is *complete*. There isn't one, and the gap is not
theoretical.

Measured by scanning every `"<name>/v<n>"` literal in `bga/` and
`tools/` against `schemas.names()`:

```text
analyze/v1           registry
blast/v1             registry
compare/v1           registry
correlate/v1         registry
store/v1             registry
store-aggregate/v1   registry
whatif/v1            registry
host/v1              NOT IN schemas.names()   bga/hostinfo.py
sources/v1           NOT IN schemas.names()   bga/sources.py

registry: 7    stamped anywhere: 9
```

`host/v1` is known to `UX-233`'s drift guard as a hand-added special
case (`schemas.names() | {hostinfo.SCHEMA}`). **`sources/v1` is in no
registry and no guard at all** — and it is not an internal detail:
`sources.build_inventory` calls itself *"the on-disk shape"*, `bga
extract` writes it to `sources.json` in every run directory, and
`sources.load_inventory` reads it back. It is exactly the
written-by-one-`bga`-read-by-another artifact Direction 10 is about,
and it is invisible to every mechanism that is supposed to watch such
things — including the docs index table added one round ago
(`UX-236`), which lists eight.

The pattern that produced this is `UX-233`'s own: a guard that names
one file will not see the second one. `_published_schemas()` unions the
registry with one hard-coded id, so the third contract to be defined
outside `schemas.py` joins nothing.

## Required Fix

1. **One inventory, derived rather than listed.** Something that
   answers "every contract this tool stamps" without a human keeping a
   list — the scan above is the evidence that a hand-kept list loses.
2. `sources/v1` joins it, and therefore joins the spec's Part 32.5
   table, the architecture inventory and `docs/README.md`'s table,
   which is what `UX-233`'s existing guards will then demand.
3. The guard that finds a stamped id absent from the inventory, so a
   fourth one cannot arrive quietly.

## Out of Scope

- Registering `sources/v1` as a `--schema`-printable document. Whether
  it deserves a full published contract with view-hints is a separate
  decision; being *inventoried* is not the same as being published, and
  conflating them is how this one got skipped.
- Retro-versioning. Every contract stays at `v1`; this item is about
  knowing the set, not changing it.

## Acceptance Test

The inventory reports 9 (proving the gap against `schemas.names()`'s
7), a stamped id added in a test fixture is reported as missing, and
the existing `UX-233` guards go green over the full set rather than
over 8 of it.

## Outcome

**Status:** 🟢 Fixed & Verified

`bga/contracts.py` derives the set by walking the package for
module-level `SCHEMA` declarations, which is the convention every
contract outside `schemas.py` already followed. The next one is
inventoried by *existing* rather than by someone remembering.

```text
inventory()   9 contracts
printable()   7   (what `bga --schema` prints)
unprintable() 2   host/v1, sources/v1 - on-disk shapes, not documents
```

### The measurement is what happened when the guards were repointed

`test_the_documents_keep_up_with_the_contracts.py` and
`test_the_front_door_is_current.py` both used
`schemas.names() | {hostinfo.SCHEMA}`. Switching them to
`contracts.ids()` reddened three checks immediately, all on the same
contract:

```text
published schema(s) Part 32.5 does not list: ['sources/v1']
published schema(s) missing from the architecture inventory: ['sources/v1']
published schema(s) docs/README.md does not name: ['sources/v1']
```

That is the item's whole argument, run: a union with a literal covers
the contracts someone remembered. `sources/v1` had been written to
`sources.json` in every run directory since `UX-171` and read back by
`load_inventory`, and appeared in no registry, no guard and no
document. It is in all three now, with the *written but not printable*
distinction stated rather than left for a reader to discover at a
`--schema` refusal.

### Two derivations, not one

The module derives from the runtime (module `SCHEMA` constants plus the
registry). `tests/unit/test_the_contract_inventory_is_derived.py`
derives it a second way — scanning source text for `"<name>/vN"`
literals — and asserts the two agree. That catches the case the runtime
walk structurally cannot: a contract stamped by a string literal nobody
bound to a constant.

The derivation is proven to *be* a derivation rather than a list: the
guard writes a module into the package at runtime, asserts it joins the
inventory, deletes it, and asserts it leaves. Without the second half
the first would pass against a cached answer.

**A mutation of mine that did not discriminate.** Injecting
`owned["legacy/v1"]` to test "the inventory names nothing the source
does not" left the guard **green** — because the injected line is
itself a source literal, so the scan found it. Rejected rather than
counted; the mutation now builds the id from `chr()` calls so it exists
at runtime and nowhere in the text. The lesson is narrow and worth
keeping: *when a guard reads the source, a mutation written into the
source is part of what it reads.*

**Mutations verified red and reverted (4, one rejected and redone):**
the inventory stopping its package walk (reddened three checks); an id
in the inventory that no source stamps; a contract claiming an owner
that is not a file; the id pattern no longer requiring a version.

**Deviation from the Required Fix:** none.

Small tier: `2079 passed, 1142 deselected in 26.57s`.
Full suite: `3218 passed, 3 skipped in 360.71s`. `make lint`: clean.
