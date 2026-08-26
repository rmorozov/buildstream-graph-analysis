# UX-317: apparatus in its place

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-314 (the control group it tidies), styleguide §2b | **Serves:** R1 | **Topic:** viewer

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

## Log

**The header, measured.** Chromium, a served page, the handoff group
open — which is the state the field pass read and which the committed
fixtures do not reach on their own, so the measurement forces it:

```text
                          before      after
sticky header, 1440x900    172 px      92 px     -47%
sticky header,  390x844    284 px     134 px     -53%
blocks in the header          6           3
controls in the header        4           0
```

The header is `position: sticky`, so every one of those pixels is paid
on **every** screen rather than once. That is what "occupies precious
vertical height" costs, and it is why the budget is a guard: three
block lines, and no control at all.

**A defect the move fixed on the way.** `--head` — what every anchor's
`scroll-margin-top` and the rail's sticky offset read — was **5.5rem
against a 172px header**, so a pasted `#floors` landed 84px *under* the
heading. It is measured against the header it describes now (6rem wide,
8.5rem narrow), and a clause asserts `--head >= header height` at both
viewports rather than trusting the number.

**The descriptions.** `UX-201` put the schema's sentence in a `title`,
where discovery is hover archaeology. Every described value now shows a
visible `?`; the sentence opens **inside the `<dd>`**, beside the value,
inline where the row has room and below where it does not. Counted on
the two committed exports: **60 described values on the golden page and
72 on macro_micro**, one marker and one sentence each, all three
`<dt>`-building sites covered by one helper so a fourth would have to
opt out rather than forget.

The `title` stays on all of them. §4.3 asks that hover is never the
*only* door, not that it be shut, and the title is what a screen reader
and a keyboard focus already read.

**The room rule, measured rather than asserted.** The shim has no
layout engine, so the placement is checked in Chromium at both
viewports: at 1440 the sentence computes `display: inline` and sits to
the right of its value; at 390 it computes `display: block` and sits
below it.

**A five-year-old accessibility defect, found by the first guard that
read one back.** `el()` set anything not `class` or `data-*` as a
**property**:

```text
node["aria-label"] = "filter rows"    getAttribute("aria-label") -> null
node.setAttribute("aria-label", …)    getAttribute("aria-label") -> "filter rows"
```

Measured in Chromium 141 on a blank page. A property assignment
reflects nowhere — not into the attribute, not into a
`[aria-expanded="true"]` selector, not into the accessibility tree — so
the five `aria-label`s in `app.js` (the row filter, each column
threshold, the Top-N select, the preset view) had been invisible to
assistive technology since they were written. `UX-317`'s own
`aria-expanded` is simply the first one a guard reads back. `el()` now
sends every hyphenated name through `setAttribute`, and a clause walks
a built table asserting no `aria-` name sits on a node as a property.

**Deviation from the Required Fix, recorded.** It asks that the opened
state "survives in export/print as §2b requires". The marker and the
sentence both render in an export and in print, and the guard asserts
that no print rule hides either — but the *open* state is DOM, so a
description opened before printing prints and one that was never opened
does not. That is §2b.3's own wording ("the description renders
inline-on-open state only"); a page that printed all seventy-two would
print a glossary nobody asked for.

**Mutations — seven, all discriminating.** Run against the committed
tree, one at a time, reverted between:

```text
O1  a prose line added to the header       5 red   incl. both viewports
O2  el() reverts to data-only attributes   2 red   the aria clause, statically
O3  the marker is never built              5 red   incl. the browser placement
O4  the wide-viewport rule is deleted      2 red   the sentence never moves
O5  the sentence goes back in the header    7 red   the field defect, restored
O6  --head reverts to 5.5rem               1 red   88px against a 92px band
O7  the description is revealed by hover    3 red   the door being replaced
```

O5 is the one worth naming: it is the reported defect put back exactly
as it was, and it reddens the tag scan, the pixel measurement at both
viewports and the anchor-cover clause together.
