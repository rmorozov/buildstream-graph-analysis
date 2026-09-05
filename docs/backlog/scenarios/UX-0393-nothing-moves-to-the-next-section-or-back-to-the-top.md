# UX-393: nothing moves to the next section, or back to the top

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-199 (a report you can find your way around), UX-286 (the report has chapters), UX-347 (the distance budget), UX-209 (the rail) | **Serves:** anyone reading past the first screen | **Topic:** viewer | **Area:** bga/viewer

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

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, and where the controls went

The rail already said *where you are* — `UX-399` landed the scrollspy
one phase earlier in this round, so the third Required Fix bullet was
done before this started. What was missing is the step.

Driven in Chrome on the exported `macro_micro` page:

```text
nav.toc .toc-steps            [top] [previous] [next]
rail entries                  66

six presses of Next   #readers #evidence #overview #findings
                      #headline #next_steps
two presses of Prev   #headline #findings
86 more presses       #document_shape   (the last, and it stops)
```

**In the rail, not a banner.** `UX-347`'s distance budget measures
scroll distance to *content*, and a 60 px chrome bar makes every
measurement on every screen worse. The rail is already sticky and
already beside the reading column, so three buttons at its head cost
that column nothing — the distance and volume guards are unchanged.

### The trap: the mark is asynchronous

Reading `data-current` on every press means reading a mark an
`IntersectionObserver` has not written yet, and the scroll it is
watching is smooth. Measured before the cursor landed:

```text
six presses of Next   decision decision decision decision decision decision
```

So the stepper carries its own cursor and adopts the mark only when the
mark has **moved on its own** — the reader scrolling, the one case
where the mark knows something the cursor does not. A mark that is
merely behind reads as the same value it had at the previous step, and
that is what tells the two apart.

`test_two_presses_move_two_sections` is what would catch it coming
back, and the guard reads `location.hash` — set synchronously by the
rail link — rather than the mark this item had to stop depending on.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it.

| # | mutation | reddened |
|---|---|---|
| E1 | the stepper reads `data-current` on every press again | 5 of 8, incl. `test_two_presses_move_two_sections` |
| E2 | wrap at the end instead of clamping | 1 of 8: `test_next_past_the_end_stops` |
| E3 | show the Top button always | 1 of 8: `test_it_appears_only_once_there_is_a_top_to_go_back_to` |
| E4 | drop the input/textarea/select check on the key handler | 1 of 8: `test_they_are_ignored_while_typing` |

### Deviation from the Required Fix

- **The third bullet was already done.** `UX-399` landed the rail's
  `data-current` mark earlier in this round; this item consumes it
  rather than repeating it, and the two cannot disagree about where the
  reader is because one writes the mark and the other reads it.
- **Keyboard reach is Tab plus `[` and `]`.** The three controls are
  buttons, so the keyboard reader `UX-223` established reaches them
  already; the bracket keys are an accelerator, unmodified and
  unclaimed, ignored while the reader is typing so the palette does not
  lose two characters.
- **`PAGE_BUDGET_B` moved 276,000 → 280,000**, +2,652 B of source for
  this item (`UX-392` had already spent 584 within the old bound, and
  the note in the guard carries both). The reading column and both
  payloads are unchanged — which is the point of putting the controls
  in the rail rather than in a banner.
