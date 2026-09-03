# UX-592: two rail harnesses press before the mark they depend on

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-393 (the stepper), UX-399 (the mark), UX-359 (the guard that measures a different reader) | **Serves:** every session reading a red CI job on a branch that changed nothing | **Topic:** guards

## Motivation

`test (3.11)` red on round 83's branch at `5b4c05f`, on two clauses
the branch does not touch — `git diff $(git merge-base origin/main
HEAD)..HEAD -- tests/unit/test_the_rail_takes_a_step.py bga/viewer/nav.js
bga/viewer/sections.js bga/viewer/app.js` is empty, and the base
`b100beb` is green:

```text
FAILURE …test_next_walks_the_order_the_page_declares
        AssertionError: ['#decision', '#readers', '#evidence', '#overview', '#findings', '#headline']
FAILURE …test_previous_walks_back
        AssertionError: ['#findings', '#overview']
```

Both are the declared order shifted one earlier. `nav.js:567` says
why, and says it on purpose:

```text
// From nowhere, `next` is the first and `previous` is the last:
// the ends of the order, not an error.
const to = cursor < 0 ? (by > 0 ? 0 : all.length - 1) : cursor + by;
```

`_WALK` and `_KEYS` press without waiting for `data-current`, which
an `IntersectionObserver` writes on a later task. When the mark has
not landed, `cursor` is `-1` and the first press spends itself
reaching section 0 — so the whole walk is one short. **The code is
right and the harnesses are racy**, which is the reverse of what the
job reports. The from-nowhere branch itself has no guard at all.

## Required Fix

Both scripts wait for the mark before their first press, and the walk
reports whether it arrived so a page that never marks cannot pass
quietly. The from-nowhere branch gets its own guard, on a page whose
marks are stripped synchronously — deterministic, because the cursor
only moves on a press.

## Out of Scope

- Changing `stepper` — declined: the from-nowhere rule is argued in
  `UX-393` and the reader it serves is real; this item guards it.
- The junit namer that reported these (`UX-589`) — a separate row.

## Acceptance Test

The pre-fix values reproduce on demand by stripping the marks;
mutation: poll for an attribute nothing writes — the walk's vacuity
clause reds; `next` from nowhere becomes the *second* section — the
new guard reds.

## Outcome (round 83, 2026-09-03) — 🟢 Done

**The gap, reproduced on demand.** Stripping the marks synchronously
puts the page in the state CI's loaded runner reached on its own, and
gives back CI's two values exactly:

```text
expected forward (order[1:7]): ['#readers', '#evidence', '#overview', '#findings', '#headline', '#next_steps']
observed forward            : ['#decision', '#readers', '#evidence', '#overview', '#findings', '#headline']
expected back               : ['#headline', '#findings']
observed back               : ['#findings', '#overview']
```

Both match `test (3.11)` on `5b4c05f` character for character, which
is what settles the diagnosis: not a defect in the order, the
from-nowhere rule reached by a press that arrived too early.

**A second harness had it too, and only a rate found it.**
`_KEYS` sends `]` twice and reads the hash; under load its first `]`
was also spent on the from-nowhere rule:

```text
E   AssertionError: {'afterTwo': '#readers', 'afterBack': '#decision', 'whileTyping': '#decision'}
E   assert '#readers' == '#evidence'
```

Before the fix, over the runs that included it: **2 red in 19**
(load 5-18). After both waits: **0 red in 20** at load 28.75, and
0 red in 24 earlier runs. A rate, not a mutation - said plainly,
because a race has no deterministic mutation and pretending
otherwise is the shape this repository keeps catching.

**Mutations verified red and reverted (2):**

| mutation | reddened | run |
|---|---|---|
| the walk polls `data-never-written`, an attribute nothing writes | `test_the_walk_started_from_a_marked_page` | 1 failed, 12 passed |
| `nav.js:567` from-nowhere `next` becomes the *second* section | `TestTheStepFromNowhere::test_next_from_no_mark_is_the_first_section` | 1 failed, 13 passed |

The first mutation left the other twelve clauses green - the two-second
poll still elapses, so the mark lands before the presses. That is the
vacuity clause earning its place: it is the only thing that catches a
page which never marks.

**Deviation from the Required Fix:** none. `stepper` is unchanged;
only the two harnesses and the new guard.

**Tier:** `tests/tiers.py` has this file at large (8.6s, `UX-455`); it
now runs 14 tests where it ran 12, 5.8-6.9s single-process on a
loaded box. Within its tier, no row change.

**Suite:** the batch gate runs at the end of the round.
