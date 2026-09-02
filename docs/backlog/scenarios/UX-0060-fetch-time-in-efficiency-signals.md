# UX-60: whether `FETCH` time belongs in any efficiency signal has been deferred by two separate tasks and never decided

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-53` (done — which made the duration definition single, and made this the remaining question) | **Topic:** analysis

## Motivation

Two tasks have now stopped at the same line and declined to cross it.

`UX-50`, Out of Scope:

> Whether `FETCH` time should appear in *any* efficiency signal, which is
> a separate question this task should not silently settle.

`UX-53`, Out of Scope, having just unified the per-element duration to
"the longest task the element ran":

> Whether a FETCH should contribute to a *build* chain's floor **at all**.
> The most faithful model of "unlimited relevant capacity" is that every
> fetch starts at t=0 and only BUILD durations accumulate along the
> chain, which would make `T∞,observed` a BUILD-only longest path.

Both were right to defer: it changes a spec-published number (Part 14.1)
and is a modelling decision rather than a defect. But it is now the only
thing standing between `T∞,observed` and a definition that can be
defended from first principles rather than from "the maximum is at least
safe".

## Why it matters more after `UX-53` than before

`UX-53` chose the maximum because a floor must never overstate, and an
element genuinely occupies at least its longest task. That reasoning is
sound and it is also *provisional*: it justifies the choice as safe, not
as correct. On an element whose FETCH outlasts its BUILD — a large
tarball over a slow link — the "structural floor of the build" currently
includes a download.

The three candidate definitions and what each would mean:

| definition | `T∞` says | risk |
|---|---|---|
| max over tasks (today) | an element occupies at least its longest task | a long FETCH inflates a *build* chain |
| sum over tasks | fetch then build, sequentially | overstates: fetches overlap other elements' builds, so a real schedule can beat it — invalid for a certified floor |
| BUILD only | the chain of actual build work | may violate `I3` (`T∞ >= max(observed task duration)`) when a FETCH is the longest task in the run |

That third row is the crux, and it is also why **`I3` should be
implemented as part of this** — `UX-53` recorded that it appears nowhere
in `bga/validation/invariants.py`. Under today's definition it holds
trivially; under the one that is arguably most correct it is exactly the
check that would catch a bad choice.

## Required Fix

1. Decide, with the spec's own words as the test: "no schedule with
   unlimited relevant capacity can complete faster than this value."
   Whichever definition survives that sentence wins.
2. Implement `I3` regardless of which does.
3. Whatever changes, `structural.sensitivity.critical_path_us` and
   `floors.t_infinity_observed` must stay equal — `UX-53` made that hold
   by construction and it must not regress.

## Out of Scope

- `LB` and the capacity floor, which are about resource totals rather
  than chain composition.
- Attribution's treatment of FETCH time, which is a horizon question
  (`I4`) and independent of the floor's definition.

## Acceptance Test

1. A fixture where one element's FETCH is longer than its BUILD produces
   a defensible `T∞` under the chosen definition, and the doc states why.
2. `I3` is implemented and green on every fixture.
3. `sensitivity.critical_path_us == t_infinity_observed` still holds
   everywhere, including on the real capture.

## `I3` Implemented

`T∞,observed >= max(observed task duration)` is now checked, emitting a
`floor_below_longest_task` violation. It holds trivially under the
current definition — the per-element duration *is* the longest task, and
the chain contains that element — and that is exactly why it was worth
implementing: it is the guard that would catch a future definition which
stops holding, which is precisely what `UX-53` changed with nothing
watching. Filed as a violation rather than a hard gate so a capture with
no tasks cannot fail an invariant about its own measurements.

Tests: 10 new, shared with `UX-62` (`tests/unit/test_i3_and_span_status.py`).

## The decision, derived — and why it is not yet applied

Running the spec's own sentence — *"no schedule with unlimited relevant
capacity can complete faster than this value"* — against the three
candidates gives an answer none of them is.

Under **unlimited relevant capacity**, a BuildStream fetch depends on
nothing: sources are fetched independently of any dependency's build. So
every FETCH starts at t=0. But an element cannot build before its *own*
sources are fetched. Therefore:

```text
build_start(E) = max( fetch_duration(E), max over deps D of finish(D) )
finish(E)      = build_start(E) + build_duration(E)
```

This is a genuine lower bound — E's build cannot begin before its own
fetch completes, nor before its dependencies are ready, and the second
term is recursively a lower bound — and it is *faithful* rather than
merely safe:

- when a fetch is shorter than the dependency chain's arrival time (the
  normal case) it contributes **nothing**, because it really did overlap;
- when an element has a long fetch and no dependencies, the chain really
  is fetch-then-build;
- `I3` holds either way: if the longest observed task is a FETCH, that
  element's own chain is at least `fetch + build >= fetch`.

Against the three candidates this task listed: `max` is safe but charges
a long fetch to a build chain it did not delay; `sum` overstates and is
invalid for a certified floor; `BUILD`-only understates and can violate
`I3`. The two-stage model is the one the spec's sentence actually
implies.

**Why it was not implemented when it was decided.** It cannot be
expressed as one number per element, which is the shape
`compute_element_durations` — and every consumer of it — is built
around. It needs per-element durations split by task kind and a change
inside `compute_critical_path`, and it moves a *certified* floor. That
deserved its own verification pass against real captures rather than a
tail-end edit to a commit about something else. `I3` went in first,
which is the check that made attempting it safe. The pass is below.

## The decision, applied

The two-stage model is in `compute_element_stage_durations` +
`compute_critical_path(..., head_durations=...)`, wired at
`analyze_graph` - the one place that computes the chain - so every
figure derived from it moves together.

`head` is FETCH, the stage that waits on nothing; `work` is the longest
of everything else, which keeps `UX-53`'s collapse for the part where it
applies. **An element with no FETCH gets `(0, today's number)`**, which
is why this could be introduced without moving a published floor on any
real capture: verified after the change, the freedesktop-sdk capture
still reads `T∞ = 3401.9s` and `examples/06` still reads `28.2s`,
because in both every fetch is either absent or zero-length.

On the one checked-in fixture with real FETCH durations,
`synthetic_multi_subproject`, the floor moves 118s → 122s. The four
seconds are `libcore.bst`'s own fetch: it fetches for 4s and builds for
8s with nothing above it, so its build genuinely cannot start until its
sources have arrived, and the chain is `4+8 → 35 → 35 → 40`. The old
number took the longest *task* per element (8s) - safe, and charging
nothing for an ordering that really happened.

`sensitivity.critical_path_us == t_infinity_observed` still holds, and
keeping it held was not free: the two figures come from two different
traversals (`compute_critical_path` and `StructuralAnalyzer.
_longest_path_us`), so the model had to be threaded into both. A model
applied to one of them is `UX-52` again.

### What applying it found: the replay was under-constrained

The moment the floor modelled fetch-before-build, the same fixture
reported:

```text
Model score reduced: T_C (118000000) < LB (122000000)
```

The replay could still finish in 118s because **a BUILD task carried no
dependency on its own element's FETCH**. `clamp_task_starts` built each
BUILD's edges from the graph's `depends:` entries - its *dependencies'*
builds - and nothing said an element must fetch its own sources first,
so replay was free to start any build at t=0.

That function's own comment had warned about exactly this class of
error:

> getting it wrong under-constrains replay's readiness gating, which can
> under-schedule the replay makespan `T_C` below the certified `LB`,
> violating `I2`

It was invisible for as long as no floor modelled the ordering either -
two models agreeing because both omitted the same constraint. The floor
disagreeing is what surfaced it. BuildStream cannot run build commands
before an element's sources are staged, so the edge is real and the
replay was wrong: a BUILD task now depends on its own FETCH, and
`T_C ≥ LB` again.

### The acceptance

1. A fetch longer than its own build produces a defensible `T∞` - it
   precedes the build rather than replacing it, and does not accumulate
   down the chain the way a `sum` collapse would (`4+8 → …`, pinned in
   `tests/unit/test_fetch_in_the_floor.py`).
2. `I3` was implemented first, before the definition moved - which is
   the order that makes the move safe, and it is green on every fixture.
3. `sensitivity.critical_path_us == t_infinity_observed` everywhere,
   including on the real freedesktop-sdk capture.

Tests: 7 new in `tests/unit/test_fetch_in_the_floor.py`. Suite: 1316 →
1323.

## Verification Log

Filed 2026-08-17. Both deferrals are quoted verbatim from the Out of
Scope sections of `UX-50` and `UX-53`. The absence of `I3` was confirmed
by grepping `bga/` for it, which returns nothing.

Applied 2026-08-18. The two real captures were re-analyzed after the
change and are unchanged (3401.9s and 28.2s), which is the evidence that
the move is confined to elements that really do fetch before they build.
The replay under-constraint was found by the change rather than looked
for: it announced itself as `T_C (118000000) < LB (122000000)` on the
first fixture with real FETCH durations.
