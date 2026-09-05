# UX-522: the selector runs last, and carries the census

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-500 (the measurement this changes the odds of), UX-336 (`dev_touching`) | **Serves:** the implementing session, at the commit it is about to make | **Topic:** guards | **Area:** tools

## Motivation

Round 75 ran `UX-500`'s Regime A and recorded why the cheap gate did
not earn a place as the only gate:

```text
defects caught by the per-item make test            5
  of which test-touching's set could not name       2   (UX-503's register cap, UX-502's skip census)
test-touching run before the final edit             yes — the close, the Outcome, the row move came after
```

Both misses are the same class: a **census guard** reads the whole
tree (the register cap, the skip census, the index counts, the context
map, the docs links) and names no module, so a grep from the diff can
never select it. And the selector's *timing* is a habit, not a
mechanism — nothing runs it after the last edit, so the last edit is
the one it never sees.

## Required Fix

- `dev_touching.py` unions its grep set with a fixed **census set**:
  the guard files that read the tree rather than a module (declared
  in `tests/tiers.py` beside the tiers, or by a marker the files
  carry), so every `test-touching` run includes them. Measured cost
  to state: the census set's seconds at `-n auto`.
- A `PreToolUse` hook on `git commit` (matcher `Bash`, tokenised
  like `no_bulk_add.py`) that runs `make test-touching` on the staged
  diff and blocks the commit on red — the selector at the one moment
  it cannot be skipped. `PYTEST_XDIST=` respected; a `--no-verify`
  equivalent stated in the hook's message for the case where the
  commit *is* the fix to a red guard.
- Re-count the miss rate on the next Regime-A round: the two classes
  above should read zero.

## Out of Scope

- Replacing the per-item suite — that is `UX-500`'s decision, on
  its numbers; this changes what the cheap gate can see.
- A coverage-derived selection map — `UX-524`.

## Acceptance Test

`make test-touching` on a diff touching only `docs/` runs the census
set; a commit with a red census guard is blocked with the guard's
name in the message. Mutations: drop a file from the census set —
the declaration guard reds; commit with the hook disabled — allowed,
and the hook's own guard in `test_the_agent_configuration_holds.py`
reds when `settings.json` stops declaring it.

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

The census set is **derived**, not typed — a guard that walks a path
rooted at the repository (AST, not grep) and that no diff points at:

```text
guards that walk a repository tree                      35
  of which a grep from some source module reaches       24
census                                                  11
```

Both of round 75's misses are in the eleven — the second only after a
defect in the selector itself: `tokens_for` emitted `__init__` as a
bare stem, so **fifteen `__init__.py` files each "selected" a guard
about skip reasons**.

### After

```text
$ dev_touching.select(["docs/guides/cli.md"])   23 files, 11 by census
$ pytest <the 11> -q -n auto                    272 passed in 10.80s
```

The hook, on a staged one-file diff:

```text
$ echo '{"tool_input":{"command":"git commit -m x"}}' | .claude/hooks/selector-before-commit.sh
Blocked: `make test-touching` is red on the tree you are committing.
FAILED test_the_register_is_terse.py::...[tools/dev_touching.py]
FAILED test_the_agent_configuration_holds.py::...::test_every_script_on_disk_is_declared
                  2 failed, 183 passed, 3 skipped in 29.58s   exit 2
```

Those two are not the planted defect: they are **this item's own
commit**, caught by its own hook.

### Mutations verified red and reverted (10)

| # | mutation | red |
|---|---|---|
| M1 | a census file is dropped | 3 |
| M2 | the census is not unioned | 3 |
| M3 | `--why` forgets which set chose it | 2 |
| M4 | `__init__` is a token again | 2 |
| M5 | a non-walker is padded into the census | 1 |
| M6 | the hook sees no commit | 5 |
| M7 | the hook fires on everything | 1 |
| M8 | the escape hatch is gone | 1 |
| M9 | `settings.json` stops declaring it | 2 |
| M10 | the hook reads its own path for the repo | 1 |

M7 and M8 were green on their first writing: the clauses drove
`is_git_commit` rather than `main`, and the one that fired the real
hook did it on a **clean index** — nothing staged, so it returns 0
whatever the matcher and the hatch do. Driving `main` with the
selection and the run replaced discriminates both.
`test_nothing_is_declared_that_the_grep_already_reaches` was withdrawn:
it reddened when a guard's prose mentioned `dev_touching`. M10 is a
defect a parallel track found before this landed - the hook resolved
the repository from its own path, which in a worktree is the
**shared** checkout, 8 changed files reported into a tree with 2.

### Deviation from the Required Fix

One: the hook's blast radius. `dev_touching` returns **every** file
when the shared harness changes — `tests/tiers.py` is in `EVERYTHING`,
and this commit touches it. Measured there: 1,596 tests, **450s**, a
timing guard reddening under this round's parallel tracks. A hook that
costs seven minutes and can fail on load gets deleted, so it judges the
**staged** diff (`--staged`, new) and stands down above 120 files.

```text
=== 8 failed, 5944 passed, 27 skipped in 990.42s ===  (load average 12)
Seven were the row this commit moves. The eighth ranks a real `bst`
build's savings and loses `core.bst`'s lead under this round's four
parallel tracks - `UX-538`.
ruff check bga/ tools/ tests/ .claude/hooks/  ->  All checks passed!
```
