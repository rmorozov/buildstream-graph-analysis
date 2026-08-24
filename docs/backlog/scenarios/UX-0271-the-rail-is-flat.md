# UX-271: the rail is flat, and the report has thirty sections

**Priority:** Medium | **Status:** 🟢 Fixed & Verified | **Depends on:** UX-254 | **Serves:** R1 | **Topic:** viewer

## Motivation

Requested: *"maybe we generally need to rethink navigation and bring
here a third column with a table of contents navigation bar containing
the full or partly full JSON structure"*.

The need is real and measured — the served report renders **30 sections
at 4 elements and 34 at 44**, in a rail that is one flat list per rail
group. But the proposed shape is challenged, for two reasons:

- **A JSON tree makes the document's shape the organising principle.**
  `UX-207` and `UX-199` deliberately moved the other way: the page
  answers questions, and the rail is grouped by *what you are trying to
  do* (`decide`, `investigate`). A structural tree is a data browser,
  and the reader already has one — the JSON.
- **A third column costs the reading column.** `UX-254` measured the
  two-pane layout at 1440px: the rail takes 18.8% and the text gets the
  rest. A third column leaves under 900px, undoing the item that was
  filed to *fix* the page being crowded.

What the request is actually asking for is that the rail stop being
flat. That is achievable without a column.

## Required Fix

1. The rail nests one level: section → its named subsections, expanded
   for the section you are in and collapsed elsewhere.
2. The growing group stays bounded (`UX-254` capped `investigate` in
   CSS with its own scroll rather than truncating in JS).
3. The jump box (`UX-223`) reaches subsections too, since that is the
   fastest path for anyone who knows what they want.

## Out of Scope

- A third column, per the argument above. If nesting the rail proves
  insufficient the column can be re-argued **with a measurement** of
  what it buys.
- Mirroring the JSON structure. The rail follows sections, which are
  questions.

## Acceptance Test

At 1440x900 the rail lists sections and their subsections, the reading
column keeps the width `UX-254` measured, and the geometry guards
(`UX-257`) still report zero overlaps at all three viewports.

## Outcome

**Fixed by nesting the rail, and the third column stays declined.**

```text
top-level rail entries   31
nested entries           12
bounded at               8 per section, then "+N more"
```

A section's subsections are the folded maps `UX-267` labels, each given
an id and a link. Bounded at `SUBSECTIONS_SHOWN = 8` with the remainder
counted rather than silently dropped (`UX-208`'s rule), because a
section with one entry per element would put the run's size back in the
rail — which is the defect `UX-254` capped in the first place.

**The declined alternative is recorded where the next person will meet
it**, in `nav.js` beside the code that answers the need: a structural
tree makes the *document's shape* the organising principle, which
`UX-207` and `UX-199` moved away from, and a third column leaves under
900px of reading width at 1440 (`UX-254` measured the two-pane split at
18.8%/rest). A guard fails if that argument is deleted.

**A guard that did not discriminate, and was fixed.** Replacing the
call with `void subsections;` left every test green — they checked the
function existed, not that the rail used it. A wiring guard now pins
the call site, and that mutation reddens.
