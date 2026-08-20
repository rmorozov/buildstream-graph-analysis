# UX-182: the inventory stops at the junction boundary

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-171 (the inventory this extends), UX-172 (the query that inherits it)

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
