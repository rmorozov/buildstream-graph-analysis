# UX-393: nothing moves to the next section, or back to the top

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-199 (a report you can find your way around), UX-286 (the report has chapters), UX-347 (the distance budget), UX-209 (the rail) | **Serves:** anyone reading past the first screen | **Topic:** viewer

## Motivation

The user asked whether there is an easy way to reach the next section
when it is off-screen. Counted on the round 63 export:

```text
page height                     9,316 px   (7.4 screens at 1,260 px)
rail entries                          77
controls matching next/prev/top        1
```

The one control is an ordinary link to `#next_steps` inside a
sentence. There is no *next section*, no *previous section*, no *back
to the top*, and nothing that says where in the report the reader
currently is.

The rail is sticky and lists seventy-seven entries, which is the
report's map — but a map is not a step. A reader working through the
findings in order has to move the pointer to the rail, find the entry
after the one they are on among seventy-seven, and click it, for every
section. Over 7.4 screens that is the dominant navigation cost, and
it is exactly the distance `UX-347`'s budget was written to measure.

`UX-199` gave the page a rail and an anchor per section; this is the
half that was never built on top of it.

## Required Fix

- **Next and previous section**, from wherever the reader is,
  following the page's own declared section order (`UX-235`'s order,
  not the DOM's accident).
- **Back to the top**, appearing once the reader is past the first
  screen.
- **The rail says where you are.** The current section is marked in
  the rail as the page scrolls, so seventy-seven entries become a
  position rather than a list.
- Keyboard reach for all three, since `UX-223` already established the
  page has a keyboard reader.

## Falsification

A driven browser: load the export, press the next-section control N
times, and assert the viewport lands on each section of the declared
order in turn and then stops; press back-to-top and assert the scroll
offset returns to zero. Today there is no control to press.

The other direction: the controls must not add a fixed banner that
costs vertical space on every screen — `UX-347`'s distance budget
measures scroll distance to content, and a 60-px chrome bar makes
every measurement worse. Whatever is added is measured against that
budget before it lands.

## Out of Scope

- Changing the section order. This item moves through the order the
  page already declares.
- The rail's contents. Seventy-seven entries is `UX-286`'s chapter
  question, and folding it is a different item.
