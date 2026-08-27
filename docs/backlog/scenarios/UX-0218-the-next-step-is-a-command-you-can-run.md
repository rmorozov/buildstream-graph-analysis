# UX-218: the next step is a command you can run

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-207 (the diagnosis it branches on), UX-126 (the loop as one command run twice)

## Motivation

This tool is used in a loop:

```text
capture → analyze → read → change something → capture again
                              ↑                     │
                              └── did that help? ───┘
```

and the loop is where the repetition lives. After reading the decision
panel, the reader's next action is drawn from a small closed set —
`bga blast <element>`, capture-and-analyze again, `bga compare @last
@prev` — and every round they retype it, with the run path and the
element name copied by hand out of the page.

The page already knows the run path, the project, the diagnosis and the
top element. The command is a *rendering* of facts it holds.

The branch itself is the more important half. Which next step is right
depends on `headline.diagnosis`, and that mapping is written today in
documentation prose. If the viewer encodes it, the viewer becomes a
second decision-maker — the thing `UX-207` exists to prevent. So the
step is **decided in the pipeline and published**, and the terminal, CI
and the page then give the same answer.

## Required Fix

1. `analyze/v1` grows `next_steps`: an ordered list, each entry with a
   `reason` (why this step, drawn from published values), an `argv`
   (the command as a list, with the run and element already
   substituted) and the finding or signal it follows from. Decided by a
   small deterministic table over values the payload already carries —
   diagnosis, scheduling gap, path concentration, blast radius,
   comparability — and no new analysis.
2. `bga analyze`'s text report ends with them, in the same words.
3. The page renders them at the foot of the decision panel, each with a
   Copy button (`UX-208`'s helper).
4. Any step whose precondition is absent is **not rendered** —
   `UX-194`'s dead-button rule: no "compare against previous" on a run
   with no predecessor in its store.

## Out of Scope

- Running anything. The page proposes; the reader runs. No exec, no
  server write, no shell-out.
- Any step the tool cannot spell exactly — if the run path cannot be
  written as a stable argument, the step is omitted rather than
  approximated.
- Natural-language advice beyond the deterministic table.

## Acceptance Test

Two committed fixtures answer differently: the golden run
(`scheduler_bound`) and `examples/06` (`chain_bound`) produce different
first steps, asserted by value rather than by presence. Every published
`argv` is executable as spelled — asserted by running it against the
fixture and requiring a non-error exit, not by matching a string.

Mutations, each asserted red: make the viewer recompute the step from
`chain_ratio` instead of reading `next_steps` → a fixture whose
published step and derived step disagree reddens; drop the
precondition check → a run with no predecessor offers a compare step
and the dead-button guard fails.

---

## Outcome (round 25)

**Status:** 🟢 Done.

`analyze/v1` publishes `next_steps`: an ordered list, each with the
reason it was chosen (in terms of the values that chose it), the `argv`
with the run and element already substituted, and the field it follows
from. `bga analyze`'s text report ends with them and the decision panel
renders them with a Copy button — **one function, so the terminal, CI
and the page cannot advise differently**, which is the whole reason the
branch is in the pipeline rather than the viewer.

**The acceptance that matters is not "a command is shown".** `bga
blast` with its arguments the wrong way round shows just as well. Every
published `argv` is *executed against the fixture* and required to exit
zero and print something; reversing `uid` and `run_dir` reddens it.

**Two committed fixtures answer differently, asserted by value:**

```text
golden (scheduler-bound, outside a store, no Plane 2)
    blast-the-top-element      bga blast base.bst tests/fixtures/…
    sweep-the-capacity         bga sweep tests/fixtures/…

examples/06 (chain-bound, in a store, Plane 2 present)
    blast-the-top-element      bga blast core.bst examples/06/…/run
    look-inside-the-element    bga correlate examples/06/…/run
    measure-again              bga snapshot examples/06-…
    compare-with-the-run-before  bga compare @prev @last --project …

> **`UX-326` (round 47):** the last two lines above were wrong as
> shipped, and this Outcome is left as written per `UX-132`. `bga
> snapshot <project>` put the project where `snapshot`'s REMAINDER build
> command goes and crashed with `ValueError: command must start with
> 'bst'`; `bga compare … --project` named a flag `bga compare` has never
> had. Neither was caught because this round's own acceptance -
> "every published `argv` is executed" - was implemented as a
> hand-written parametrize of two step ids, and these are the other two.
```

Note what is *absent* from each: the golden run is offered no
`measure-again` (it is not in a store) and no `look-inside` (no Plane
2); `examples/06` is offered no capacity sweep, because more builders
is the wrong advice for a chain-bound build. `UX-194`'s dead-button
rule, applied to advice rather than controls — and a table that
returned the same list for both would be no branch at all.

**`compute_next_steps` stays a pure function of the result.** The
store-shaped steps are decided by the *shape* of the published run path
(`<project>/.bga/runs/<stamp>/run`), not by probing the filesystem, so
the pipeline does no IO to give advice and a path that is not
store-shaped simply yields no store-shaped steps.

One thing the first draft got wrong and the fixtures caught **twice**:
the reason rendered *"0.0s of wall-clock is beyond the critical path"*
on the golden run (gap: 2 ms), and then *"worth 0.0s"* on the
synthetic topologies. A figure that rounds away argues against the
sentence carrying it, so both clauses appear only above 0.1s.

**Two of the repository's own guards caught real consequences**, and
both were right to. `test_section_stage_gating` compares a gated
render against a full one from two different directories — and a
next-step command *names the run*, which is what makes it runnable, so
its existing path normaliser was extended to cover the commands rather
than the feature weakened. And `_StubResult` in the scale tests has no
`run_instance` at all: `compute_next_steps` reached for the attribute
directly and raised. It uses `getattr` now — advice is the last thing
that should be able to break a report.

Eight mutations, each verified red: the argv spelled wrong; the branch
removed; store steps offered to a run outside a store; the join step
offered without Plane 2; the panel deriving the step instead of reading
it; the Copy button copying the reason; the text report dropping the
block; `follows_from` dropped.

**Deviation from the Required Fix:** none. Nothing is executed — the
page proposes and the reader runs.

**A third guard caught it after the fact, in CI, and that is the honest
record.** The verification above ran `pytest tests/unit`. CI runs
`make test`, which is `pytest tests/` — four files wider, one of them
`tests/test_golden.py`, whose committed snapshot is an exact diff of a
full `analyze/v1` report. Adding `next_steps` to every full report made
that snapshot stale, so the pull request went red on all four Python
versions while the local run was green. The narrower command was the
mistake, not the feature.

Fixing it exposed the same tension `test_section_stage_gating` had
already raised, in a place where it matters more. A next-step command
names the run directory, so the value is a property of the machine that
ran the analysis — exactly why `run_instance` is dropped from that
snapshot. Regenerating naively would have committed this checkout's
absolute path and failed on every other machine. `_run_analyze` now
replaces the fixture path with `<run>` before comparing, and the
regeneration recipe in the file's own docstring was rewritten to do the
same thing, since a recipe that disagrees with the test writes a
snapshot the test can never match.

Measured, not argued. The regenerated snapshot's diff is `next_steps`
and nothing else — 23 lines added, zero changed — so round 25 drifted
no other field. The test passes from a second checkout at a different
absolute path (`tar`-copied out of `git ls-files`), which is the
condition CI actually exercises. Two mutations verified red against
that copy: a next-step reason reworded, and `run_dir` dropped from the
blast argv. The path is normalised; the *command* is still compared,
including the fact that it names a run at all. Full `make test`:
2829 passed, 3 skipped.
