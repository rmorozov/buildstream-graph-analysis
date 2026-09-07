# UX-728: a track's repro runs the session's checkout, not its worktree

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-510 (a track's brief names the base it will actually get) | **Serves:** every `implementer` track that reproduces a defect through the CLI | **Topic:** guards | **Shape:** judgement | **Area:** tools

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
guard that refuses a `bga` import resolving outside the tree it is
invoked from is the judgement; the third catches it where it bites and
the first two only tell someone about it.

**The decision, taken here: the third, as a warning at CLI startup,
plus the brief line.** Not a `conftest` guard — this row's own
Motivation measures `pytest` as unaffected, because every test file
derives `REPO` from its own `__file__`. A `conftest` check would run
where the trap is not and stay silent where it is.

The place it bites is the manual CLI repro, so the check belongs at
`bga`'s own startup, and it must be **precise enough to have no false
positive for an ordinary user**: warn only when the current working
directory is inside a checkout of *this* repository and the imported
`bga` package resolves to a *different* checkout of it. A user running
a system install from an unrelated directory is the normal case and
must see nothing.

Warn rather than refuse: the shadowed invocation still produces real
output, and a round that knows what it is doing may want it. What
round 98 lost was not the ability to run the command, it was the
knowledge that the output came from somewhere else — so the sentence
is the fix, and it names both paths.

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

## Outcome

**Gap measured:** before the fix, `bga.cli` printed nothing on any of
the three cwd/import combinations - including the shadowed one, where
`sys.path.insert(0, REPO)` from a fabricated second checkout still ran
silently. `tests/unit/test_a_shadowed_checkout_warns_at_startup.py`
against `git show HEAD:bga/cli.py` confirms: `test_warns_when_cwd_is_a_different_checkout`
fails (`assert 'UX-728' in ''`) on the pre-fix module.

**Close measured:** `_checkout_root` walks up from cwd for
`bga/__init__.py` beside a `pyproject.toml` naming `bga` - no
subprocess. Startup, `python -m bga.cli --version`, n=30:
before `mean=0.2179 median=0.2120`; after `mean=0.2270 median=0.2094`
(re-check `mean=0.2233 median=0.2168`) - inside run-to-run noise, no
`git` spawn added. The three guard cases all pass:
`test_warns_when_cwd_is_a_different_checkout`,
`test_silent_when_cwd_and_import_agree`,
`test_silent_when_cwd_is_not_a_checkout_at_all` - 3 passed in 0.93s.
`make test-touching`: 144 files, 2887 passed, 72 skipped. `make lint`
clean.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| drop the call to `_maybe_warn_wrong_checkout()` in `_run` | the mismatch case (`UX-728` absent from stderr) | 1 failed, 2 passed |
| `import_root == cwd_root` → `!=` | the mismatch case (now silent) and the agreement case (now warns) | 2 failed, 1 passed |
| drop the `cwd_root is None` guard | the unrelated-cwd case (warns with `at None`) | 1 failed, 2 passed |

Reverted each from a scratchpad copy, not `git checkout`; all three
green after revert.
