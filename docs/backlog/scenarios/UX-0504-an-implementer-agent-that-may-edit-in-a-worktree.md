# UX-504: an implementer agent that may edit, in a worktree only

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-498 (the tracks it would run), UX-501 (the index it must not touch) | **Serves:** the orchestrating session that has two independent tracks and one context window | **Topic:** guards

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

## Outcome (round 75, 2026-09-01) — 🟢 Done

### The gap, measured

```text
$ ls .claude/agents/
researcher.md  verifier.md
$ python3 -m pytest -k test_neither_can_edit_the_tree
1 passed   # for every agent: Edit, Write, MultiEdit, NotebookEdit forbidden
```

`decompose` §3 defines a track as something that runs in its own
worktree and reports back, and nothing could run one: both agents are
read-only by a rule that is right *for them*. An implementer is a
different role with a different guard-rail, not an exception to theirs.

### After

Three agents. `.claude/agents/implementer.md` takes one task file and
one worktree, runs the inner loop, commits on the track's branch, and
reports the surfaces it touched against the ones the Decomposition
declared. Its editing is bounded by **where it runs**, not by what it
promises — the Agent tool's worktree isolation — and its body names the
four files no track writes, with the measurement behind that rule:

```text
docs/backlog/scenarios/README.md      UX-501: two branches each closing
docs/backlog/scenarios/closed.md      one item conflicted on the topic
tests/tiers.py                        table and silently auto-merged the
tests/ci_reference.json               counts to a number neither meant
```

The guard split in three: a **reporting** agent cannot edit; the
implementer must be able to; and a reporter is never put on the editing
list — the third is the one that took two tries.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| T1 | the implementer's tools trimmed to read-only | `..._implementer_may_edit` |
| T2 | the worktree sentence dropped | `..._says_where_it_runs` |
| T3 | a shared file no longer named in the body | `..._names_the_files_no_track_touches` |
| T4 | the verifier given `Edit` | `..._reporting_agent_cannot_edit_the_tree` |
| T5 | `MAY_EDIT` widened to every agent, verifier given `Edit` | `..._reporter_is_never_put_on_the_editing_list` |
| T6 | a reporter's body stops saying it does not edit | the same clause |

**T5 passed on first writing.** The split was expressed as "everyone
except whoever is on the editing list", so widening that list exempted
the reporters and every clause stayed green — the guard asserted its
own configuration rather than the role. It now names the reporters and
checks that each still says so in its own body, and T5 and T6 red from
both ends.

The phrasings accepted for "this agent does not edit" are the three the
two bodies actually carry (`report only`, `fix nothing`, `do not edit`).
A fourth is a decision somebody makes, not a pattern to lengthen —
fixing guide §5's rule applied to the guard itself.

### Deviation from the Required Fix

- **The end-to-end track run is not in this Outcome.** The acceptance
  test asks for one real track whose report matches `git diff --stat`
  on its branch. Launching a worktree agent is the orchestrating
  session's move and this round has been running its items serially;
  the first round that uses two tracks is where that measurement
  belongs. The configuration half — the half a guard can hold — is done
  and mutated.
- `isolation: "worktree"` moved from the frontmatter `description` into
  the body: a colon inside a front-matter value breaks PyMarkdown's
  parse, and `make lint` said so (`MD023` at `2:1`).

```text
make test  5770 passed, 27 skipped in 319.13s;  make lint clean
```
