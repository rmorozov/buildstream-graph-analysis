# UX-218: the next step is a command you can run

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-207 (the diagnosis it branches on), UX-126 (the loop as one command run twice)

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
