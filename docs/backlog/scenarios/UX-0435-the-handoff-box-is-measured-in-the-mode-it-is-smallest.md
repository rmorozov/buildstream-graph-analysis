# UX-435: the handoff box is measured in the mode where it is smallest

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 69, a field report that the Perfetto handoff occupies more of the left rail than it needs | **Serves:** anyone reading the rail while a server is behind the page — the mode `bga view` opens by default | **Topic:** viewer

## Motivation

`#actions-group` holds the Perfetto handoff in the sticky rail. Measured
on a real capture of `examples/06`, at 1440x900, in both modes:

```text
                 group      share of rail    visible paragraphs
export           208x39px          4.9%              1 of 3
served          208x157px         19.5%              2 of 3
```

**Four times the height, in the mode `bga view` opens by default.** The
export hides two of the group's three paragraphs — they are unhidden
only when a server is behind the trace — so a measurement taken there
reports a box that is not the one the reader has.

Served, the space goes where nobody would choose to put it:

```text
  actions            208x45px   Open timeline in Perfetto / Questions to ask it
  actions-fallback     hidden   Nothing opened? open ui.perfetto.dev with this trace.
  actions-download   208x92px   Or save the trace and drag it into ui.perfetto.dev.
```

**The two controls cost 45px; one fallback sentence costs 92px** —
twice the affordance it is a fallback for. And `#actions-fallback` is
hidden only because Perfetto's CSP permitted the deep link on this
capture; where it does not, a third paragraph unhides and the box grows
again. The worst case is larger still: `app.js` writes a ~300-character
refusal sentence into `#handoff`, in the same 208px-wide column.

`tests/unit/test_apparatus_in_its_place.py:191-201` guards this group —
`position === "static"`, `group_px > 0` — with **no upper bound on its
height**, and its fixture is the export, chosen with a stated reason:
"the header, its budget and the room rule are identical in both". They
are; the handoff group is not, and it is the thing being measured.

**This is `§3f`'s rule in a second dimension.** That section says a
bound is enforced at the largest size the tool tells people to use.
This says: **in the mode people use it in.** A page has modes as well
as sizes, and a measurement taken in the mode where a control is
smallest has not met the control.

## Required Fix

- **Bound the group's height**, measured served and at both viewports,
  and let the guard fail when it grows.
- **Spend the space on the control, not on its fallbacks.** The two
  fallbacks exist because pop-up policy and CSP both fail sometimes
  (`UX-198`, `UX-314`) and neither may be dropped — but neither needs to
  be prose in the rail at rest. Options, to be decided in the item:
  - both fallbacks behind one `?` or a `details` whose summary is a
    single glyph, opened when the primary control fails;
  - the download as an icon-button beside the primary, no sentence;
  - the fallback text moved into the status line that already exists
    (`#handoff`), which is written to only when something has gone
    wrong — the case the fallbacks are for.
- **The status sentence gets a width that is not the rail's.** A
  300-character sentence in a 208px column is roughly fifteen lines.
- Whatever is chosen must still survive the export and a `file://`
  open, and must not depend on hover to be discoverable (§1's standing
  constraint).

## Out of Scope

- **Removing either fallback**: both were added for a measured failure
  and this item changes where they sit, never whether they exist.
- **The rail's own width** — 240px is settled and several sections
  depend on it.
- **`UX-430`'s trace-size work**: a smaller trace would make the CSP
  refusal rarer, which shrinks the worst case here, but the two items
  fix different things and neither waits on the other.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
bga view @last --port 8931 --no-browser
```

Measure `#actions-group` in the served page at 1440x900 and 390x844.
Its height is under the stated bound with the fallbacks present, and a
mutation that unhides both fallbacks as prose must redden the guard —
a guard measuring the export passes that mutation, which is the defect
this item is.

## Outcome

_Not started._
