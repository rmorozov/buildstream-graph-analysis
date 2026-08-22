# UX-208: everything important is one click from investigation

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-204 (the TraceContext transport), UX-205 (the table tools these extend), UX-207 (the panel the top actions live in)

## Motivation

UX-204 gave findings an "Investigate in Perfetto" button; the
round-23 review's observation is that findings are the only objects
that got one. Everything else the page shows is inspection-only:

- **Critical-path boxes** (`bga/viewer/views.js`, `pathBox`) are
  anchors to `#signals` carrying `data-share` and
  `data-duration-us` — and showing neither. No share, no popup, no
  investigate; the drawing knows the element and tells the reader
  nothing they can act on.
- **Table rows** have no way into the workflow. A reader who finds
  `openssl.bst` at the top of a sorted duration column must
  remember the name, scroll to a finding that mentions it (if one
  does), and click there.
- **The SQL is copied by hand.** `questions.js` renders `<pre>`
  blocks and the investigate button reveals a paste — but
  `tables.js` already ships a `copy()` helper and neither surface
  uses it. Manual selection of a twelve-line query is the exact
  friction a button removes.
- **Top-N is spelled by hand.** UX-205's thresholds can express
  "worst ten" only as a guessed threshold; "show me the worst 10 by
  duration" is the single most common table question and it takes
  the most typing.
- **The blast box teaches nothing.** `renderBlastSearch` offers a
  free-form input and a placeholder; the payload already knows the
  top-ranked targets (`signals.top_blast_radius`), and the box
  could open with the next useful question instead of an empty
  field.

## Required Fix

1. Path boxes get a hover/click popover — element, duration,
   share-of-path, kind, all read from the published entry — plus an
   investigate button (via `investigationFor`, only when
   `run.has_timeline`; UX-194's dead-button rule stays).
2. A column can declare it holds element uids (a `role` in
   `bga:columns` v2); rows of such tables get one generic Inspect
   affordance — jump-to-element plus investigate — with no
   per-table code.
3. Every rendered SQL block (questions page, export, the
   investigate paste) gets a Copy button with a "✓ copied"
   acknowledgment.
4. The table tools grow a Top-N preset (`Top 10 ▾` by any declared
   quantity column): sets the sort and shows the first N, badge
   reporting `10 of 1,202`.
5. The blast box renders example chips from the published payload
   (top blast-radius elements; a resource url when `sources.json`
   names one) — click fills and asks.

## Out of Scope

- An element inspector page or comparison workspace (the P3
  deferral stands).
- New analysis or new queries (the query *content* is UX-210).
- Buttons on runs without a timeline.

## Acceptance Test

On `examples/06`: a path box's popover text equals its published
share and duration (asserted from `data-` attributes; mutation:
popover reading recomputed values instead of published ones has no
fixture to pass); a table whose columns declare an element role
renders per-row Inspect (mutation: remove the declaration → no
buttons, nothing errors); the Copy button places the block's exact
SQL into the clipboard stub; the Top-N preset on the 1,202-row
table leaves ten visible rows and the badge says so; blast chips
match the payload's ranking (mutation: empty ranking → no chips).
Page-size guard holds.
