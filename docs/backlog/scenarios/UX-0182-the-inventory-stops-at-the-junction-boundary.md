# UX-182: the inventory stops at the junction boundary

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-171 (the inventory this extends), UX-172 (the query that inherits it) | **Topic:** analysis

## Motivation

UX-171 declares junction-prefixed elements `unreadable` — honest, and
verified live against a real junctioned build. But the projects the
monorepo question actually arrives from are junction-heavy:
freedesktop-sdk-style projects keep most elements *behind* junctions,
so on exactly the shape the axis was built for, the Shared Sources
answer degrades to a table of "unreadable" and the headline stays
silent. The user's real project is the test that matters here.

Also inherited by the query: `bga blast` runs a full `analyze` per
question (`bga/blast.py:161-176`) — at thousands of elements that is
the whole UX-168/169 analysis cost to answer one lookup; and path
queries resolve against the project root only, so a path typed from a
subdirectory silently misses.

## Required Fix

1. **Walk into checked-out junction subprojects**: when the junction's
   sources are on disk (the common case for a project being actively
   built), read the subproject's element YAML through the same
   memoised reader, prefix identities with the junction name, and keep
   `unreadable` only for junctions that genuinely are not there —
   counted and named, per UX-171's own no-silent-skips rule.
2. **`bga blast` answers from the inventory without the full
   analysis** when the question does not need durations (the
   direct/closure/kind half), and says "add a run for measured cost"
   — the expensive half stays optional.
3. Path queries resolve against cwd first, project root second, and
   say which matched.

## Out of Scope

- Junctions whose sources are not fetched (honestly unreadable).
- Cross-junction dependency edges beyond what `graph.json` already
  carries (bst show flattens them; the closure is already right).

## Acceptance Test

A fixture project with one junction whose subproject stages two
elements from a shared url: the table shows the junction-prefixed
resource with its blast, and `unreadable` appears only when the
junction checkout is removed (both asserted). `bga blast <url>`
without durations answers in under a second on the 1,000-element
synthetic project (timed bound, generous). A path query from a
subdirectory finds what the root-relative form finds.

## What was built

**Junctions.** `tools/bst_extract_run.py` grew `_junction_subproject`,
`_resolve_junctioned` (walking nested junctions left to right) and
`_qualify`. When a junction's sources are on disk the subproject's
element YAML is read through the same memoised reader, and identities
are namespaced by the junction — but only **content-keyed** ones: a
repository url stays global, so two subprojects sourcing one monorepo
group into one resource instead of two, which is the whole question
the axis exists for. `unreadable` survives only for junctions that
genuinely are not there, counted and named per `UX-171`'s
no-silent-skips rule.

**The expensive half is optional.** `blast(..., measure=False)`, wired
to `bga blast --no-cost`, answers the direct/closure/kind half from
the graph and the inventory alone and says *Cost: not measured* rather
than reporting zero. Measured on the 1202-element synthetic run
(`bga gen-synthetic --seed 1`, inventory of one shared url):

```text
measure=False  0.102s  direct=1202 blast=1202 measured=False
measure=True   3.221s  direct=1202 blast=1202 measured=True
```

**Paths resolve from where you are.** `classify_target` and
`_elements_for_path` try the target relative to the shell's cwd first
and project-relative second — but only when cwd is *inside* the
project. A `main.c` beside an unrelated shell says nothing about what
this project stages, and reading it as a path would trade one
confident wrong answer for another; both directions are asserted.

Tests: 24 in `tests/unit/test_identity_and_junctions.py` (shared with
`UX-181`). Mutations: dropping the cwd candidate reddens the
subdirectory case; consulting cwd unconditionally reddens the
outside-the-project case; removing the junction walk reddens the
prefixed-identity cases; deleting the junction checkout is what makes
`unreadable` appear, asserted rather than assumed.

## Deviation from the Required Fix

The acceptance asked for a **timed** bound ("under a second on the
1,000-element synthetic project"). The shipped guard is structural
instead: `_tasks_of` is monkeypatched to raise, so `--no-cost`
entering the analysis pipeline at all fails the test. A wall-clock
assertion is flaky on a shared runner and proves less than "the
expensive path is never entered"; the timing above is recorded here as
evidence rather than asserted in CI.
