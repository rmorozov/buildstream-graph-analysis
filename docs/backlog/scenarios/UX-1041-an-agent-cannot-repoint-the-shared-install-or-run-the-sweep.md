# UX-1041: an agent cannot repoint the shared install or start the touching sweep

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 143 — the workflow review of rounds 140 and 142 | **Serves:** every parallel round's verifiers and the push gate after them | **Topic:** guards | **Area:** unassigned | **Shape:** mechanical | **Reading:** container

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

## Decision

The `architect`, round 149, at `c324f250`.

```text
Route:     a new PreToolUse Bash hook, agent_worktree_limits.py (.sh entry): resolve the payload
           `cwd` with gate_covers_push.repo_root(payload); a linked worktree when `git rev-parse
           --git-dir` differs from `--git-common-dir`; tokenise with no_bulk_add.tokens_of /
           without_heredocs; refuse pip/pip3/python -m pip install -e|--editable, make test |
           test-touching | test-tiers | push-check, and dev_touching.py without --spread; exit 2
           naming the rule. Absorbs the r140 fail-open line: selector_before_commit.repo_root
           (:37) judges the process cwd, the main checkout, for every worktree commit; it takes
           the payload's cwd, and a cwd in no repo allows (a commit there commits nothing)
Rejected:  a `.claude/worktrees/` prefix test - misses the decompose skill's `git worktree add`
           the hook's process cwd - CLAUDE_PROJECT_DIR whatever the worktree (UX-992)
           the rule kept in briefs - rounds 140 and 142 show a brief does not hold
Files:     .claude/hooks/agent_worktree_limits.py, .claude/hooks/agent-worktree-limits.sh (new);
           .claude/settings.json; .claude/hooks/selector_before_commit.py;
           tests/unit/test_the_agent_configuration_holds.py; docs/backlog/bookkeeping.md (--mark)
Guard:     on a tmp repo plus a `git worktree add`, process cwd a non-repo tmp: payload cwd the
           linked tree -> 2; the main tree -> 0; `pip install ruff`, `dev_touching.py --spread`,
           a heredoc naming a banned command -> 0; repo_root(payload) returns the payload's repo
Mutation:  worktree test always True -> main clause reds; resolve from the process cwd ->
           linked clause reds; the selector's repo_root ignoring the payload -> its clause reds
Class:     optimization - round 142's ~400 orphaned sweep processes timed push-check out at 50 min
Split:     one track, parallel with UX-938
Question:  none
```

## Outcome
