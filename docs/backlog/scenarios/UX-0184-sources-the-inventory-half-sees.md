# UX-184: sources the inventory half-sees

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (the inventory), UX-181 (the identity model)

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
