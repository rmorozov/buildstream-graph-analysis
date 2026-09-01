# UX-482: the browser harness waited a duration where it meant a condition

**Priority:** Medium | **Status:** 🟢 Done | **Found by:** round 73, PR #191 — a store guard reported 40 sections on its first boot and 47 on its second, in one run, on both interpreters | **Serves:** the contributor whose PR is red on a page the tool renders correctly | **Topic:** guards

## Motivation

`tests/cdp.mjs` navigated and then slept:

```javascript
await send("Page.navigate", { url });
// The page is one file with inlined payloads and no network, so a fixed
// settle is enough and a load-event race is not worth the machinery.
await new Promise((resolve) => setTimeout(resolve, 1200));
```

That reasoning is about the *network*, and the thing being waited for is
the *render*. A fixed 1,200ms is a duration standing in for a condition
— fixing guide §5, in the harness rather than in a finding — and on a
loaded two-core runner it lost:

```text
tests/unit/test_one_bad_row_costs_one_section.py:237:
    assert booted["damaged"]["value"]["sections"] == \
E   AssertionError: ({... 'sections': 47}, {... 'sections': 40})
E   assert 47 == 40
```

Run 33504066746, on `test (3.9)` and `test (3.11)` both. The shape of
the numbers is the diagnosis: the **damaged** boot counted *more*
sections than the healthy one, and damage cannot add sections. What
differs between them is only order — `booted` boots healthy first, on a
browser that has just started, and damaged second, on a warm one. A
first boot observed mid-render counts a prefix of the page.

## Required Fix

Wait for the condition: the rendered size of `#report` has stopped
changing. Keep the old 1,200ms as a **floor**, so nothing observes
earlier than it used to and no existing guard can be made flakier by
this change; add a ceiling so a page that never settles fails on its
own assertion rather than hanging the driver.

## Out of Scope

- **A load event or a page-published "ready" marker.** Either would be
  better still, and both need the page to cooperate — a marker is a
  contract the exported report would have to carry, which is a change
  to the artifact rather than to the harness. The stability poll needs
  nothing from the page and is strictly closer to the condition than a
  constant is.
- **`tests/browser.py`'s launcher.** `UX-456` part one fixed the port
  race and the silent error there; this is the other end, after the
  browser is up and the page is loading.
- **Reducing what the suite runs concurrently** — declined, because the
  harness should be correct under load rather than protected from it,
  and a suite tuned to keep one race quiet would hide the next one.

## Acceptance Test

```bash
python3 -m pytest tests/unit/test_one_bad_row_costs_one_section.py -q
```

green, and the driver contains no bare `setTimeout` standing alone as
the wait between navigation and evaluation.

## Outcome

**Round 73 · 2026-09-01 · Status: 🟢 Done — with the causal claim stated as unconfirmed, because it is**

### What changed

`tests/cdp.mjs` polls `document.getElementById("report").innerHTML.length`
every 150ms after the old 1,200ms floor and stops on two equal samples,
with a 20s ceiling. Three constants, each named:

```javascript
const SETTLE_FLOOR_MS = 1200;
const SETTLE_STEP_MS = 150;
const SETTLE_CEILING_MS = 20000;
```

Because the floor is unchanged, the observation can only happen **later**
than it used to, never earlier — so no guard that passed before can be
made to fail by this.

```console
$ python3 -m pytest tests/unit/test_one_bad_row_costs_one_section.py -q
12 passed in 11.27s
```

### What I could not show, and am not claiming

The honest part. I tried to reproduce the CI failure locally under
saturation — twelve busy loops on four cores — and ran the clause with
the fix and with the old fixed settle restored:

```text
with the fix,    12x CPU load    1 passed, 11 deselected in 7.49s
without the fix, the same load   1 passed, 11 deselected in 6.82s
```

**Neither reproduced it.** So the claim that this change fixes that
failure is an inference from the mechanism and from the shape of the
numbers (first boot low, second boot complete, damage cannot add
sections), not a measurement. What is measured is that the wait is now
the condition rather than a constant, and that the floor makes the
change one-directional.

The other half of the honesty: the failure did **not** recur on the
next commit (`fe89e0a`, run 33505406758), where the suite passed and
only the drift gate failed. So it is intermittent, and one green run
after this change would not confirm anything either. CI over several
runs is the only instrument that can settle it, and this row is closed
on the mechanism rather than on a green.

### No new guard

Deliberate, and it is the `falsify` skill's own test applied
honestly: a guard here would assert that `cdp.mjs` contains a poll,
which is reading the source for the property rather than exercising it,
and a guard that reproduced the race would be the reproduction I could
not build. The acceptance test above is the existing clause, and the
existing clause is what reddened.

### Deviation from the Required Fix

None.

### Verification

```text
make lint                  clean
dev_close_task.py --check  0 problems
make test                  5604 passed, 27 skipped in 313.35s
```
