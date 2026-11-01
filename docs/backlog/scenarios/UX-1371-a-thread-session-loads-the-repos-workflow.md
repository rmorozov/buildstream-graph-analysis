# UX-1371: a project-thread session loads the repository's agents, skills and hooks

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** — | **Found by:** the workflow review of 2026-11-01 (project thread "Review and optimize the agentic workflow") | **Serves:** every round run from a project thread, and every rule a hook holds | **Topic:** guards | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_thread_session_runs_the_repos_hooks.py`

## Motivation

A project-thread session starts in `/home/claude`, above both
checkouts. Both `CLAUDE.md` files load; no `.claude/agents`,
`.claude/skills` or `.claude/settings.json` does. In this session
(CLI 2.1.316) the Agent tool lists only built-in types, the skill list
has none of `orient`, `decompose`, `verify`, `falsify`, and `git add -A
-n` in the checkout ran unrefused while `.claude/hooks/no_bulk_add.py`
fed the same payload exits 2. Round 175 ran its four tracks as
`general-purpose` (three on Opus high, $8.52-$21.81 each) with no
verifier (`UX-1370`). The project has no cloud environment, so nothing
runs before a session starts.

## Decomposition

Input classes: a tool call inside a checkout, inside a linked worktree,
outside any checkout; a tool the hook's matcher names and one it does
not; a first setup and a rerun; the owner's checkout and `bga-bench`.

## Required Fix

`tools/dev_cloud_setup.sh` links the agents and skills into the user's
`~/.claude`, adds one user hook per event that runs
`.claude/hooks/dispatch_by_repo.py`, and (without `--links-only`)
unshallows each clone and installs the lock and the package. The
dispatcher runs the hooks of the checkout a call is made in.

## Out of Scope

Creating the cloud environment: only the owner can, in Project settings.
Reconciling `bga-bench`'s diverged agent files with this repository's.
`BGA_CHROME`, which a setup script cannot export into the session.

## Acceptance Test

With `HOME` a temp dir, setup links every agent and skill and a rerun
leaves one dispatcher hook per event; the dispatcher refuses `git add -A`
inside the checkout and runs nothing outside one or for an unmatched
tool. Mutation: drop each clause; its test reds. The live reading, a new
thread session listing `verifier` among its agents, waits on the owner.

## Outcome (2026-11-01)

Gap: listed above (agents, skills, the unrefused bulk add). Close:
`python3 -m pytest -q tests/unit/test_a_thread_session_runs_the_repos_hooks.py`
reads `3 passed`. Mutations, `PYTHONDONTWRITEBYTECODE=1`:

| mutation | red |
|---|---|
| the dispatcher ignores the matcher | 1 failed, 2 passed |
| the dispatcher finds no checkout | 1 failed, 2 passed |
| a refusing hook is not passed on | 1 failed, 2 passed |
| skills are not linked | 1 failed, 2 passed |
| a rerun adds a second hook | 1 failed, 2 passed |

Deviation: running the script against this session's own `~/.claude`
was refused by the session's permission classifier as self-modification,
so the live reading is the cloud environment's first session. The
environment's setup script is one line:
`bash /home/claude/buildstream-graph-analysis/tools/dev_cloud_setup.sh /home/claude/buildstream-graph-analysis /home/claude/bga-bench`.
