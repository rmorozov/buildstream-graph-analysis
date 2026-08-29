# UX-402: the journey is a guard with an answer key

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-330 (the planted store it can start from), UX-345 (the real-boot precedent) | **Serves:** every future round, before its walk | **Topic:** guards

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
