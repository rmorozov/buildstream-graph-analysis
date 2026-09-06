# UX-728: a track's repro runs the session's checkout, not its worktree

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-510 (a track's brief names the base it will actually get) | **Serves:** every `implementer` track that reproduces a defect through the CLI | **Topic:** guards | **Shape:** judgement | **Area:** tools

## Motivation

Two of round 98's three tracks lost time to the same trap, and one of
them shipped a measurement it had to throw away.

`bga` is installed editable against the session's checkout. A track
works in `.claude/worktrees/agent-<id>/`, and Python's `-m` and the
console script both resolve `bga` to the **install**, not the worktree,
unless cwd is the worktree itself:

```console
$ cd /tmp && python3 -c "import bga.report.text as m; print(m.__file__)"
/home/user/buildstream-graph-analysis/bga/report/text.py   # the session's
```

`UX-724`'s track ran its first post-fix repro this way, saw the old
output, and read it as "the fix did nothing". It caught the shadowing
only by printing `__file__` across two cwds. `UX-725`'s track hit the
neighbouring shape — `cd`-ing to the session path for git commands that
looked like they were acting on its own worktree.

`pytest` is unaffected: every test file derives `REPO` from its own
`__file__`, so a guard run inside a worktree reads that worktree.
The trap is exactly the *manual* repro — which is the step a track is
told to do first, and the step whose output lands in an Outcome.

## Required Fix

The `implementer` skill's brief template says how a track invokes the
tool it is changing — `PYTHONPATH=<worktree> python3 -m bga.cli`, or
cwd pinned to the worktree — and says why, in one line. Whether that
belongs in the skill, in `dev_track_brief`'s generated text, or in a
`conftest`-style guard that refuses a `bga` import resolving outside
the tree it is invoked from is the judgement; the third catches it
where it bites and the first two only tell someone about it.

## Out of Scope

- Making the editable install per-worktree. **Declined**: it would put
  a second install in every track's environment for a trap that one
  line of brief text avoids, and `UX-336` already measured what extra
  per-track setup costs the loop.
- The `cd`-away-from-the-worktree shape `UX-725`'s track hit. Same
  root cause in prose, but it is a permission/classifier interaction
  and not this row's; file it if it recurs.

## Acceptance Test

A track's brief, generated or written, names the invocation that reads
the worktree; or a guard refuses a `bga` import whose `__file__` is
outside the repository root the caller resolved. Mutation: drop the
line, or the check — red, naming the resolved path.
