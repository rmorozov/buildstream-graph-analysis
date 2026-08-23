# UX-223: the jump box becomes a command palette

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-199 (the jump box), UX-216 (the actions it offers), UX-218

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

## Outcome (round 26)

`paletteResults` is a pure function over the list the page already
holds, so the guards test it directly rather than through a rendered
document. Results come back grouped — elements with their published
numbers, actions on the current query, sections — and the rendering in
`app.js` walks the groups into a flat keyboard order, so `ArrowDown`
moves through what a reader sees.

**Clause 3 is guarded in both directions**, which matters more than it
sounds. A guard that only asserts "no Perfetto row on a run with no
timeline" passes on an implementation that offers nothing at all, so
there is a companion asserting the row *does* appear when there is a
timeline.

**Clause 4's fixture separates read from derived.** `total_duration_us`
is 100 s while `openssl.bst` alone is 672 s, so a palette computing its
number from the run total cannot match the payload's — the mutation this
task names reddens three guards on it. An element off the critical path
has `share_of_path: null`, not zero: zero would read as "on the path,
costing nothing".

### Two collisions the flattened export found

The export concatenates every module into one scope. The first draft
declared `elementFacts` in `nav.js` — and `views.js` has had one since
UX-216 — and a `cssId` that `app.js` also declares. Both are a
`SyntaxError` in the shipped page: **UX-199's defect, by a new route**,
and the exported report renders nothing.

Renaming to `paletteFacts` fixes the first. The second was fixed by
*not duplicating at all*: `views.js` imports nothing, so `nav.js` can
import `elementAnchor` from it, and the palette's link and its target
stay one expression — which is the whole of UX-216.

A general guard came out of it: **no two modules may export the same
top-level name.** That is the class of bug, not this instance of it, and
it is the kind a byte-count or a render test would never name.

**Mutations verified red and reverted:** drop the has-timeline check (2
guards — this task's first); compute the shown duration rather than read
it (3 — its second); let the palette spell its own anchor (1).

**Deviation from the Required Fix:** clause 2 asks for "a documented
shortcut" to open the palette from anywhere. `Escape` closes and the
arrows and `Enter` work as specified; a global open-key was **not**
added, because binding a document-level key needs a decision about what
it does inside the filter inputs UX-205 put on every table, and guessing
that is a worse outcome than leaving the box reachable by click and by
tab. Recorded rather than silently dropped.
