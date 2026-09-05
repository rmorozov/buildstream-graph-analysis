# UX-435: the handoff box is measured in the mode where it is smallest

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 69, a field report that the Perfetto handoff occupies more of the left rail than it needs | **Serves:** anyone reading the rail while a server is behind the page — the mode `bga view` opens by default | **Topic:** viewer | **Area:** bga/viewer

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

**Round 70, 2026-08-31.** Reproduced in a real Chromium, both modes and
both viewports, on `with_timeline`.

### The defect

```text
                 group      share of rail
exported  1440x900   208x39px      4.9%
exported   390x844   327x39px     38.6%
served    1440x900  208x157px     19.5%
served     390x844  327x113px     64.2%
```

The desktop numbers match the item exactly. **The mobile served figure
is new**: 64.2% of the rail, which nothing had measured because nothing
had opened the served page at that width either. The item's own defect,
one dimension further out.

And the split it named:

```text
  actions            208x45px
  actions-download   208x92px   <- twice the affordance it falls back for
```

### What changed

The two fallbacks are **routes on the control's own line**, not
paragraphs under it. Each is still its own hideable element with its own
id, so `wireTheHandoff` unhides exactly what it unhid before —
`perfetto-link.parentElement` is still `#actions-fallback`,
`trace-download.parentElement` is still `#actions-download`. **No
JavaScript changed.** `UX-198` and `UX-314` added both for measured
failures and both are still here; this moved them.

```text
                 group      share of rail
served    1440x900  208x106px     13.2%      (-32%)
served     390x844   327x62px     50.0%      (-45%)
exported             unchanged
```

### The guard

`tests/unit/test_the_handoff_box_is_measured_served.py`, eight clauses,
14.2s (medium by measurement), serving the run and driving a browser at
both viewports:

- the served page really unhides a fallback — without which every bound
  below would be a measurement of the export, which is the defect;
- the group is under its height bound (130px / 86px, one wrapped line of
  headroom over the measured 106 / 62);
- the group is under its share of the rail (16% / 56%) — the field
  report's own unit;
- **no fallback renders as a block.** A height bound alone can be met by
  shrinking a font; the rule is what the height is spent on.

### Falsification

| # | mutation | result |
|---|---|---|
| H1 | the fallbacks go back to being `<p>` blocks (the item's own acceptance mutation) | **red** — 6 of 8 clauses, at both viewports |

### A clause of mine that was self-contradicting

The first cut of `test_the_served_page_really_unhides_a_fallback` looked
for the fallbacks in the page's list of **block** elements — a list this
fix empties of them by design. It asserted the opposite of what it
meant, and went red on the correct state. It reads each element's own
`hidden` and box now.

### A guard this change made wrong, fixed in the same commit

`test_the_perfetto_handoff.py::test_both_modes_offer_a_way_out_when_nothing_opens`
asserted the literal sentence `"Nothing opened?"` appears in both pages.
The way out still exists and was re-worded, so the clause went red on a
change that kept what it guards. It reads the **route** now — the
element that holds the fallback and the link inside it, named per page,
since `perfetto.html` calls its link `deep` and `index.html` calls its
`perfetto-link`.

### Deviation from the Required Fix

The Required Fix offered three shapes and asked the item to choose. The
second was chosen — the fallbacks as compact routes beside the primary
control, no sentence — because it needs no disclosure widget, no hover,
and no JavaScript, which is what makes it survive the export and a
`file://` open unchanged.

**The status sentence's width was not changed.** The item asks for "a
width that is not the rail's" for `#handoff`, and that is a real
problem — a ~300-character refusal in a 208px column is about fifteen
lines. It is not fixed here: the sentence is written by `app.js` only
when a hand-off fails, this session could not produce that failure to
measure it, and a width chosen without seeing the sentence rendered
would be exactly the unmeasured claim this repository forbids. Filed as
**`UX-451`** with what is known.

### The suite

```console
$ make lint
All checks passed!

$ make test
5429 passed, 28 skipped, 1 warning in 264.68s (0:04:24)
```
