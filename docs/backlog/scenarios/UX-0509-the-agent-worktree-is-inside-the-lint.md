# UX-509: a parallel track's worktree is inside the tree that lints it

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-504` (the agent that runs in one) | **Found by:** round 75, three tracks in flight at once | **Serves:** the orchestrating session whose `make lint` is red on a file it did not write | **Topic:** guards

## Motivation

`UX-504`'s `implementer` runs in a worktree, and the Agent tool puts
that worktree at `.claude/worktrees/agent-<id>/` — **inside** the
repository. `lint-docs` scans `.claude/` recursively, so the
orchestrator lints every track's working copy:

```text
$ make lint
.../.claude/worktrees/agent-af3da166d3b53f87c/examples/README.md:248:1:
    MD040: Fenced code blocks should have a language specified
.../.claude/worktrees/agent-af3da166d3b53f87c/examples/README.md:260:1:
    MD040: Fenced code blocks should have a language specified
make: *** [Makefile:102: lint-docs] Error 1
```

Neither file is in the orchestrator's diff. Scanning only its own tree
is clean:

```text
$ python3 -m pymarkdown --config .pymarkdown.json scan -r README.md \
    CLAUDE.md REVIEW.md docs/ .claude/agents .claude/skills .claude/hooks
$ echo $?
0
```

Nor is the directory ignored, so `git status` carries `?? .claude/worktrees/`
for as long as a track runs and `git add -A` would commit another
branch's working copy — the hook `UX-485` added refuses that, which is
the only reason this cost nothing worse.

The blast radius is exactly `lint-docs` plus `git status`: the one guard
that globs from the repository root
(`test_the_register_is_terse.py`) is scoped to `tools/dev_*.py` and
`.claude/hooks/*.py`, and `dev_touching` reads `tests/` only.

## Required Fix

- `.gitignore` names the worktree directory, so `git status` is clean
  and a bulk add cannot reach it.
- `lint-docs` reads that same list rather than a second copy of it —
  `--respect-gitignore` — so a future ignored directory is excluded
  once, not twice.
- A guard that reddens if either half goes: an ignored markdown file
  under the worktree directory must not appear in the lint's own file
  list, and a tracked one under `.claude/` must.

## Out of Scope

- Where the Agent tool puts a worktree. That is the tool's, not this
  repository's, and the fix above holds wherever it puts it as long as
  the path is ignored.
- The stale base a worktree starts from, which is `UX-510`.

## Acceptance Test

`make lint` clean with a markdown file present under
`.claude/worktrees/` that would fail it, and the same file absent from
`pymarkdown scan -l`'s list.

## Outcome

**Round 75, 2026-09-02.** Found while three `implementer` tracks were in
flight — the first time `UX-504`'s agent ran for real.

**The gap, measured.** `make lint` on a tree whose own documents are
clean:

```text
.../worktrees/agent-af3da166d3b53f87c/examples/README.md:248:1: MD040 ...
.../worktrees/agent-af3da166d3b53f87c/examples/README.md:260:1: MD040 ...
make: *** [Makefile:102: lint-docs] Error 1
```

and the same scan over this tree's own directories, `exit 0`. The
worktrees are 3 whole clones at `.claude/worktrees/agent-<id>/`, and
`git status` carried `?? .claude/worktrees/` throughout.

**The close.** `.gitignore` names the directory; `lint-docs` gains
`--respect-gitignore` so it reads that one list rather than a second
copy. The file set is unchanged by the flag — **655 files before, 655
after**, `comm` empty in both directions — so the flag costs nothing
beyond the exclusion it is for.

```text
$ mkdir -p .claude/worktrees/agent-probe && printf '# probe\n\n```\nx\n```\n' \
    > .claude/worktrees/agent-probe/PROBE.md
$ make lint
All checks passed!
exit=0
```

**Mutations.** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__` cleared.

| # | mutation | reddened | count |
|---|---|---|---|
| N1 | `.gitignore` stops naming the directory | `..._git_ignores_the_worktree_directory`, `..._not_listed` | 2 failed, 1 passed in 8.03s |
| N2 | the recipe drops `--respect-gitignore` | `..._reads_that_same_list`, `..._not_listed` | 2 failed, 1 passed |
| N3 | the recipe stops reading `.claude/` at all | `..._not_listed` | 1 failed, 2 passed |

N1's own runtime is the finding twice over: 8.03s against 1.64s green,
because the un-ignored scan walks three clones.

**Blast radius, checked rather than assumed.** One guard globs from the
repository root — `test_the_register_is_terse.py`, scoped to
`tools/dev_*.py` and `.claude/hooks/*.py` — and `dev_touching` reads
`tests/` only. So `lint-docs` and `git status` were the whole of it.

**Deviation from the Required Fix:** none.

**Tier and suite.** New file `test_the_lint_reads_its_own_tree.py`, 1.64s
— small by default, no `tiers.py` row. `make test-touching`, `make test`
and `make lint` are in the round's own record below the batch.
