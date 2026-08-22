# UX-223: the jump box becomes a command palette

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 (the jump box), UX-216 (the actions it offers), UX-218

## Motivation

`wireJumpBox` searches section names and element uids and scrolls to
the hit (`app.js:686`). Useful, and now the weakest thing in the page:
by the time the reader has typed `openssl`, the page can offer the six
things they might want to do with it, and it offers one.

```text
> openssl

ELEMENT
  openssl.bst            672s · 18.6% path · saves 522s
ACTIONS
  → Show everything about openssl.bst
  → Focus openssl.bst
  → Inspect in Perfetto
  → Blast radius
SECTIONS
  → Findings
  → Critical path
```

Every row is a link or a control that exists elsewhere in the page.
This is an index over affordances, not a new capability — which is
precisely why it is cheap and why it should not grow into one.

## Required Fix

1. Results grouped: elements (with their published numbers beside
   them), actions on the current query, sections. Sourced from
   `jumpTargets` plus the actions `UX-216`/`UX-218` register.
2. Keyboard: `↑`/`↓` move, `Enter` runs, `Escape` closes, and a
   documented shortcut opens it from anywhere in the page.
3. An action whose precondition is absent is not listed —
   `UX-194`'s rule again: no Perfetto row on a run with no timeline.
4. The numbers beside an element are read from the payload, never
   recomputed.

## Out of Scope

- Fuzzy matching, ranking heuristics or a search index. Substring
  matching over a list the page already holds is what this is.
- Executing anything (`UX-218` proposes commands; it does not run
  them).
- Replacing `UX-205`'s per-table filters — those narrow a table, this
  navigates.

## Acceptance Test

Typing an element name yields its row with the published duration and
path share (asserted against the payload). On a run with no timeline,
no Perfetto action is offered and nothing errors. Keyboard: `↓ ↓ Enter`
activates the third result — asserted by the effect, not by focus
state.

Mutations, each asserted red: drop the has-timeline check → the dead
action appears on the no-timeline fixture; compute the shown duration
in the palette instead of reading it → a fixture where the two differ
reddens.
