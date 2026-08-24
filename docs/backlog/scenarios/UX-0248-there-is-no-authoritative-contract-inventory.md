# UX-248: there is no authoritative contract inventory

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Serves:** R4 and R8, who pin a document; and every guard that thinks it covers "every contract" | **Topic:** contracts

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
