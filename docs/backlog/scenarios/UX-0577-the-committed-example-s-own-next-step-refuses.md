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

## Outcome (round 83, 2026-09-03) — 🟢 Done

**Premise:** falsified — no `.bga` path has ever been tracked here, so
the "committed example store" is one machine's untracked leavings; the
defect it names is real and reproduces on committed fixtures.

### The gap, measured

`tests/fixtures/same_build_twice_{cold,incremental}` are a `full` and an
`incremental` run. Planted as a two-run store, `bga analyze @last`:

```text
  Whether it helped, judged against this store's noise - run it in …/mixstore.
    bga compare @prev @last

$ bga compare @prev @last; echo $?
Refusing to compare these runs (run_mode):
  - baseline is a full run and candidate is a incremental run - …
6
```

The advice and the refusal are one command apart; `6` is
`EXIT_CODES["mismatched runs"]` (`UX-574`). The untracked `examples/06`
store is the same shape: one `full` run and five `incremental`.

### After

`compute_next_steps` reads one `run-context.json` per snapshot — the
read `UX-296` chose for a band sample, no trace parse:

```text
store: incremental, full, incremental
  @prev is a full run and @last a incremental one, which compare refuses -
  20260901T000000Z is the newest incremental run and pairs with it. …
    bga compare @20260901T000000Z @last      -> exit 0

store: full, incremental          (no run pairs with @last)
    (no compare step offered)     `bga compare @prev @last` -> exit 6

store: incremental, incremental
    bga compare @prev @last                  -> exit 0
```

`unknown` is not a mismatch, for `_check_run_modes`' reason. `cli.md`'s
`Next:` block, which quoted a stamp no clone has, is now verbatim from
`bga gen-synthetic --store /tmp/bga-demo` — both its runs are `full`, so
its `compare @prev @last` exits 0, and the guard replants and runs it.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| A1 | re-offer `@prev @last` when nothing pairs | `test_a_mismatched_pair_is_not_advised`, 1 of 7 |
| A2 | a matched pair reported as a mismatch | `test_a_matched_pair_is_advised_and_runs`, 1 of 7 |
| A3 | drop the `unknown` clause | `test_an_unknown_mode_is_not_a_mismatch`, 1 of 7 |
| A4 | the pairing step names `@prev` again | `test_the_run_that_would_pair_is_named_and_runs`, 1 of 7 |
| A5 | `_check_run_modes` returns `None` always | `test_a_mismatched_pair_is_the_refusal_this_guards`, 1 of 7 |
| A6 | the guide quotes a run path the store lacks | both guide clauses, 2 of 7 |
| A7 | the guide quotes `@20260303T091500Z` for `@last` — exits 0, is not the advice | `…are_the_ones_the_tool_prints`, 1 of 7 |

A first draft asserted the block names `/tmp/bga-demo`; no mutation
reddens it alone, because A7's clause substitutes the planted path back
and catches any other literal. Dropped rather than kept.

### Deviation from the Required Fix

`--baseline-run <stamp>` is not the flag: it appends a band sample, so
`bga compare --baseline-run @prev @last` exits 1 with *"the following
arguments are required: candidate"*. The step publishes
`bga compare @<stamp> @last`. No run was committed — **0 bytes added**,
`UX-189`'s clone stays capture-free — the guides name the pair instead.

```text
$ make test-touching
49 file(s) selected · 934 passed, 44 skipped in 20.66s
$ make lint
All checks passed!
```

`make test` is the orchestrator's; this track ran the selector only.
