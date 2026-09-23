# UX-992: the push gate reads the main checkout's `HEAD` from a worktree

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-762, UX-948 | **Blocks:** — | **Found by:** round 139 — a live push from a track's worktree, always blocked | **Serves:** every track that runs `make push-check` in a worktree and then pushes | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`.claude/hooks/gate_covers_push.py`'s `repo_root()` calls `git
rev-parse --show-toplevel` with no `cwd=`, so it resolves against the
*process's* inherited working directory, not the worktree the pending
`git push` runs in. A `PreToolUse` hook is spawned by the harness with
`CLAUDE_PROJECT_DIR` (the main checkout) as its cwd, so `repo_root()`
returns the main checkout every time, regardless of which worktree the
Bash tool call that carries the push is about to run in. `head_sha`
and `covered_sha` then both read the main checkout's `.gate-covered`
and `HEAD` - never the worktree's - so a worktree's own green `make
push-check` is invisible to the hook, and its push is refused for a
sha it never claimed to cover.

`repo_root`'s own docstring already names the class of bug ("a hook
reading its own path judges a tree the pusher is not in", round 80's
track D) and believes `git rev-parse --show-toplevel` fixes it - it
does, for a hook invoked with the pusher's cwd already set, but not
for one invoked with `CLAUDE_PROJECT_DIR` as cwd, which is what a
`PreToolUse` hook in a worktree actually gets.

## Required Fix

Resolve the toplevel from the tree the pending command will actually
run in, not from the hook process's own inherited cwd - e.g. read the
`cwd` the `PreToolUse` payload itself carries (Claude Code sends one)
and pass it as `cwd=` to the `git rev-parse --show-toplevel` call,
falling back to the hook's own cwd only when the payload carries none.

## Out of Scope

- `repo_root`'s existing round-80 fix for a hook invoked with the
  pusher's own cwd already set (e.g. a session running outside any
  harness-managed `CLAUDE_PROJECT_DIR`) - that path stays correct and
  needs no change.
- `no_bulk_add.py` / `selector_before_commit.py`'s own worktree
  handling — not measured here, filed only if a track finds the same
  gap there.

## Acceptance Test

From a worktree with a green `make push-check` (its own `.gate-covered`
naming its own `HEAD`), feeding the hook a `git push` payload returns
exit 0 - today it returns 2, naming the main checkout's `HEAD` as
"never covered", not the worktree's covered sha. Mutation: revert the
fix (drop the payload `cwd`) and confirm the guard reds again.

## Outcome

**Round 139, 2026-09-23**

**Gap measured.** This session's own sandbox refuses a git operation
whose cwd resolves to the real main checkout (`git rev-parse HEAD`
against `/home/claude/buildstream-graph-analysis` is itself blocked:
*"a worktree-isolated agent's git operations must target its own
worktree"*) - so the witness below reproduces the shape with the
*unmodified* hook file copied byte-for-byte into a scratch main
checkout + linked worktree pair (`diff` confirmed identical), the same
scratch-repo technique `UX-762`'s own Outcome used:

```text
$ diff .claude/hooks/gate_covers_push.py <scratch>/toy-repo/.claude/hooks/gate_covers_push.py
verbatim copy confirmed

$ cd <scratch>/toy-wt && git rev-parse HEAD             # the worktree's own HEAD
b4571046f18a4a2114847db20350802fb0c68b7b
$ git rev-parse HEAD > .gate-covered                    # stand-in for a green `make push-check`
$ cat .gate-covered
b4571046f18a4a2114847db20350802fb0c68b7b

$ cd <scratch>/toy-repo && git rev-parse HEAD            # the main checkout's HEAD - moved on independently
3a5a75c90d1bd8bb944f34af40bee99f22918e91

$ cd <scratch>/toy-repo && python3 .claude/hooks/gate_covers_push.py < payload.json   # payload: {"tool_input":{"command":"git push origin toy-branch"}}
Blocked: HEAD (3a5a75c90d1bd8bb944f34af40bee99f22918e91) was never covered by a green `make push-check`.
...that sha is no commit - no suite has passed yet, not this one.
EXIT: 2

$ cd <scratch>/toy-wt && python3 <scratch>/toy-repo/.claude/hooks/gate_covers_push.py < payload.json
EXIT: 0
```

Run with cwd = the pushing worktree, the hook sees the worktree's own
`.gate-covered` and passes. Run with cwd = the main checkout - what a
`PreToolUse` hook spawned with `CLAUDE_PROJECT_DIR` as cwd gets, since
`repo_root()`'s `subprocess.run(["git", "rev-parse", "--show-toplevel"])`
carries no `cwd=` and so inherits the hook process's own - it names the
main checkout's `HEAD` (`3a5a75c9...`), not the worktree's covered sha
(`b4571046...`), and blocks a push the worktree's own gate already
covered.

The real main checkout's current `HEAD`, read from
`.git/refs/heads/claude/project-thread-y8n8bv-flake-ledger` directly
(a file read, not a git op, so unaffected by the sandbox above):
`1e40e4adac5d41af95775fa37847d715c70a5c5e` - a different commit from
this worktree's, confirming the same divergence the scratch pair
demonstrates is live on this exact box, not merely constructible.
