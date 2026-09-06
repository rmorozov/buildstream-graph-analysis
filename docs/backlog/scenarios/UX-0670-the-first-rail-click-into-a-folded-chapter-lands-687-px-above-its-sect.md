# UX-670: the first rail click into a folded chapter lands 687 px above its section

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-399 (`content-visibility: auto`), UX-534 (Focus scrolls) | **Serves:** anyone who clicks a rail entry | **Topic:** viewer | **Shape:** judgement

## Motivation

```text
rail link → binary_cost (chapter folded, fresh load)    lands at sectionTop −687 px   (twice, two fresh loads)
same link once the chapter is open                       lands at 104 px — under the sticky header, correct
```

`content-visibility: auto` (`UX-399`) estimates the height of a
folded chapter's unrendered sections; the scroll runs against the
estimate, the chapter opens, the real height arrives, and the reader
is two thirds of a screen above the heading they clicked.

## Required Fix

Reveal first, then scroll: `revealChapter` awaits layout (a frame
after the fold opens, or `contain-intrinsic-size` set from the
rendered height the page already measured) before `scrollIntoView`;
the landing position is asserted for a link into a folded chapter on
a fresh load.

## Out of Scope

- `content-visibility` itself — `UX-399`'s saving stands.

## Acceptance Test

Guard (browser tier): fresh load, click a rail link into a folded
chapter — the section's heading rect top is within the sticky
header's height of the viewport top. Mutation: scroll before reveal
— red.

## Outcome

**The gap, measured.** On `macro_micro`, exported and booted at
1440x900, **one fresh load per link** - 61 rail links whose target is a
section in a chapter folded on load. Section top against the 104 px a
correct landing gives:

```text
whatif                -736      restructuring          -317
perfetto-questions    -576      critical_path_detail   +673
```

Both directions, so it is not an offset anyone could subtract, and 55
of the 61 already landed correctly - the miss is a property of the
particular fold, not of every one.

**The close, measured**, same page, same method:

```text
landings       104-105 px on all 55; header 92, scroll-margin-top 104
the other 6    run_instance, producer, document_shape, cpu_time,
               peak_memory, utilization_envelope - all at fromEnd 0,
               where the document stops, not where the fix failed
```

**The mutation table.** Six, each reddening a named clause in
`test_a_rail_click_lands_on_its_section.py`.

| mutation | clause that reds |
|---|---|
| drop the settled landing | `..._lands_now_and_again_two_frames_later` |
| one frame, not two | `..._every_link_lands_or_runs_out_of_page` |
| drop the immediate landing | `..._lands_now_and_again_two_frames_later` |
| the delegated anchor keeps `revealChapter` | `..._every_way_in_goes_through_the_settle` |
| the jump box keeps `revealChapter` | `..._every_way_in_goes_through_the_settle` |
| the fold opens but nothing lands | `..._every_link_lands_or_runs_out_of_page` |

**One clause of mine was too tight, and the suite found it.** The
landing band was asserted as the set `[104, 105]`, measured
single-process; under `-n auto` the same landing rounds to 103 and the
file went red in `make test`. It is a stated +-2 band now - four
pixels against a 900 px viewport, which still rejects -317 and +673.

**Four deviations.**

*It lands twice, not once.* The Required Fix says await layout, then
scroll. Measured, one frame is **worse than none** - 6 of 61 correct
against 55 - because it runs mid-layout while the estimate is still
live. Landing now covers the jump box, which has no anchor scroll of
its own; landing again two frames later covers the fold. The first
draft did only the frames, and the mutation that removed them left
every browser clause green: the rail link's own anchor scroll was
supplying the first landing and the guard could not see it.

*`contain-intrinsic-size` was not needed.* The Required Fix offers it
as the alternative; a second `scrollIntoView` after layout costs
nothing and adds no state to keep in sync.

*Six links land where the page ends.* The Acceptance Test asks for the
heading within the header's height of the viewport top, which no
section in the last screenful can satisfy. The guard asserts the
**split** - 55 under the header, those 6 at `fromEnd == 0`, named -
rather than a tolerance that would also pass -317.

*One defect this falsified, filed rather than fixed here.* Two rail
targets are not sections: `restructuring--edges` and
`restructuring--projection` are `<details>` inside a `<table>` whose
`overflow` is `auto`. Both land at 44 px - under the 92 px sticky
header, with 895 px of scroll left - before this change and after it.
A nested scroll container, not an estimate (`UX-722`).
