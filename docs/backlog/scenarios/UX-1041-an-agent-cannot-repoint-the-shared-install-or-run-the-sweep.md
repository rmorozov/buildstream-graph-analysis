# UX-1041: an agent cannot repoint the shared install or start the touching sweep

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143 — the workflow review of rounds 140 and 142 | **Serves:** every parallel round's verifiers and the push gate after them | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

Every agent brief says never `pip install -e .` from a worktree and not to
start the touching sweep. Round 142's verifiers did both: one repointed the
shared `bga` install at its worktree, one ran `dev_touching.py` against its
brief, and orphaned sweeps left about 400 processes that timed
`make push-check` out at 50 minutes. Round 140's UX-992 verifier skipped
`dev_sizes.py --check` and said MERGE on unadopted growth. A brief is a
promise; a PreToolUse hook is a mechanism.

## Required Fix

A PreToolUse hook on Bash refuses `pip install -e` and `make test`,
`make test-touching` or `dev_touching.py` without `--spread` when the
payload's cwd is a linked worktree the Agent tool created, naming the rule.

## Out of Scope

The session's own checkout; `pip install <tool>`.

## Acceptance Test

`test_the_agent_configuration_holds.py` fires the hook with each payload
from a worktree cwd and gets a block, and from the main checkout gets none.
Mutation: drop the worktree test from the hook, and the main-checkout
clause reds.

## Outcome
