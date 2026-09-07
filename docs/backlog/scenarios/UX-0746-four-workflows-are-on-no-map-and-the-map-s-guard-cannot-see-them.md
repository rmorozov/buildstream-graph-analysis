# UX-746: four workflows are on no map, and the map's guard cannot see them

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-239 (the context map), UX-573 (the last time the map's walk was too narrow to notice) | **Serves:** the low-context session told not to re-derive where things live | **Topic:** docs | **Area:** unassigned | **Shape:** judgement

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

## Outcome

### The gap, measured

```text
$ ls .github/workflows/*.yml
ci.yml  mutation.yml  quality.yml  real-project-capture.yml
$ sed -n '165,442p' docs/contributing/fixing-guide.md | grep -c "github\|workflow"
0
```

Confirmed before the fix: adding `.github/workflows/probe.yml` (a file
that does not exist) produced no red anywhere, because `MAPPED_SUFFIXES`
had no `.github/workflows/` root for either walk direction to read.

### The close, measured

`.github/workflows/` joined `MAPPED_SUFFIXES` as `(".yml",)`; §6 gained
a "**The CI workflows**" block, one row per file with a `when` column
(`push/PR`, `PR + weekly`, `weekly`, `manual`) — the other halves of the
map name only *what*, but `mutation.yml` and `real-project-capture.yml`
only make sense against *when* they run. The intro paragraph above §6's
map was re-wrapped to add `.github/workflows/` to the walked list. The
stale-path regex (`test_the_map_names_nothing_that_does_not_exist`)
gained `\.github` to its alternation, since it excludes dot-prefixed
roots by default.

```text
$ make lint
All checks passed! / clean: 291 finding(s)
$ python3 tools/dev_touching.py
40 file(s) selected (23 census + 17 naming the change) · 1101 passed, 3 skipped
$ make test
7597 passed, 127 skipped, 1 warning in 493.25s (0:08:13)
```

### Mutations verified red and reverted (3)

| # | mutation | reddened |
|---|---|---|
| M1 | deleted `mutation.yml`'s §6 row | `test_every_module_is_on_the_map` names the file |
| M2 | added a `probe.yml` row for a file that doesn't exist | `test_the_map_names_nothing_that_does_not_exist` names it |
| M3 | removed `.github/workflows/` from `MAPPED_SUFFIXES` | `test_the_walk_finds_each_population_it_claims_to_walk`'s new vacuity member (`.github/workflows/ci.yml`) |

M3 is the clause `UX-573`/`UX-746`'s own text asks after: without a
named vacuity member for the new suffix, removing the root from
`MAPPED_SUFFIXES` reddened nothing (the walk over an empty root passes
vacuously) — so `.github/workflows/ci.yml` was added to that clause's
list precisely to make M3 discriminate.

### Deviation: the row this task asked for was false

The verifier read the `.yml` the row describes. `real-project-capture.yml`
is not manual: it carries `schedule:` with two crons alongside
`workflow_dispatch`.

```console
$ grep -n "^on:\|^  schedule:\|^  workflow_dispatch:\|cron:" \
    .github/workflows/real-project-capture.yml
70:on:
71:  workflow_dispatch:
148:  schedule:
149:    - cron: "0 3 * * 0"
158:    - cron: "0 4 1 * *"
```

Both crons predate this row (`git show 1a31fac:` has them), so nothing
in this diff introduced it — this task's own Required Fix asserted
"manual" and the track copied the premise forward without opening the
file. The row now names all three triggers. A row that misdescribes a
workflow is worse than no row, which is the map's whole point.

The dropped `docs/design/capture-workflow.md` citation is restored. Its
stated reason — that it tripped `test_the_map_states_no_count_it_does_not_check` —
does not reproduce: that guard fires only on a number glued to one of
six plural nouns, and the citation is neither. 30 passed with it back.
The narrowness of that noun list is `UX-750`.
