# UX-362: the Plane 2 absence sentence claims a timeline it does not own

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-329 (the absence grammar, split), UX-358 (the fixture that found it) | **Serves:** anyone reading a Plane 1 capture's report | **Topic:** viewer

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
