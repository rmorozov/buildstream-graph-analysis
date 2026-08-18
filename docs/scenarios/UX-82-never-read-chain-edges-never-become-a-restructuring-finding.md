# UX-82: the tool measures every fact of the macro fix and never states the macro fix

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-46, UX-74 (both done)

## Motivation

On `examples/06`'s baseline — the project built to be walked through a
macro-then-micro cycle — this round's real traced run gave `bga` every
fact of macro problem 1 (six libraries chained instead of fanned out):

- `analyze` prints the critical path: ten elements, `lib-a..lib-f` six
  links of it at 8.0% each, 82.6s of slot-time "had nothing ready to run
  at all - it is a dependency-graph shape problem";
- `correlate --trace-opens` reports, for **every one of the five chain
  edges**, "opened no file staged by … (lib-a.bst)" — each edge
  individually measured as never read at build time.

And the user still has to invent the fix themselves. No output ever says
*these six elements form a chain whose every internal edge is unread —
fan them out*. The evidence sits as five disconnected per-element
hedge-worded rows, ranked last by design (UX-68), while the one
structural conclusion they jointly support — the single biggest win in
the project, measured this round at **27.9s → 25.0s (−10.1%)** from
exactly that change — is never drawn. The tool found every brick and
never saw the wall.

The projection machinery to *quantify* the recommendation already
exists: UX-74 recomputes longest paths with elements zeroed in
milliseconds, and `bga replay` simulates arbitrary capacity; replaying
the observed run with the never-read edges deleted is the same class of
computation.

## Required Fix

A synthesis pass in `correlate` (it is the one place both planes are in
hand): find connected chains/sets of dependency edges that (a) gate the
critical path or carry material dependency-wait, and (b) were measured
never-read (UX-46 evidence, with its existing hedges — runtime-only
edges stay excluded). For each, emit a single structural finding naming
the edge set, the projected makespan with those edges removed (replayed
over the same observed durations, same capacity), and the standing
caveat that the projection is not a re-capture. Rank it by projected
saving alongside UX-74's per-element projections — on this project it
would outrank everything except `core.bst` itself.

## Out of Scope

- Auto-editing `.bst` files.
- Treating never-read as proof (the UX-46 hedge stands; the finding
  recommends *checking* the edges, with the projected prize attached).

## Acceptance Test

On this round's baseline capture of `examples/06` (protocol in
`docs/audit-round-10.md`): `bga correlate` emits one finding naming the
`lib-a→lib-b→…→lib-f` edge chain as never-read-and-gating, with a
projected makespan within noise of the measured macro-fixed run
(25.05s ± the documented band), and it appears above every declared-
not-used row. On `examples/07`, `user.bst`'s genuinely-consumed edge
must not appear in any such finding.
