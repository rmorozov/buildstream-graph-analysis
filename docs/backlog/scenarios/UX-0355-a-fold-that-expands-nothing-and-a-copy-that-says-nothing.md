# UX-355: a fold that expands nothing, and a copy that says nothing

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-347 (chapters fold), UX-279 (a copy control says what it copies) | **Serves:** anyone who lands on the report and tries to open it | **Topic:** viewer

## Motivation

Round 55 pressed every control class the page offers, on the page an
export actually produces, in the state a reader lands in. Twelve button
classes, two selects, one input class. Ten of them do what their label
says. Two do not.

### "Expand all" expands nothing

The rail's pair is built on `collapsible().all(shut)` in `nav.js`,
which walks **sections**. `UX-347` moved the document's fold to the
**chapter**. Sections are default-open — `collapsible` says so in its
own docstring, *"a report that hid itself on first load would answer
the navigation complaint by making the document harder to read"* — so
from a fresh load `all(false)` opens what is already open.

Measured on `golden`, at 1440x900, exported from the fixture in
place:

```text
                                     height   chapters open   sections
                                                              collapsed
landed                                3,548             1/7           0
after clicking "Expand all"           3,548             1/7           0
after opening each chapter by hand   13,844             7/7           0
"Expand all" again, chapters open    13,844             7/7           0
```

`macro_micro` behaves identically at its own scale: 5,588 px landed,
5,588 after "Expand all", 24,689 with the chapters opened by hand.

"Collapse all" *does* work — it shuts the six sections of the one open
chapter, and the height moves. So the pair is asymmetric: one half acts
on a layer the reader can see, the other on a layer that is already
open. A reader who wants the whole document clicks six chapter
headings, one at a time, and the control that says it will do it for
them does nothing.

This is not a dead listener. `UX-194` forbade controls with no handler
and a guard checks for them; this control has a handler, the handler
runs, and it changes nothing. That is the same defect with a passing
guard.

### "Copy 11 rows" acknowledges nothing

Of the four copy controls, three change their own label on success:

```text
copy-step   "Copy command"  -> "✓ copied"   (decision.js, views.js)
copy-sql    label changes                    (questions.js)
copy-view   label changes                    (app.js)
copy-rows   nothing                          (structured.js)
```

`copy-rows` is the most numerous of them — 13 on `golden`, 23 on
`macro_micro` — and a clipboard write is invisible by construction. The
control that most needs to say it fired is the one that says nothing.

## Required Fix

Two clauses, one rule (styleguide §4c):

1. **"Expand all" expands what the page folds.** The control acts on
   the layer the reader is looking at — today the chapter, and the
   sections under it. `toc(…, { controls })` receives the section
   controls only; it needs the chapter fold as well, and the two
   halves must stay symmetric: whatever "Collapse all" shuts, "Expand
   all" opens.
2. **`copy-rows` acknowledges the press**, in the shape the other
   three already use — the label becomes "✓ copied" for ~1.2 s and
   returns. `UX-279` made every copy control say *what* it copies;
   this makes it say *that it did*.

## Out of Scope

- The other ten control classes. They were measured and they work:
  `describe`, `collapse`, `json-toggle`, `copy-sql`, `copy-step`,
  `copy-view`, `chapter-open`, `select.top-n`, `details > summary`,
  `nav a[data-toc]`. Their *number* is `UX-356`'s and `UX-360`'s
  problem, not their behaviour.
- The Perfetto button, which renders on no committed fixture — that is
  `UX-358`.
- Remembering the fold across loads. `collapsible` already writes to
  storage and the chapter fold does not; harmonising the two is a
  larger question than this item.

## Acceptance Test

Booted, on both fixtures, from the landed state: clicking "Expand all"
opens every chapter and every section, and the page's height equals
the height reached by opening every chapter by hand. Clicking
"Collapse all" then "Expand all" returns to that same height. And
every control that writes to the clipboard changes its own text within
one frame of the press — asserted over the *class* of copy controls,
so a fifth one added later is covered without an edit.

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured

```text
=== golden
  landed                                     height   3548  ... chapters decide:true change:false time:false ...
  after Expand all                           height   3548  ... chapters decide:true change:false time:false ...
  after opening every chapter by hand        height  13844  ... chapters decide:true change:true  time:true  ...
=== macro_micro
  landed                                     height   5588
  after Expand all                           height   5588
  after opening every chapter by hand        height  24689
```

### After

```text
=== golden
  landed                                     height   3548  ... decide:true change:false ...
  after Expand all                           height  13844  ... decide:true change:true time:true machine:true
                                                                elements:true believe:true run:true
  after opening every chapter by hand        height  13844
=== macro_micro
  landed                                     height   5588
  after Expand all                           height  24689
  after opening every chapter by hand        height  24689
```

One press now reaches exactly what a reader reaches by opening every
chapter herself, on both fixtures.

### The fold layer is injected, not imported

`collapsible` takes `enclosing`, a `(open) => …` for the fold layer
outside the sections; `app.js` passes `chapters.setAllOpen`. Injected
rather than imported so `nav.js` keeps knowing only about sections, and
so `all()` is the one place both layers are named — which is the whole
of what went wrong, a control that named "all" and drove one of two.

`all()` opens the enclosing layer *before* the sections and shuts it
*after* them, so a section is never told to open while the chapter
holding it is folded.

**The decision chapter is skipped, deliberately.** `setAllOpen` walks
only chapters that have a toggle. The first one does not, because
`UX-347` decided the verdict stays open — "a reader who has to open the
verdict has been handed nothing" — and shutting it from the rail would
make a fold with no way back. Mutation P3 removed that guard and
reddened six clauses, which is the shape of the trade being refused.

### The copy says it fired, and comes back to what it says

`copy-rows` now shows `✓ copied` for 1.2 s. The restore goes through
`label`, not a captured string: the label carries a live count (`Copy
11 rows`) that the filter, the threshold, the sort and the bound all
move, so what it should say on the way back is whatever it would say
now. `TestTheAcknowledgementGoesBackToWhatItSays` is that clause, and
mutation P5 — acknowledge but never restore — reddens only it.

The guard's population is the **class**: every `button` whose class
begins `copy` is pressed and its own text watched. A fifth copy control
added later is covered without an edit.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `71300af`.

| # | mutation | reddened |
|---|---|---|
| P1 | `enclosing` dropped — "Expand all" drives only sections again, the defect itself | 4: both `test_one_press_opens_the_document` and both `test_the_pair_is_symmetric` |
| P2 | only Expand drives the chapters; Collapse leaves them open | 2: `test_collapse_all_shuts_both_layers`, both fixtures |
| P3 | `setAllOpen` stops skipping the toggle-less chapter | 6, including both `test_the_decision_chapter_never_shuts` |
| P4 | `copy-rows` goes silent again | 4: `test_no_copy_control_is_silent` and the restore clause, both fixtures |
| P5 | it acknowledges and never restores | 2: `test_the_label_comes_back` only |

P2 is the one that makes this a rule rather than a fix. A change that
only taught "Expand all" the chapter layer would pass the first clause
and leave a reader who pressed "Collapse all" first looking at a folded
page with a control that says it will open everything.

### Deviation from the Required Fix

- The Required Fix said "whatever 'Collapse all' shuts, 'Expand all'
  opens". Implemented as both halves driving both layers, which is the
  same property from the other side and is what `test_the_pair_is_
  symmetric` actually asserts (collapse-then-expand returns to the
  expanded state, field for field).
- The Out of Scope entry about remembering the fold across loads
  stands: `collapsible` writes its section state to storage and
  `setAllOpen` does not write the chapter state. A reader who collapses
  everything, reloads, and finds the chapters back is a real friction
  and it is a different item — the two layers disagreeing about memory
  is a question about `viewstate`, not about a label naming its scope.
