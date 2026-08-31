# UX-451: the hand-off's refusal sentence is written into a 208px column

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 70, the half of `UX-435` that could not be measured | **Serves:** the reader whose hand-off failed — the only reader who ever sees this sentence | **Topic:** viewer

## Motivation

`#handoff` is the status line inside the rail's hand-off group.
`app.js` writes into it, and one of the things it writes is a refusal:
a sentence of roughly 300 characters explaining that Perfetto's CSP,
or the size threshold, or the pop-up policy stopped the trace opening.

The rail is 240px wide and the group inside it measures 208px. Three
hundred characters at `.82rem` in a 208px column is on the order of
fifteen lines — in a sticky column, on the screen of a reader who has
just had something fail.

`UX-435` bounded the group's *resting* height and left this alone, for
a stated reason: **the sentence could not be produced to measure.** It
appears only when a hand-off actually fails, which needs Perfetto to
refuse a real trace, and a width chosen without seeing it rendered
would be the unmeasured claim this repository forbids. `UX-435`'s guard
therefore bounds the group with the status line **empty**, which is
honest about what it measured and silent about this.

## Required Fix

- **Produce the sentence.** Drive the failure rather than waiting for
  it: `wireTheHandoff` decides from `perfettoCanFetch` and the size
  threshold, both of which a guard can force. Then measure the group
  with the sentence in it, at both viewports, served.
- **Give it a width that is not the rail's**, or a shape that does not
  need one — the same three options `UX-435` weighed for the fallbacks
  apply here, and the third of them (fold the refusal into the status
  line) is what created this.
- **Extend `UX-435`'s bound to the failed state**, so the group is
  bounded in the mode *and* the state where it is largest. That is the
  same rule one step on, and leaving it out is what this row records.

## Out of Scope

- **What the sentence says**: `UX-326` made the tool's sentences
  contracts and this changes where one is drawn, never its wording.
- **The rail's width**: 240px is settled, as `UX-435` also recorded.
- **`UX-435`'s resting bound**, which is measured and holds; this adds
  a state to it rather than replacing it.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --port 8931 --no-browser
```

Force a refusal, measure `#actions-group` at 1440x900 and 390x844 with
the sentence rendered, and paste both. The height is under a stated
bound, and a mutation restoring the sentence to the rail's width
reddens the guard.

## Outcome

_Not started._
