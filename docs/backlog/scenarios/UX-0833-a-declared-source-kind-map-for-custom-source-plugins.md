# UX-833: a declared source-kind map for custom source plugins

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-192 (the source kind behind a heuristic), UX-683 (a declaration in project.conf) | **Found by:** round 115, the design review | **Serves:** R2 whose sources come through a custom plugin | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`bga/blast.py:202` names the source kind behind a resource-blast
match by heuristic over the kinds BuildStream ships. A project whose
elements fetch through a custom plugin — a Gerrit source, an internal
mirror — matches nothing, and the blast for a change to that source is
unreported rather than wrong.

## Required Fix

A declaration beside `bga-foundation`: `variables: {bga-source-kinds:
"gerrit=git"}` maps a plugin kind onto the shape the heuristic already
reads (git-like: `url` + `ref`; tar-like: `url` + `sha`), validated at
extraction; an unmapped custom kind is reported as such in
`element_join_coverage`, never silently skipped. Judgement: whether the
map is by kind or by field names is the design question the task
answers first.

## Decomposition

Input classes: a mapped custom kind, an unmapped one, a project with
no declaration (today's behaviour byte for byte); the journey is R2's
resource-blast question in the answer key.

## Out of Scope

- Writing plugin-specific readers — the map is the mechanism; a reader per plugin is what it avoids.
- Resource blast for non-source resources — out of `blast.py`'s question.

## Acceptance Test

A fixture with a `gerrit` kind mapped to `git` produces the same
resource-blast rows as the same element with kind `git`; unmapped, the
coverage block names the kind.
