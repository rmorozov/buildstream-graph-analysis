# UX-746: four workflows are on no map, and the map's guard cannot see them

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-239 (the context map), UX-573 (the last time the map's walk was too narrow to notice) | **Serves:** the low-context session told not to re-derive where things live | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

## Motivation

`fixing-guide.md` §6 is headed *"Where things live (context map — don't
re-derive this)"*. It names no `.github/workflows/` file, and four
exist:

```console
$ ls .github/workflows/
ci.yml  mutation.yml  quality.yml  real-project-capture.yml
$ sed -n '165,442p' docs/contributing/fixing-guide.md | grep -c "github\|workflow"
0
$ git grep -l "mutation.yml" -- 'docs/*.md' 'CLAUDE.md' '.claude/*' | grep -v backlog
$ # (no output: no live document names it)
```

CI reaches §6 only sideways, through the artefacts it writes —
`tests/ci_reference.json`, `tests/touch_map.json`. The workflows
themselves are unmapped, and two of them (`mutation.yml`, `quality.yml`)
shipped in rounds 102-103 with no document naming either.

**The guard cannot see it.** `test_the_context_map_is_the_tree.py`
walks exactly what `MAPPED_SUFFIXES` lists —
`{"tools/": (".py", ".c", ".h", ".sh"), "bga/viewer/": (".js", ".html",
".css")}` — plus `bga/`. A directory absent from that table is absent
from both the map and the check that the map is complete, so the
omission is invisible in the same motion.

This is the third time in this shape. `UX-239` filed the map when it
said *"tests/test_e2e.py — only existing test file"* against 220 test
files. `UX-573` widened the walk when it was `tools/*.py`
non-recursively, so `hook.c`, `spine.c` and `bwrap_shim.py` — Plane 2
itself, the map's own subject — were on neither the map nor the guard.

## Required Fix

`.github/workflows/` joins `MAPPED_SUFFIXES` with `(".yml",)`, and §6
gains a row per workflow: what fires it, what it gates, and where its
output goes. The guard then holds both directions, as it already does
for `tools/` — a new workflow with no map row is red, and a map row for
a workflow that no longer exists is red.

Weigh, and record which was chosen: `real-project-capture.yml` is
manual and `mutation.yml` weekly, so a row per workflow may want a
*when* column that the other halves of the map do not have.

## Out of Scope

- Documenting what each workflow *does* beyond one line. The map says
  where a thing lives; `docs/design/` argues why.
- The round-document gap (`UX-744`) and the workflows' own content.

## Acceptance Test

`ls .github/workflows/*.yml` and §6's workflow rows are the same set,
in both directions. Mutation: add `.github/workflows/probe.yml` — the
guard reds naming it; add a §6 row for a workflow that does not exist —
the guard reds the other way. Today, before the fix, the first mutation
passes silently, which is the finding.
