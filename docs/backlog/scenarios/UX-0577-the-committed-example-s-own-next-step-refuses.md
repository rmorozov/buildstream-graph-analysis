# UX-577: the committed example's own next step refuses

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-78 (the run-mode refusal), UX-330 (the planted store) | **Serves:** the stranger who follows the README's second command | **Topic:** store

## Motivation

`examples/06-macro-micro-optimization/.bga/runs/` holds a cold run
and an incremental run. `bga analyze` on it prints, as its next step,
`bga compare @prev @last`; `README.md:82` and `cli.md:1226` teach the
same command on the same store:

```text
$ cd examples/06-macro-micro-optimization && bga compare @prev @last; echo $?
Refusing to compare (run_mode): baseline is a full run and candidate is a incremental run
6
```

The refusal is right (`UX-78`); the *advice* is wrong: `next_steps`
recommends a comparison the store cannot make, and the documented
example store carries the one pair that refuses. Also stale beside
it: `cli.md:1220-1222` quotes a `Next:` block with stamp
`20260821T170127Z`, absent from the tree since the ex06 refresh, and
the fresh block opens with two lines the guide does not have.

## Required Fix

- `next_steps` advises `compare @prev @last` only when the two runs'
  modes match; otherwise it names the refusal and the run that would
  pair (`--baseline-run <stamp>` of the same mode).
- The committed example store gains a second cold run (or the guides
  name the pair that compares), and the stale `Next:` block is
  refreshed and dated like `UX-511` did for Step 3.
- A guard runs every `bga …` line the guides print as a *next step*
  on the committed store and asserts exit 0.

## Out of Scope

- The refusal rule itself — `UX-78`'s rule is right; only the advice that leads into it changes.

## Acceptance Test

`bga compare @prev @last` in the example exits 0, or the analysis
no longer advises it there; mutation: restore the unconditional
advice — the next-step guard reds on the committed store.
