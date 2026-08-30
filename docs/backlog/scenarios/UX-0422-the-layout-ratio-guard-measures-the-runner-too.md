# UX-422: the layout-cost guard measures the runner as well as the page

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 66, a red `test (3.12)` on PR #183 | **Serves:** every contributor, at the point CI tells them something is wrong | **Topic:** guards

## Motivation

`test_the_browser_is_the_library.py::test_the_layout_cost_stops_tracking_the_document`
holds a real property: `content-visibility` means a reflow costs
something bounded by what is on screen rather than by the whole
document. It holds it as a **ratio**, deliberately — its own comment
says *"the number is the machine's, the property is the page's"*:

```python
assert seen["on"] < seen["off"] / 2
```

A ratio is the right instinct and this shape of it does not survive a
loaded runner. It went red on CI at 15.4 ms with `content-visibility`
against 28.6 ms without — a 1.86x saving where 2x is required — on
`macro_micro`, a fixture that had not changed. Measured on a developer
container, six runs, three idle and three under eight CPU spinners:

```text
                on      off    ratio
idle           3.0     19.6     6.53
               2.9     17.9     6.17
               2.8     18.0     6.43
loaded         2.9     18.4     6.34
               2.8     16.8     6.00
               3.0     17.8     5.93
CI, 3.12      15.4     28.6     1.86
```

**The two numbers moved by different factors**, which is the whole
finding: `on` is 5x its local value and `off` only 1.6x. That is the
signature of a *fixed additive overhead* on each measurement — a
scheduler delay between `performance.now()` and the forced reflow —
rather than of a slower machine, which would scale both. Subtract
about 12.5 ms from each of CI's figures and you get 2.9 and 16.1: the
local numbers exactly.

A ratio is invariant under a multiplicative change and not under an
additive one, and the smaller operand is the one an additive term
swamps. So the guard, whose job is to prove that `on` is small, fails
precisely when the harness makes small things unmeasurable.

Three of four interpreters passed this test on the same commit, and it
passes six times out of six locally. Nothing about the page changed.

## Required Fix

Make the measurement measure the page:

- **Subtract a floor.** The probe already forces a reflow 25 times and
  takes the median; a third measurement of a reflow that does no layout
  work at all gives the harness overhead, and both operands minus that
  floor is a ratio of layout costs. This is the smallest change and the
  one the numbers above argue for.
- **Or assert the saving, not the ratio** — `off - on` against a floor
  scaled by node count. An additive term cancels in a difference.
  Weaker as a claim, and it re-introduces a machine-dependent number,
  which is what the ratio was avoiding.
- **Or refuse to judge when the floor is high**, skipping with a reason
  that names the measured overhead. Honest, and it means the property
  goes unchecked on exactly the runs where a regression would be
  cheapest to catch.

Whichever is chosen, the test should fail on a page that genuinely lost
`content-visibility` *while the overhead is high* — that is the case
worth building, and the numbers above are the ones to replay.

## Out of Scope

- Relaxing the 2x threshold. The local ratio is 5.9-6.5x, so a page
  that lost the property would still be well under any threshold worth
  having; moving it to 1.5x would be quarantining the guard rather than
  fixing it, and would not survive the next slower runner either.
- The other browser guards in the file. They assert structure, not
  time, and are not exposed to this.

## Acceptance Test

- The clause passes with 12.5 ms of synthetic overhead added to every
  reflow measurement, on the real fixture.
- With `content-visibility` removed from the stylesheet it fails, both
  with that overhead and without it.

## Outcome (round 68, 2026-08-30) — 🟢 Done

### Option 1 was tried first, and the measurement refused it

The filing recommended subtracting a floor: *"a third measurement of a
reflow that does no layout work at all gives the harness overhead"*.
That probe was built — the same 25-iteration median loop with the
invalidating write removed, so `offsetHeight` is served from cache and
no layout runs. It reads **0.00 ms**, five runs idle and five runs
under eight CPU spinners on a four-core container:

```text
   floor       on      off   on-net  off-net    raw     net
    0.00     2.90    16.50     2.90    16.50   5.69    5.69
    0.00     3.00    16.50     3.00    16.50   5.50    5.50
    0.00     3.00    16.50     3.00    16.50   5.50    5.50
    0.00     3.00    16.10     3.00    16.10   5.37    5.37
    0.00     2.80    16.20     2.80    16.20   5.79    5.79
                                   ... 8 spinners on 4 CPUs ...
    0.00     2.90    16.00     2.90    16.00   5.52    5.52
    0.00     3.20    18.20     3.20    18.20   5.69    5.69
```

**The CI condition did not reproduce**, and the floor probe does not
see the term that caused it. Shipping option 1 would have shipped an
instrument that reads zero everywhere it can be checked and is unproven
where it matters — which is this round's own defect class.

### Option 2, and why the filing's assessment of it was backwards

The filing called it *"weaker as a claim, and it re-introduces a
machine-dependent number"*. The measurement says the opposite: the
saving is the quantity that **agrees across machines**, and the ratio
is the one that does not.

```text
      on     off    ratio   off - on
    15.4    28.6     1.86     13.2     CI, the red run
     3.0    16.5     5.50     13.5     here, idle
     2.9    16.6     5.72     13.7     here, under load
```

The ratio spans 1.86 to 5.72. The saving spans 13.2 to 13.7 — a 4%
spread across two machines and a 5x difference in `on`. An additive
term cancels in a difference, which is exactly the property needed.

So the clause is now `off - on >= LAYOUT_SAVING_FLOOR_MS`, with the
floor at **4.5 ms** — a third of the smallest saving either machine
produced. It is an absolute quantity in milliseconds, so `UX-420`'s
rule (*require a magnitude, not only a ratio*) is satisfied by
construction rather than bolted on.

### Mutations: the filing's acceptance test, run as written

| # | mutation | result |
|---|---|---|
| Q1 | 12.5 ms of synthetic overhead on **both** measurements | **1 passed** |
| Q2 | the page loses `content-visibility` (`off` = `on`) | 1 failed |
| Q3 | ...and with the 12.5 ms overhead as well | 1 failed |
| Q4 | the **old ratio rule** restored, with the overhead | 1 failed |

Q1 and Q2/Q3 are the two clauses the Acceptance Test asked for, and
they hold. **Q4 is the one that earns the change**: the same overhead
that the new rule shrugs off still reddens the rule it replaced, on the
same fixture in the same browser. Without Q4 this would be a rewrite
that might have been a rename.

```text
baseline    1 passed in 2.55s
reverted    1 passed in 2.46s
```

### Deviation from the Required Fix

- **Option 1 was not shipped**, though it was the option the filing's
  numbers argued for. It could not be validated: its probe reads 0.00
  on the only machine available, so it would have been an unfalsifiable
  fix. Recorded rather than quietly substituted.
- **Option 3 (refuse to judge when the floor is high) was not built.**
  With the floor unmeasurable here there is nothing to condition on,
  and the filing itself notes it would leave the property unchecked on
  exactly the runs where a regression is cheapest to catch.
- **The additive-term hypothesis is still one observation.** The CI run
  is the only place it has been seen, and eight spinners on four cores
  did not reproduce it. The fix does not depend on the mechanism being
  right — it depends on the saving being stable, which is measured on
  two machines — but the mechanism is not established, and a later
  round should not read this file as if it were.
