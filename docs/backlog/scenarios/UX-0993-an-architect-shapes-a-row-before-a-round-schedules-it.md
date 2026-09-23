# UX-993: an architect shapes a row before a round schedules it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-706 | **Blocks:** UX-994 | **Found by:** round 139 — Ruslan in the project thread, 2026-09-23 14:44, answering the workflow review ([doc](https://claude.ai/code/artifact/7f65768e-b4bb-405a-b3e1-90a672a249f5)) | **Serves:** every round's planning, and the implementer tracks a judgement row never reaches | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

Judgement rows go to the orchestrating session, which also sequences,
merges and closes. `dev_process_bands.py --runs` prices them at a
median of 318k tokens and 51 min against bounded's 228k and 33 min
(73 runs against 34), and the ledger's friction column names a wrong
task-file premise 19 times, each found by an implementer after it spent
its run. Ruslan adopted the role outright on 2026-09-23 14:44.

## Required Fix

A read-only `architect` agent in `.claude/agents/` that returns a
fixed-shape decision for one row: route, rejected routes, files, guard,
mutation, product or process, tracks, and a question only when the fork
changes the owner's goal. The session pastes it into the task file as
`## Decision`. The pipeline line in `CLAUDE.md`, the rules card and
`decompose`'s shape step name it. It is pulled, never a gate.
`dev_close_task.py --shape` derives a row with a `## Decision` naming
its files, a guard and a mutation as mechanical.

## Out of Scope

A hook or guard that refuses an unshaped row: that would be the
review-cadence block of round 138 again. The retro routine (review
proposal 6).

## Acceptance Test

`python3 -m pytest -q tests/unit/test_the_agent_configuration_holds.py`
green with `architect` in `REPORTERS`; giving it `Edit` reddens it.

## Outcome (round 139, 2026-09-23) — 🟢 Done

**Premise:** held — the three rows this round filed on process surfaces derived judgement.

### The gap, measured

```text
$ python3 tools/dev_close_task.py --shape UX-99N    # origin/main's tool, this round's task files
UX-995   judgement   ...
UX-996   judgement   ...
UX-997   bounded     y..
```

A row naming `.github/` or `.claude/` could never become a track, however
precisely it was shaped.

### After

Three `architect` runs (opus, read-only) wrote the `## Decision` of
UX-995, UX-996 and UX-997; each names files, a guard and its mutations.

```text
$ python3 tools/dev_close_task.py --shape UX-99N    # this commit
UX-995   mechanical  ...
UX-996   mechanical  ...
UX-997   mechanical  y..
$ python3 -m pytest -q tests/unit/test_the_agent_configuration_holds.py tests/unit/test_a_task_declares_its_shape.py
144 passed
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| A1 | `architect.md` given `Edit` | `test_a_reporting_agent_cannot_edit_the_tree` |
| A2 | its body loses "Report only. Fix nothing." | `test_a_reporter_is_never_put_on_the_editing_list` |
| A3 | `derived_shape` ignores the Decision | `test_an_architects_decision_takes_the_judgement` |
| A4 | the Decision needs no `Mutation:` line | the same clause |

### Deviation from the Required Fix

The Decision block is read by `--shape`, which the Required Fix did not
name: without it a shaped row still derived judgement.
