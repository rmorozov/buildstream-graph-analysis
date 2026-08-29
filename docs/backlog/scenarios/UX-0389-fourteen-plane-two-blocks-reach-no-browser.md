# UX-389: fourteen of twenty-five Plane 2 blocks reach no browser

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-383 (Plane 2's per-element blocks reach the page), UX-386 (`plane2/v3` is described as what it is), UX-382 (the element placement rule), UX-329 (the terminal and the viewer disagree about Plane 2) | **Serves:** anyone asking in a browser whether the instrument saw everything | **Topic:** viewer

## Motivation

The user asked, in as many words, whether all the captured data is
really accessible through `bga view` or Perfetto. Counted against a
real all-planes capture of `examples/06-macro-micro-optimization`:

```text
plane2 blocks in the capture            25
  a key in analyze/v4                    6
  reaching the page through the join     6
  terminal only                         14
```

Six of twenty-five reach a reader in a browser. `UX-383` moved three
blocks one round ago and `UX-385` added `commands_not_observed` in the
same round, which is already the fifteenth terminal-only block — the
gap grows every time the capture learns something new, because
nothing holds the two ends together.

The fourteen are not leftovers. They are the *did the instrument see
everything* questions:

```text
static_census        which elements could be hiding a static binary
spine_policy         whether the ptrace spine ran, and why
max_concurrency      the peak parallelism the hook observed
process_count        how many processes were traced at all
wall_span_s          the window the hook was actually watching
stream_coverage      which of the two streams saw which process
```

A reader in a browser sees a per-element attribution table and has no
way to learn that the spine never ran, so the numbers under it are a
floor rather than a measurement. That is `UX-107`'s rule again, one
level up: the page cannot say "nobody could look" because the block
that knows is at a terminal.

`UX-386` established the shape these live in — 3 of 24 blocks are
keyed by element and the rest are run-level — so `UX-382`'s placement
rule already answers *where* each one goes. What is missing is the
carry from `plane2/v3` into `analyze/v4` and a guard that notices the
next block that does not make the trip.

## Required Fix

- **Every `plane2/v3` block has a declared destination.** Either a
  named key in `analyze/v4` (run-level blocks) or a field on the
  `element_join` row (per-element ones, by `UX-382`'s rule), or an
  explicit, reasoned entry saying it is terminal-only and why. The
  three states are the point: silence is what produced fourteen.
- **The coverage blocks reach the page first**, because they change
  how every other number is read: `spine_policy`, `stream_coverage`,
  `process_count`, `wall_span_s`, `static_census`, `max_concurrency`.
  They belong with the capture's own identity block, not scattered
  through the findings.
- **A guard walks `plane2/v3`'s own block list** and fails on a block
  with no destination — so the next `commands_not_observed` cannot be
  added and quietly stay at the terminal.

## Falsification

The guard above, run against the committed Plane 2 fixture: every
top-level block of `plane2/v3` resolves to a payload key, a join
field, or a declared terminal-only entry, and the declared entries are
enumerated rather than a wildcard. Today fourteen resolve to nothing.

The other direction: adding these must not publish the same population
twice (`UX-288`) and must not move a per-element block to a run-level
key. `UX-386`'s ratio — three keyed by element, the rest run-level —
is the arbiter, and it is already guarded.

## Out of Scope

- Rendering each block well. This item is about the carry and the
  guard; how `stream_coverage` should be *drawn* is `UX-396`'s
  question.
- Plane 1 blocks. The count above is Plane 2's; whether the scheduler
  log has the same gap was not measured this round.
