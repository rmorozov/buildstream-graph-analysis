# UX-230: what if you could choose the fixes

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-219 (the plan drawn), UX-229 (the chains it explains) | **Serves:** R1, R8 | **Topic:** viewer

## Motivation

`UX-219` draws the published optimization plan as the fixed sequence
the pipeline projects. The fourth review's sketch — checkboxes, pick
your subset, see the projected build — is the interaction R8 brings
to a prioritisation meeting. Its own warning is the constraint: this
must not pretend to simulate. A page that sums per-element savings
is wrong the moment two fixes share a chain — which is exactly why
the pipeline's projection exists.

## Required Fix

Selection over projections the analysis computed. Subsets along the
published sequence render from the payload as `UX-219` already
does; an arbitrary subset is answered by the **server** (the blast
transport pattern: the page asks, the pipeline computes, the answer
is `bga`'s own), never by page arithmetic. The export shows the
published sequence and, for other subsets, the command that answers
them — the same honesty shape as the blast box offline note.

## Out of Scope

- Any client-side projection arithmetic, including "just adding" —
  `UX-219` measured why: on the golden fixture the published
  `makespan_after_us` differs from `total - cumulative_saving_us` at
  every step, so a page that added would disagree with the payload on
  every bar.
- Scheduling simulation beyond what the pipeline's structural model
  already certifies (its assumptions print with every number).

## Acceptance Test

A selected subset's projected total is byte-identical to the CLI's
answer for the same subset (transport guard, like the blast box's);
the no-arithmetic guard extends over the what-if renderer (mutation:
summing savings client-side has no green path); the export contains
the plan and the command, no live controls; a subset the pipeline
declines to project renders the refusal, not a guess.

## Outcome (round 28)

`whatif/v1`, from the new `bga/whatif.py`, answered by `bga whatif` and
by the page's transport — the same function, so the two cannot describe
one selection differently.

```text
$ bga whatif tests/fixtures/golden/mixed_task_kinds \
      --element base.bst --element lib.bst
What if these were fixed: base.bst, lib.bst
  Makespan 0.014s -> 0.004s (saves 0.010s)
  Their individual savings add up to 0.011s, which is not what they are
  worth together (0.010s) - what one fix is worth depends on the others.
  A structural projection over this run's measured durations: "fixed"
  means the element becomes instant and nothing else about the build
  changes. An upper bound on what the selection can be worth, not a
  forecast - a re-capture is still the ground truth.
```

**11,000 µs against 10,000 µs on the golden fixture.** The item's Out of
Scope says a page must never add savings and cites `UX-219`'s
measurement; this publishes the wrong answer beside the right one so a
reader sees the gap rather than being told about it. The document
carries `sum_of_individual_us` deliberately, and the schema says why.

### Three paths and no fourth

- **A prefix of the published plan is read.**
  `optimization_horizon[i].makespan_after_us` already *is* the makespan
  after the first `i+1` fixes. The page cites the path in `data-field`.
- **Any other subset is asked.** The blast transport, again:
  `whatif.json?elements=…` calls `bga.whatif.project`. The guard asserts
  the served document is byte-identical to `bga whatif --format json`
  for the same selection — `json.dumps(served)` against the CLI's
  stdout, not "close".
- **Offline the command is shown.** No server in an export, so the
  section renders `bga whatif RUN --element …` rather than a control
  that cannot answer. `UX-199`'s shape for the blast box.

Only a *prefix* counts as published, and that is not a shortcut: the
horizon is greedy, so step `i`'s makespan assumes steps `0..i-1` were
taken. A selection that skips one is a different question, and the
mutation that deletes the prefix check reddens.

### Three refusals, by name

An empty selection, an element the run's graph does not know, and an
element with no measured duration. Each names the `check` a caller
matches on and the elements it fired on. A refusal **exits 0**: "this
selection cannot be projected" is the answer, not a failure — the same
stance `bga blast` takes.

**Mutations verified red and reverted (7):** the projection summing the
individual savings; the page computing `total - summed` instead of
asking; a non-prefix subset read as if published; offline rendering a
control instead of the command; a refusal rendering as a blank; an
unknown element projected anyway; the transport passing a different
selection from the CLI.

**A note on the falsification itself.** Reverting the last mutation with
`git checkout -- tools/bga_view.py` reset the file to `HEAD`, which
predates this item's own transport — so the revert deleted work rather
than restoring it. Caught immediately by the guard that had just gone
red staying red, and re-applied. Recorded because "the mutation was
reverted" and "the file was reverted to something else" look identical
in a terminal.

**Deviation from the Required Fix:** none. No client-side projection
arithmetic exists on any path, and the guard that says so checks the
`data-source` of whatever the section shows against a closed set of
four — published, server, command, refused — with no branch that
produces a page-computed figure.

Full suite: `3094 passed, 3 skipped`.
