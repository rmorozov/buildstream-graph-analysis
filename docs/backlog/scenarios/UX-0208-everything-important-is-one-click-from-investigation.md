# UX-208: everything important is one click from investigation

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-204 (the TraceContext transport), UX-205 (the table tools these extend), UX-207 (the panel the top actions live in)

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

---

## Outcome (round 23)

**Status:** 🟢 Done.

**1. Path boxes answer.** Each box carries `data-popover` built from the
published entry — uid, kind, duration, share — and an investigate button
gated on `run.has_timeline`, so `UX-194`'s dead-button rule holds. The
guard reads the popover text back against `signals.critical_path_detail`
rather than recomputing it, which is why "a popover reading recomputed
values has no fixture to pass" is a statement about this test and not a
promise.

**2. A column can say it holds element uids.** `bga:columns` v2 grew a
`role`, validated against a closed set at the point it is written. The
Inspect affordance is one loop in `renderTable`, keyed on the
declaration; no table names itself anywhere in the viewer.

**Two things the filing did not know, both measured.** First, the
declaration reached almost nothing: `renderPairs` rendered a nested
array of objects as a `<details><pre>` of raw JSON, so
`signals.critical_path_detail` — the list of elements the entire report
argues about — was a JSON dump, and with it `optimization_horizon` and
`latent_heavies`. Nested arrays render as tables now, through the same
renderer with the same declarations, which is what makes point 2 visible
outside `blast/v1`. Second, the first version of the Inspect guard
counted affordances **page-wide**, and page-wide is not discriminating:
with all three `signals` declarations deleted the count stayed positive
on `headline.top_actions` alone. It asserts per table now — every table
that declares the role has one Inspect per row, every table that does
not has none — and the mutation reddens.

**3, 4, 5.** Copy on every SQL block (the text asserted equal, as a set,
to the block's own `renderedSql` — the page groups by category, so
declaration order is not render order); a Top-N preset that sets the
sort and hides the rest, badge reporting `10 of 40`; blast chips built
from `signals.top_blast_radius`, empty ranking giving no chips.

**A harness defect the suite would have hidden.** The DOM shim's
`append` pushed instead of moving, so `applyTopN`'s reorder duplicated
every row and a Top-10 read back as 20 visible. Fixed in the shim
(`appendChild` moves), along with a selector matcher that understands
`section[data-section]` — a tag-only matcher had been returning nothing
for it, which reads as "the page rendered no sections" rather than "this
harness cannot see them".

**Deviation from the Required Fix:** none, plus the nested-table change
above, which point 2 could not be honestly delivered without.

**Page-size guard:** it did not hold at 80,000 B, and the honest
accounting is in `test_the_payload_dwarfs_the_page`. Every byte that
could be taken was taken (the export now strips the stylesheet's
comments the way it already stripped the modules', worth 1,239 B); the
remaining 3.6 KB is rounds 22–23's feature code, and only a deletion
would bring it back under. The ceiling moved to 90,000 B with the
arithmetic recorded, and a second guard now asserts what the ceiling
cannot: that the page is the checked-in modules plus the stylesheet and
nothing else, so 4 KB of new feature and 4 KB of vendored library stop
looking alike.
