# UX-358: no committed fixture can render a timeline, so the handoff the tool is for is never exercised

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-298 (the timeline speaks Perfetto), UX-299 (a handoff that carries the trace), UX-348 (the two capabilities, made visible) | **Serves:** every future round that has to believe the Perfetto handoff works | **Topic:** guards

## Motivation

`UX-348` moved the Perfetto handoff up the page, gave it a lead
sentence naming the one-trace handoff and a worked example. Round 55
went to press the button, on the page a user gets, and could not:

```text
                     #perfetto in the DOM   rendered (box height > 0)
golden                                  1                         no
macro_micro                             1                         no
```

`wireTheHandoff` returns before it wires anything, because
`export(...)` got no trace to inline:

```text
$ python3 -c "import tools.bga_view as v; print(v.trace_bytes(...))"
tests/fixtures/golden/mixed_task_kinds           trace_bytes = None
tests/fixtures/macro_micro/run                   trace_bytes = None
tests/fixtures/synthetic_multi_subproject        trace_bytes = None
```

And the reason is one missing file, which the renderer says out loud:

```text
$ render("tests/fixtures/macro_micro", ...)
FileNotFoundError: tests/fixtures/macro_micro: no build.log. This is a
snapshot directory - it has a `run/` - but `bga timeline` needs the
wrapped BuildStream log the build wrote, and this capture kept none.
```

Every fixture holds `graph.json`, `run-context.json` and `trace.json`
— Plane 1's inputs — and none holds a `build.log`. `bga timeline`
renders from the wrapped log, so it refuses; `trace_bytes` returns
`None`; `has_timeline` is false; the button never gets a box.

The consequence is not that the handoff is broken. It is that **nobody
knows**. The one capability no other BuildStream tool offers is the
only user-visible path in the report with no end-to-end exercise
anywhere in a 4,485-test suite. What every guard, screenshot and review
has seen for four rounds is the *absence* path — correct, well worded,
and the wrong half of the pair.

This is `UX-179`'s shape again: a discriminating case that was never
built, so the fixtures cannot tell "works" from "absent".

## Required Fix

A committed fixture that can render a timeline:

- a snapshot directory with a `build.log` — the smallest wrapped log
  `bga timeline` will accept — **beside** the existing three rather
  than replacing them. Both states have to be exercised: a snapshot
  with no Plane 2 log is what many real users have, and its absence
  sentence is the honest rendering of that.
- the handoff's own guard, on that fixture: `#perfetto` renders with a
  box, `has_timeline` is true, the inlined `#bga-trace` script exists,
  and the press does what the lead sentence says.
- the standing rule this generalises to — §2c's argument, applied to
  capabilities rather than sections: **a capability the page
  advertises is exercised by at least one fixture.** A capability with
  no fixture is not tested and not testable, and four rounds of
  reasoning about it from its source is what that costs.

## Out of Scope

- Shipping a large or realistic trace. The fixture wants to be the
  smallest wrapped log that makes `render` succeed; a realistic
  capture belongs in `docs/audits/data/`, not `tests/fixtures/`.
- Fetching `trace_processor` in CI. That seam was settled in round 44
  — the real binary is fetched in one place, not on every run. This
  item needs the *page's* half.
- The lead sentence, the worked example and the fallback wording,
  which `UX-348` landed and which are correct. They are simply unread
  by any fixture.
- `bga timeline`'s refusal message. Declined because it is already
  right: it names the missing file and the directory shape it wanted,
  which is why this item could be diagnosed in one command, and it is
  quoted above as the example rather than the defect.

## Acceptance Test

On the new fixture: `trace_bytes` is not `None`, `has_timeline` is
true, and the booted export renders `#perfetto` with a non-zero box.
On the three existing fixtures: `has_timeline` is false, the button
does not render, and the Plane 2 absence sentence does — asserted as a
**pair** in one guard, so a change that made the button render
unconditionally reddens rather than passing the first clause.
