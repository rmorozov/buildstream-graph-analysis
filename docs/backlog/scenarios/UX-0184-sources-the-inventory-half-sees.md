# UX-184: sources the inventory half-sees

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-171 (the inventory), UX-181 (the identity model) | **Topic:** analysis

## Motivation

Field feedback: *"when analyzing blast radius for repos there is a
case when recipe authors put actual path to repo inside kind:import
and kind:manual — generally there can be special handling needed;
maybe we need to recheck that such cases are handled well."*

Round 20 ground-truthed what is checkable from here:

- The inventory **does** read sources on every element kind —
  `resources_from_element` never consults `kind:`, verified live with
  `kind: import`. Import/manual elements with ordinary source stanzas
  are covered.
- bst itself **rejects** `local` paths that are absolute or escape the
  project (`node_get_project_path`: LoadError) — but bga's reader,
  fed one anyway (a project that does not build can still be
  inventoried), **silently mangles** it: `/opt/monorepo` becomes the
  identity `opt/monorepo` (colliding with a genuine project-relative
  path of that name), `../monorepo` is kept verbatim, and no
  complaint is raised — against UX-171's own no-silent-skips rule.
  `_elements_for_path`'s fallback can still prefix-match a `../`
  identity.

What is *not* checkable from here is the user's actual recipe shape —
"actual path to repo inside kind:import" may mean a workspace-style
checkout inside the project (handled, content-keyed), a symlink out
of it, or a repo path in `config:`/`variables:` that is not a source
stanza at all (invisible to the inventory by design). The fix must
start from a real stanza.

## Required Fix

1. Absolute and `..`-escaping local paths are **named complaints** in
   the inventory (like unreadable stanzas and packageless pip), never
   silently normalized into colliding identities; `_elements_for_path`
   refuses them in fallback too.
2. A symlinked source directory resolves to one identity (realpath at
   inventory time, recorded so the report and blast agree).
3. **Ask-the-user acceptance**: obtain one real import/manual element
   stanza from the field project (sanitized) and add it verbatim to
   the fixture set; whatever it turns out to be, the inventory either
   handles it or names it — the test pins which.

## Out of Scope

- Repo references outside `sources:` (config/variables) — invisible
  by design; if the field stanza shows this shape, that becomes its
  own filing with its own design.

## Acceptance Test

An inventory over a fixture containing an absolute path, a `../`
path, a symlinked directory, and the field stanza: the first two are
complaints with element names, the symlink is one identity, the field
stanza's behavior is asserted explicitly. Mutation: restoring the
silent `.strip("/")` normalization reddens the collision test.

## What was built

Reproduced first, exactly as the Motivation describes:

```text
'/opt/monorepo' -> opt/monorepo   | complaint: None
'../monorepo'   -> ../monorepo    | complaint: None
```

**1. A path this project cannot key is named.** `resource_of_source`
now refuses an absolute or `..`-escaping *content-keyed* path with a
complaint that says why - the absolute case naming the collision it
used to create (`/opt/monorepo` and a genuine project-relative
`opt/monorepo` became one row). Scoped to content keying: `git` against
a bare repository on local disk has an absolute url and is a perfectly
legal configuration, and there is a guard for it.

Content identities are also `normpath`ed now, so `sub/../files/src` and
`files/src` are one identity. The query side had always normalised; the
inventory side had not, so the two disagreed about one directory.

`_elements_for_path` refuses them too. A `sources.json` written before
this complaint existed still carries `../monorepo`, and its fallback
could prefix-match a query and answer confidently about a path the
project cannot key - it now matches nothing.

**2. A symlinked source directory is one resource.**
`_resolve_symlinked`, at extract time (the one moment the project is on
disk): a content-keyed identity whose realpath differs takes the real
project-relative path, and `declared` keeps what the recipe wrote. A
project staging `vendor/lib -> files/lib` beside an element naming
`files/lib` reported two resources and halved the blast the table
exists to show. A link pointing *out* of the project has no
project-relative identity at all and becomes a complaint, on the same
reasoning as the absolute case.

Tests: 18 new (`tests/unit/test_sources_the_inventory_half_saw.py`),
including the half round 20 verified as already working - every element
kind's sources are read, pinned across five kinds so the inventory
cannot learn to consult `kind:`. Five mutations, each red, and two of
them are over-refusal directions (`".." in path`, and applying the
check to ref-keyed urls), because refusing a working configuration is
this fix's failure mode.

## Deviation from the Required Fix

**Item 3 - the ask-the-user acceptance - is not done.** It requires "one
real import/manual element stanza from the field project (sanitized)",
and this session has no channel to the person who filed the feedback.
What was built instead is the *checkable* set: the three shapes round 20
ground-truthed (absolute, `..`-escaping, symlinked) plus the
already-working every-kind case, each asserted explicitly. The two
shapes the item names as *possible* readings of "actual path to repo"
are now handled and named respectively; the third reading it names - a
repo path in `config:`/`variables:` rather than a `sources:` stanza -
remains invisible by design and out of scope, per this item's own Out
of Scope.

This is recorded rather than quietly dropped: the fixture set does not
contain a real field stanza, and nobody should read this item as
evidence that one was checked.

