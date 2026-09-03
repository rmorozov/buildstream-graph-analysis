# UX-555: `--no-trace` tells a two-plane run it kept no Plane 2 log

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** `UX-545` (which fixed the branch beside this one) | **Found by:** `UX-545`'s track, one branch over from its own fix | **Serves:** anyone who exports without a timeline on purpose | **Topic:** viewer

## Motivation

`tools/bga_view.py:1203` is the fallback for "no timeline in this
file". It reads `plane2.absence() or "this run kept no raw Plane 2
log, so there is no timeline to carry"`.

For a complete two-plane run exported with `with_trace=False`,
`plane2.absence()` returns `None` — there is no absence to describe —
and the `or` swallows it into a sentence that is simply false: the run
*did* keep a raw Plane 2 log, and the reason there is no timeline is
that the caller asked for none.

This is `UX-545`'s shape exactly, one branch over: an absence
described as a *different* absence. `UX-545` fixed the refusal path,
where two states shared one key; this is the third state sharing it.

## Out of Scope

- `UX-545`'s refusal path, which is closed: this row is only the
  `with_trace=False` branch beside it.
- Making `--no-trace` reachable from more callers: declined, because
  the sentence is wrong whether or not a caller reaches it, and
  widening the surface is a separate question from telling the truth
  on it.

## Required Fix

The three states are distinguished, and each says its own reason:
the caller asked for no trace, the run has no Plane 2 to draw, and
the timeline was refused for its size. A mutation swapping any two
must redden.

## Acceptance Test

`export(run, path, with_trace=False)` over
`tests/fixtures/with_timeline` — a run that demonstrably *has* a raw
Plane 2 log — and the published sentence names the flag rather than
the run.

## Note on reachability

No caller in `bga/` passes `with_trace=False` today, so the sentence
is unreachable outside tests. That is why this is Low and not Medium,
and it is also why it survived: `UX-326`'s axis reads what the tool
prints, and nothing prints this.
