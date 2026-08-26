# UX-317: apparatus in its place

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-314 (the control group it tidies), styleguide §2b | **Serves:** R1 | **Topic:** viewer

## Motivation

Two field observations, one placement rule. The save-the-trace
sentence (`bga/viewer/index.html:40`, `#actions-download`) renders
in the **header**, under the run information and above everything —
"occupies precious vertical height" and explains a control that
lives two blocks away in the actions group. And the attribution
section's descriptions hide behind hover on the term: the reader
who does not know to hover never learns what `scheduler_wait`
means; the one who does gets a tooltip they cannot keep open while
comparing values. §2b: a control's explanation lives with the
control; the header carries identity only, within a measured
vertical budget; a described value shows a visible `?` affordance
whose description opens beside the value.

## Required Fix

The trace-download sentence moves into the Perfetto action group
(under "open timeline", where its subject is); the header's
vertical budget is stated and guarded in lines. Every value whose
schema carries a `description` renders the visible marker; opening
it places the sentence to the right of the value where the row has
room, below where it does not; the state survives in export/print
as §2b requires. Attribution is the acceptance surface but the
mechanism is generic — any described value anywhere.

## Out of Scope

- Rewriting any description (the schemas own the prose).
- Header redesign beyond placement and budget — the header's
  content is right; only its apparatus and its height were the
  complaints.

## Acceptance Test

The booted header contains no control apparatus (walk asserts the
download sentence is inside the actions group, after the Perfetto
control it explains) and fits the stated line budget (mutation:
a prose line added to the header reddens); every described value in
attribution shows the marker (count equals described-field count);
opening one places the description adjacent per the room rule
(both layouts asserted at two viewports); print CSS renders opened
descriptions and never relies on hover.
