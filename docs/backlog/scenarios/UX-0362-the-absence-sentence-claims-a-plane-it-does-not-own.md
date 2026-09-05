# UX-362: the Plane 2 absence sentence claims a timeline it does not own

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-329 (the absence grammar, split), UX-358 (the fixture that found it) | **Serves:** anyone reading a Plane 1 capture's report | **Topic:** viewer | **Area:** bga

## Motivation

`UX-329` split the Plane 2 absence into three sentences so a reader
could tell a machine that never captured the plane from a complete
capture whose raw log was dropped. One of them says:

> Plane 2 was not captured for this run, so there is no per-process
> detail and no timeline. `bga snapshot -- bst build TARGET` captures
> both planes.

`UX-358` committed `tests/fixtures/with_timeline` — a real capture with
a wrapped `build.log` and **no** Plane 2 — and the contradiction
appeared on the first boot:

```text
with_timeline   has_timeline=True   #perfetto box 21px   #bga-trace present
                absence sentence rendered: NOT_CAPTURED
```

The page carries a Plane 1 timeline, renders the Perfetto button, hands
the trace over — and says, three sections away, that there is no
timeline.

**Both halves are individually right.** Plane 2 *was* not captured, and
`bga timeline` *does* render from the wrapped BuildStream log alone;
`render` treats the raw Plane 2 log as optional and returns a Plane 1
trace when it is absent. What is wrong is the sentence's scope: whether
there is a timeline is not Plane 2's fact. `UX-329` split the grammar
one level too high — it distinguished three Plane 2 states and then let
one of them speak for a Plane 1 capability.

Nothing found it for two rounds because no committed fixture had Plane
1 and not Plane 2. `golden` has neither, `macro_micro` has a Plane 2
report and no raw log, and `examples/06`'s two-plane capture is
gitignored. The state was unreachable until `UX-358` made it reachable.

## Required Fix

`NOT_CAPTURED` says what it owns and stops:

```text
Plane 2 was not captured for this run, so there is no per-process
detail. `bga snapshot -- bst build TARGET` captures both planes.
```

Whether a timeline exists is `run.has_timeline`, which the page already
reads and the handoff already acts on — so the reader is told once, by
the thing that knows.

The sentence is a **published contract string** (`UX-326`: the tool's
own sentences are contracts). It is printed by the terminal, the page
and the export from one constant in `bga/plane2.py`, and every one of
those three readers is in a run where the timeline claim is equally not
Plane 2's to make. The change is one string and the guards that quote
it.

## Out of Scope

- The other two sentences. `CAPTURED_NO_RAW_LOG` says *"the raw trace
  log it was built from was not kept, so there is no timeline to
  render"* — and that one is about the log the timeline is rendered
  from, so the claim is its own to make. `DECLINED` makes no timeline
  claim at all.
- Whether a Plane 1-only timeline is worth handing to Perfetto. It is —
  `bga timeline`'s whole Plane 1 path predates Plane 2 — and this item
  does not reopen it.
- Adding Plane 2 to `tests/fixtures/with_timeline`. The fixture is
  deliberately Plane 1 only: 64 KB against 712 KB, and `UX-189` is on
  file for what a clone should not ship. Its being Plane 1 only is what
  made this reachable.

## Acceptance Test

Booted on `tests/fixtures/with_timeline`: the page renders the Perfetto
button *and* states the Plane 2 absence, and the absence sentence makes
no claim about a timeline. Asserted as the pair, so a fix that removed
the sentence entirely — losing the honest Plane 2 half — reddens too.
`test_the_handoff_has_a_fixture.py::test_the_page_says_which_plane_is_
missing` is the clause that records today's behaviour and should move
with this.

## Outcome (round 57, 2026-08-28) — 🟢 Done

### The defect, re-measured on the current tree

Booted on all three committed captures, before the change:

```text
fixture         has_timeline  #perfetto box  #bga-trace  says "no timeline"  NOT_CAPTURED
golden                 False              0       False                True          True
macro_micro            False              0       False                True         False
with_timeline           True             21        True                True          True
```

The last row is the contradiction: a page that renders the button,
inlines the trace, and denies the timeline. The other two rows are why
the fix is not "stop saying it" — on those captures the denial is true,
and `macro_micro`'s comes from `CAPTURED_NO_RAW_LOG`, which owns its
claim because it is about the log the timeline is built from.

### The change

One string in `bga/plane2.py`, as the Required Fix said:

```text
- ...so there is no per-process detail and no timeline.
+ ...so there is no per-process detail.
```

Its comment records why the clause left, so the next person to write
"and no timeline" into it has the reason in front of them.

Three readers print it — the terminal, the page and the export — and
none needed a change: `UX-329` already made them read one constant.
The golden snapshot's `plane2_absence` field was restated to match; it
is one field of `expected_output.json` and the rest is untouched.

### The guard

`test_the_page_says_which_plane_is_missing` recorded the contradiction
as what was true; it is replaced by
`test_the_absence_is_stated_and_claims_only_its_own_plane`, which
asserts the rule. The probe now collects **every** rendered sentence
matching `no timeline`, so the claim is about the page rather than
about one constant.

Both directions, because either alone is vacuous:

- on `with_timeline` (has a timeline) no rendered sentence may deny one,
  **and** the Plane 2 absence must still be stated;
- on `golden` and `macro_micro` (no timeline) a sentence must say so —
  without this, "denies none" passes on a page that never mentions a
  timeline at all.

### Mutations

Three, against the committed tree, all reverted:

| | mutation | result |
|---|---|---|
| M1 | put `and no timeline` back — the defect itself | 1 failed |
| M2 | delete the absence sentence — the over-fix that "passes" M1 | 2 failed |
| M3 | invert `questions.js`'s `hasTimeline` branch so a *different* module denies the timeline | 1 failed |

M3 is the one that matters: the guard reddens on a denial it did not
know the source of, which is what distinguishes measuring the page from
re-asserting a constant.

### Deviation from the Required Fix

None to the fix. One addition to the work: the sweep this item should
have run — *every* sentence naming Plane 2 on the Plane-1-only page —
found the mirror image in `UX-348`'s handoff lead, which claims "Plane
2's process lanes" are in a trace that has none. It is **filed as
`UX-364`, not fixed here**, because the honest predicate is neither
`has_timeline` (this capture has one) nor `plane2_absence` (`DECLINED`
leaves the lanes in the trace) but whether the trace was built with a
Plane 2 raw log — and no published field says so. That is a contract
change, and this item's Required Fix is explicit that the change is one
string.
