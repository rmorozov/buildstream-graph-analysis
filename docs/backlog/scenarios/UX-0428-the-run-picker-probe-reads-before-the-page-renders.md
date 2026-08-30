# UX-428: the run-picker probe reads the page before it has rendered

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 68, a red `test (3.10)` on PR #187 that no other interpreter reproduced | **Serves:** every contributor, at the point CI reddens on something their diff cannot reach | **Topic:** guards

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

## Outcome (round 69, 2026-08-30) — 🟢 Done

### The gap, measured

```text
FAILED tests/unit/test_the_page_moves_between_runs.py::TestTheSelectorIsThere
       ::test_it_lists_the_store_s_runs
  AssertionError: the page still reaches no other run
```

`test (3.10)` on run 393 only. 3.9, 3.11 and 3.12 passed the same
commit; 3.10 passed the two runs either side; three of three locally.

### After

The probe waits — and waits for **the state it is about to read**
rather than a fixed interval: the box, its `select`, and at least one
option, which is the precondition all four clauses in the class share.
`tests/cdp.mjs` already settles 1200 ms after load, and that is the
interval this contradicts; a longer one would only move the race.

On the deadline it returns what *was* there:

```text
AssertionError: no run picker after 5000ms; the page had
  {'title': 'bga — run', 'rail': True, 'railChildren': ...}
```

`rail: True` with no picker is a different defect from no rail at all,
and the old `sections: document.title` could not tell them apart.

### Mutations verified red and reverted (3)

Counts are what the run printed, not what was expected of it.

| # | mutation | result |
|---|---|---|
| T1 | the rail is removed and put back after 1s | **4 passed** in 20.75s |
| T2 | the picker is genuinely absent | 4 failed in 26.86s |
| T3 | the rail arrives late **and** the wait is removed | 4 failed in 6.70s |

T1 and T2 are the two clauses the Acceptance Test asked for. **T3 is
the one that earns the change**: with the same late rail, removing the
wait reddens it again, so the wait is what makes T1 pass rather than
something incidental to the fixture. T1's runtime — 20.75s against a
6.76s baseline — is the wait engaging, four clauses each holding for
their own second.

```text
baseline    4 passed in 6.76s
reverted    4 passed in 6.62s
8 passed in 20.44s   (the whole file)
```

### Deviation from the Required Fix

- **None.** The Required Fix offered polling to a bounded deadline over
  a fixed `setTimeout`, and named the fixed timeout's cost — "trades
  one race for a slower one". The polling shape was taken. The
  diagnostic fields the filing asked for (`document.title`, whether
  `nav.toc` exists, its child count) are all present, plus whether the
  picker and its `select` had appeared, which distinguishes two more
  states for the same cost.
- The filing's Out of Scope holds: the fixture's 0.3s server sleep is
  untouched, and no census of other probes was attempted. `UX-425`'s
  sweep suggests there are more; that remains its own item.
