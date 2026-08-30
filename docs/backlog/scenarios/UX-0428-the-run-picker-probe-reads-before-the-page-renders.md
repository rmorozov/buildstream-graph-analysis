# UX-428: the run-picker probe reads the page before it has rendered

**Priority:** Medium | **Status:** 🔴 Not Started | **Found by:** round 68, a red `test (3.10)` on PR #187 that no other interpreter reproduced | **Serves:** every contributor, at the point CI reddens on something their diff cannot reach | **Topic:** guards

## Motivation

```text
FAILED tests/unit/test_the_page_moves_between_runs.py::TestTheSelectorIsThere
       ::test_it_lists_the_store_s_runs
  AssertionError: the page still reaches no other run
```

`test (3.10)` only, on run 393 (`e8124b7`). 3.9, 3.11 and 3.12 passed the
same code on the same commit; 3.10 passed it on runs 391 and 392. It
passes three times out of three locally, and PR #187 touches nothing
this file reads.

The probe is synchronous:

```javascript
_PICKER = """(() => {
  const box = document.querySelector("nav.toc .run-picker");
  if (!box) return { found: false, sections: document.title };
```

and its fixture serves the page, sleeps 0.3s for the **server**, and
measures immediately. Nothing waits for the **page**. Every other
browser probe in this suite that reads rendered structure waits first —
`test_the_rail_marks_the_section_the_reader_scrolled_to` opens with
`const wait = () => new Promise((r) => setTimeout(r, 300)); await
wait();`. This one does not, so on a runner slow enough that `boot()`
has not built the rail yet, `box` is null and the clause reports the
page "reaches no other run".

**It is this round's own subject in a different place**: an instrument
reading at a moment that does not represent the thing it names. The
number it returns is real — there genuinely was no picker at that
instant — but what it is a fact *about* is the scheduler, not the page.

`found: false` also loses the evidence. The failure message says the
page reaches no other run; it cannot say whether the rail was absent,
empty, or simply not built yet.

## Required Fix

- **Wait for the element rather than assume it.** Poll for
  `nav.toc .run-picker` up to a bounded deadline and only then read it —
  a fixed `setTimeout` matches the file's neighbours but trades one race
  for a slower one.
- **Say which failure it was.** On the deadline, return what *is* there
  (`document.title`, whether `nav.toc` exists, its child count) so the
  next red build distinguishes "not rendered yet" from "not rendered at
  all". The current `sections: document.title` is a start that nothing
  asserts on.
- The other three clauses in the class share the fixture and the probe,
  so fixing `_PICKER` fixes all four.

## Out of Scope

- **Re-running CI to make it green**: that is the response this item
  exists to stop. The clause is right that a missing picker is a defect;
  it is wrong about when to look.
- **The 0.3s server sleep** in the fixture — a separate race, and one
  that has not been observed failing. Worth a row of its own if it ever
  does.
- **Auditing every browser probe for the same shape**: `UX-425`'s sweep
  suggests there will be more, and a census is its own item rather than
  a thing to do while fixing one.

## Acceptance Test

- The clause passes with the page's rail injected after an artificial
  1s delay, and fails when the picker is genuinely absent from the
  document — both on the real fixture.
- The failure message names what was present at the deadline.
