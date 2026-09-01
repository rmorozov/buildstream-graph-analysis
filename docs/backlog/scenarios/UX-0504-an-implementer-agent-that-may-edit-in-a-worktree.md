# UX-504: an implementer agent that may edit, in a worktree only

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-498 (the tracks it would run), UX-501 (the index it must not touch) | **Serves:** the orchestrating session that has two independent tracks and one context window | **Topic:** guards

## Motivation

`decompose` §3 defines a track as something that runs in its own
worktree and reports back. Today nothing can run one: the two
subagents are read-only by rule —

```text
tests/unit/test_the_agent_configuration_holds.py::test_neither_can_edit_the_tree
    for every file in .claude/agents/: Edit, Write, MultiEdit, NotebookEdit forbidden
```

— and that rule is right for them: a verifier that fixes judges its
own work. An implementer is a different role with a different
guard-rail, not an exception to theirs.

## Required Fix

- `.claude/agents/implementer.md`: takes one task file and one
  worktree; runs the inner loop (`orient`, the cited ranges,
  `test-touching`, falsify); commits on the track's branch with the
  task's message; **never** touches the four shared files (the index
  pair, `tiers.py`, `ci_reference.json`); returns the touched-surface
  list against the declared one and the mutation table.
- The agents guard splits: reporting agents (researcher, verifier)
  cannot edit; the implementer may, and its body must name the four
  files it does not touch and say it runs in a worktree — both
  asserted.
- The Agent tool's `isolation: "worktree"` is the launch shape; the
  orchestrator merges, runs `dev_close_task --check --write`
  (`UX-501`), and the batch gate.

## Out of Scope

- Letting the implementer close the task — the Outcome, the row move
  and the suite stay with the orchestrator, which is the one session
  with the whole batch in view.
- More than one implementer per track — a track is one worktree.

## Acceptance Test

The agents guard green with three agents; red if the implementer's
tools drop the worktree sentence or name a shared file as editable.
One real track run end to end: the implementer's report lists exactly
the files `git diff --stat` on its branch shows.
