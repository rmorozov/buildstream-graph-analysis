# UX-355: a fold that expands nothing, and a copy that says nothing

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-347 (chapters fold), UX-279 (a copy control says what it copies) | **Serves:** anyone who lands on the report and tries to open it | **Topic:** viewer

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
