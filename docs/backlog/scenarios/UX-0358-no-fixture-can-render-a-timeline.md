# UX-358: no committed fixture can render a timeline, so the handoff the tool is for is never exercised

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-298 (the timeline speaks Perfetto), UX-299 (a handoff that carries the trace), UX-348 (the two capabilities, made visible) | **Serves:** every future round that has to believe the Perfetto handoff works | **Topic:** guards

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

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured — and the filing's claim, corrected

```text
                has_timeline  #perfetto box  #bga-trace  absence
golden                 False              0       False  NOT_CAPTURED
macro_micro            False              0       False  CAPTURED_NO_RAW_LOG
```

The filing said *"no committed fixture can render a timeline"*. That is
too broad, and the correction is the fix.
`examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/`
carries a **real capture** — `build.log`, `plane2.log.gz`,
`plane2.json` and its run — and has since round 46. Four guards already
read its *trace* under the name `REAL_CAPTURE`:

```text
tests/unit/test_the_arrows_say_why_now.py
tests/unit/test_the_counter_the_constant_was_waiting_for.py
tests/unit/test_the_slice_says_what_bga_knows.py
tests/unit/test_the_trace_knows_whose_build.py
```

None of them exported a **page** from it. So what was true is the
narrower claim: no fixture *used to build a page* could render a
timeline, and every page guard parametrised over the two in
`tests/fixtures/` that cannot. The capability was reachable and nobody
had reached it.

### After

```text
with_timeline           True             21        True  none
```

`tests/pages.py` names the capture `WITH_TIMELINE` and deliberately
keeps it **out of** `FIXTURES`: every guard that parametrises over
those two would add a third browser boot for a page that differs from
`macro_micro` in exactly one respect, and this exists for that one
respect.

### The pair is one file

`TestTheHandoffRendersWhereThereIsATrace` and
`TestTheAbsenceRendersWhereThereIsNone` sit together on purpose. A
change that rendered the button unconditionally satisfies every clause
of the first and reddens three of the second — which is mutation Q1,
below, and the reason the absence path is not a separate file.

`TestBothStatesAreReachable` is the rule rather than the instance: it
asserts that the committed captures reach **both** states, stated as a
set rather than by name, so a repository that lost the timeline capture
reddens on coverage rather than on a path.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `82e22ec`.

| # | mutation | reddened |
|---|---|---|
| Q1 | `has_timeline` forced true — the button renders whether or not there is a trace | 3, both `test_the_button_does_not_render` and `test_the_two_states_differ_where_it_matters` |
| Q2 | `WITH_TIMELINE` re-pointed at `macro_micro`, a capture with no `build.log` — the state before this item | 6, including `test_every_state_has_a_fixture` |
| Q3 | the export stops inlining the trace | 2: the box clause and the two-states clause |
| Q4 | `plane2.absence` returns `None` for a run that never captured | 1: `test_the_absence_is_stated_and_says_which_one[golden]` |

Q2 is the one that matters for the rule: it is not a mutation of the
page, it is a mutation of the *fixture set*, and it is the state this
repository was actually in for four rounds.

### Deviation from the Required Fix

- The Required Fix asked for "the smallest wrapped log `bga timeline`
  will accept", written for this item. **Not done, and deliberately.**
  A real capture that already exists, is already committed, and is
  already read by four guards is a better fixture than a synthetic log
  in every respect that matters: it exercises the renderer's actual
  input, and it cannot drift from what `bga snapshot` writes. Writing a
  minimal log would have been inventing a second, weaker answer to a
  question the tree had already answered.
- The Required Fix's third clause — "a capability the page advertises
  is exercised by at least one fixture" — is landed as
  `TestBothStatesAreReachable` rather than as a general walk over
  capabilities. There is no declared list of the page's capabilities to
  walk; asserting one here would have invented the register rather than
  read it. The rule is written in the style guide (§2c's argument
  applied to capabilities) and the clause holds it for the one
  capability it was filed about.
- Verifying the trace through Perfetto's own reader stays out of scope,
  as filed. `tests/trace_processor.py` gates that and round 44 settled
  where it runs.
