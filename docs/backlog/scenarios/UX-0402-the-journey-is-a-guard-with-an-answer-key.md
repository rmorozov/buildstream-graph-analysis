# UX-402: the journey is a guard with an answer key

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-330 (the planted store it can start from), UX-345 (the real-boot precedent) | **Serves:** every future round, before its walk | **Topic:** guards

## Motivation

Round 45's stranger walk found four bugs forty-four feature rounds
never saw; round 63's found ten more; round 64's found six — among
them a silent forfeiture of all of Plane 2 (`UX-405`) that no test
noticed because no test walks the journey the guides describe. The
walks are the highest-yield detector this project has, and they run
only when an audit round remembers to.

The journey is also cheap enough to mechanize now, measured on this
machine in round 64:

```text
bga doctor                          23.4s
cold snapshot (bst build all.bst)   31.9s
incremental snapshot                 2.8s
correlate / cache-logs / export     ~1-2s each
```

And `examples/06-macro-micro-optimization` ships an `optimized/`
twin, so the journey has an *answer key*: the chain fan-out, the
codegen edge, the `notparallel` pin. A guard can assert the tool's
advice, not just its exit codes.

## Required Fix

One large-tier test that walks `doctor → snapshot (cold) → snapshot
(incremental) → analyze → correlate → view --export → timeline` on
example 06, from the documented commands, and asserts *analytic
outcomes*:

- the headline names the chain and the #1 card is `core.bst`;
- the `notparallel` sentence reaches the terminal and the page;
- the never-read edge lists name `codegen.bst` for the lib elements;
- Plane 2 traced a nonzero process count (RED today under
  `UX-405`'s relative-path shape — the guard runs both shapes);
- the incremental page states its empty populations rather than
  dropping them (joins `UX-388`'s fix);
- the exported page and the terminal agree on the attribution digit
  the round-64 walk cross-checked.

Skip-gated on `bst` + `bwrap` like the rest of the large tier, with
the one-string skip reason the census counts.

## Out of Scope

- Driving Perfetto in this guard — trace assertions live with the
  `trace_processor` gate (`tests/trace_processor.py`) and `UX-406`
  owns the spine double-count; this guard stops at the export.
- More example projects — one journey with an answer key first; the
  sweep across examples is a follow-on once the harness exists.

## Acceptance Test

- The guard runs green on a machine with bst, and its skip reason
  appears in the census on one without.
- Falsification: restore the `[:120]` name trim or blind the Plane 2
  count — the journey guard goes RED on the assertion that names it.

## Outcome (round 64, 2026-08-29) — 🟢 Done

### The gap, measured

Nothing in the suite ran `bga snapshot` over a real project. `git grep`
finds guards that run `bst`, and every one of them checks a *step*: a
refusal, a directory listing, a parsed log. The journey - the sequence
the guides describe, ending in a reader's judgement about their build -
ran only when an audit round walked it by hand, which is why three
consecutive rounds each found bugs no test had.

### After

The journey, walked from the documented commands on a copy of example
06 with its own artifact cache:

```text
$ PYTHONPATH=. python3 -m pytest \
    tests/unit/test_the_journey_has_an_answer_key.py -q
..............
14 passed in 50s
```

The steps and their real cost on this machine:

```text
bga doctor <project>                 0.6s
cold snapshot (bst build all.bst)   43.9s
incremental snapshot                 3.2s
analyze / correlate / export        ~1s each
one Chrome boot on the export       ~2s
```

### The answer key, and what the tool said unprompted

Example 06 is mis-optimized in three independently-fixable ways, so
each is a claim the tool should make on its own. It made all three:

```text
1  macro / graph shape
   headline.diagnosis                  chain_bound
   "This build is chain-bound, not scheduler-bound: the critical path
    is 92% of wall-clock…"
   optimization_horizon[0]             core.bst
   terminal                            "core.bst is the first thing to
                                        fix, worth 6.0s"

2  macro / over-declared dependency
   restructuring[0].edges              the six-deep chain, lib-a→lib-b
                                        …lib-e→lib-f
   elements[lib-a].unused_dependencies ["codegen.bst", "core.bst"]

3  micro / inside one element
   plane2_coverage.process_count       813
   correlate, on core.bst              "…runs at only 0.88 cores busy -
                                        it is waiting, not computing,
                                        and its native build asked for
                                        -j1: remove `notparallel`"
```

`UX-405`'s class is guarded before any of it is read: the Plane 2
process count is asserted nonzero first, so a capture that silently
forfeited the second plane fails on the assertion that names it rather
than leaving every clause below vacuously green.

### The cache is isolated, and that is the point

`XDG_CACHE_HOME` moves into the temporary tree. Against the host's own
cache the first snapshot is a wall of cache hits: every element takes
0.00s, the critical path is empty and every clause above passes over
nothing. Measured, before the isolation was added:

```text
lib-c.bst: disappeared (1.75s, no delta to compare)
toolchain.bst: appeared (0.00s, no delta to compare)
real 0m5.675s
```

against 43.9s and a 28.1s critical path with it. It also means the
guard never touches the developer's artifacts.

### Two things this found that were not the tool

- **The shared node probe is always served.** The first draft read the
  incremental page through `test_a_report_you_can_navigate.py::_PROBE`.
  It boots with `location.href` hard-coded to an `http://` URL whatever
  `PROTOCOL` says, so a capture whose trace is too large to inline -
  written as a relative path rather than a `data:` URL - takes the
  served branch of the Perfetto handoff and dies on a detached element:

  ```text
  Could not load this run
  TypeError: Cannot set properties of null (setting 'hidden')
      at wireTheHandoff (…:6034:35)
  ```

  The page is fine; a real browser has a parent there and never runs
  that line from an export. Filed as **`UX-415`**, and this clause uses
  Chrome, which is the ground truth either way.
- **`[data-empty]` is not `section[data-empty]`.** The rail's own link
  carries the same mark on purpose (so the map of the report matches
  the report on an incremental run), so the bare attribute selector
  read four anchors as four silent sections. The selector names the
  element it means.

### Deviation from the Required Fix

- The Required Fix's list says the never-read edge lists "name
  `codegen.bst` for the lib elements". Measured, the *finding* names
  the chain and `codegen.bst` is on each element's own
  `unused_dependencies` row - which is where a reader looking at
  `lib-a.bst` finds it. Both are asserted, in the two places they
  really live.
- **The comparison the second snapshot prints is a refusal, not a
  verdict.** A full run and an incremental one are not comparable
  (`UX-55`), and `bga snapshot` says so rather than comparing them.
  That is correct behaviour, so the clause asserts the command the
  loop offers (`bga compare @prev @last`) rather than a verdict the
  journey cannot produce in two runs.
- Perfetto is out of scope by the filing's own text; this guard stops
  at the export and one Chrome boot on it.
