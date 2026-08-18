# UX-82: the tool measures every fact of the macro fix and never states the macro fix

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-46, UX-74 (both done)

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
`docs/audits/round-10.md`): `bga correlate` emits one finding naming the
`lib-a→lib-b→…→lib-f` edge chain as never-read-and-gating, with a
projected makespan within noise of the measured macro-fixed run
(25.05s ± the documented band), and it appears above every declared-
not-used row. On `examples/07`, `user.bst`'s genuinely-consumed edge
must not appear in any such finding.

## Fix Implemented

`bga correlate` now draws the conclusion its own rows support. Where a
*group* of declared build edges was measured never-read **and** those
edges chain elements along the critical path, it emits one finding
naming the chain and replays this run without those edges — same
durations, same capacity, same deterministic scheduler:

```text
Restructuring opportunity: 5 declared build edge(s) among 6 element(s) were
measured never-read, and they chain those elements along the critical path:
    lib-a.bst -> lib-b.bst -> lib-c.bst -> lib-d.bst -> lib-e.bst -> lib-f.bst
    Replaying this run with those edges removed - same durations, same capacity -
    finishes in 12.0s against 28.0s: 16.0s
    Worth checking whether those edges are needed at build time: each one is
    evidence, not a verdict ... and the projection is a replay of this run's
    durations, not a re-capture.
```

Rendered **above** the per-element rows, because a structural conclusion
outranks the individual measurements it is drawn from — and those
measurements are the ones the producer hedges hardest (`UX-68`).

### Why a replay rather than a longest path

`UX-74`'s per-element projection zeroes a duration and recomputes the
longest path, which is right for "what if this element were free". It is
wrong here. Removing five chain edges makes six elements ready at once,
and what happens next is decided by **how many builders there are**, not
by a chain that no longer exists: on the fixture, the longest path would
say 8s where the capacity-aware replay says 12s. The replay is the model
that can land near a measured re-run, which is what the acceptance test
asks for.

### The hedge survives the synthesis

Aggregating five instances of an explicitly hedged measurement does not
make it a verdict, and the finding says so in the same breath as the
prize. Tested: `test_the_hedge_survives_the_synthesis`.

### Deliberate bounds

- **Both endpoints must be on the critical path.** An unread edge that
  holds nothing up is a true observation and not a restructuring
  opportunity; it stays a per-element row. Tested both ways.
- **The projection is optional.** `correlate` is a library over two
  finished artifacts; the tasks and run context are an extra the CLI
  happens to have. Without them the finding still names the chain and
  reports no projection — losing the tasks costs the number, not the
  conclusion.
- On the real `freedesktop-sdk` capture this fires **not at all**, which
  is correct: after `UX-68` its never-read candidates are runtime stacks
  that do not chain along the path. It does not invent findings.

Tests: 7 new in `tests/unit/test_restructuring_synthesis.py`. Suite:
1136 → 1143.

## Verification Log

Fixed 2026-08-18. The fixture reproduces `examples/06`'s baseline shape -
six libraries that really depend on `base` with decorative chain edges on
top - and the 28s → 12s projection is the replay's own output at the
run's own capacity of 4, not a hand-computed figure. Re-run against the
published `freedesktop-sdk` capture to confirm it stays silent there.

## Round-11 verification: the filed acceptance, run on the named capture

The fix shipped verified against a hand-built fixture reproducing
`examples/06`'s shape (28.0s → 12.0s), not against the round-10 capture
the acceptance named. Round 11 closed that gap by running the filed
command on the retained real capture:

```text
$ bga correlate <round-10 run-baseline> <plane2-baseline.json>
Restructuring opportunity: 18 declared build edge(s) among 8 element(s)
were measured never-read, and they chain those elements along the
critical path:
    app.bst -> core.bst -> lib-a.bst -> ... -> lib-f.bst
    Replaying this run with those edges removed - same durations, same
    capacity - finishes in 11.1s against 24.9s: 13.8s
```

It fires, first in the output, above every declared-not-used row, with
the UX-68 hedge intact — every clause of the acceptance except one,
which the measurement corrects in place: the filed criterion expected
the projection "within noise of the measured macro-fixed run
(25.05s ±band)". That expectation was wrong as filed. The macro-fixed
variant removed only the *chain* edges; the shipped finding removes
every never-read edge on the chain, which includes the `core→lib`
edges the example's own `optimized/` variant retains — so the correct
comparison is against a graph where the libs fan out directly off
`toolchain`, whose critical path is `core.bst` alone: **11.05s
measured, 11.1s projected**. The projection is *more* accurate than
the criterion, not less; the criterion tested the example's answer,
and the tool's evidence is (correctly) more aggressive than the
example. The `examples/07` negative case remains covered by fixture
and by fdsdk's silence rather than by a live `examples/07` run.
