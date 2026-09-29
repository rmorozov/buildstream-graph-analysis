# UX-1114: a fresh session starts shallow and without the locked dependencies

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** quality gates audit (`docs/audits/quality-gates-2026-09-29.md`, 2026-09-29) | **Serves:** every thread that opens a new container | **Topic:** guards | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_a_session_starts_ready.py, absent from tests/

## Motivation

The container this audit ran in was a shallow clone without `networkx` or
`zstandard`: `git fetch --unshallow` 10 s, `pip install --ignore-installed
PyYAML -r requirements.lock` 14 s. Project memory records the same
rediscovery at least three times (the shallow conflict matrix, `zstandard`
after #260, networkx in round 150), and history-reading guards need depth.

## Decision

Architect, round 151 (2026-09-29):

```text
Route:     new `.claude/hooks/session_start.py` behind `session-start.sh`, registered under `SessionStart` (matcher "startup", timeout 120): exit 0 doing nothing in a linked worktree (`agent_worktree_limits.is_linked_worktree`, UX-1041); else `git fetch --unshallow` if shallow, and `pip install --ignore-installed PyYAML -r requirements.lock` if `dev_env_check.missing_locked()` (new, pure: importlib.metadata against the `==` pins) names any; `pip install -e . --no-deps` only when `bga` will not import, from the main root. One line printed, always exit 0
Rejected:  logic in the .sh (untestable); relying on the PreToolUse worktree hook (it does not see a SessionStart subprocess); reporting without installing (3 rediscoveries measured)
Files:     .claude/settings.json, .claude/hooks/session-start.sh, .claude/hooks/session_start.py, tools/dev_env_check.py, tests/unit/test_a_session_starts_ready.py
Guard:     on a `git clone --depth 1 file://` scratch repo with an installer stub: unshallow after; a second run prints "nothing to do"; a linked worktree does nothing; a raising installer still exits 0 (medium)
Mutation:  drop the unshallow branch; drop the worktree early exit - each reddens
Class:     optimization - ~24 s per fresh container plus the rediscovery turns
```

## Required Fix

A `SessionStart` hook in `.claude/settings.json` unshallows when
`git rev-parse --is-shallow-repository` says true and installs
`requirements.lock` when `dev_env_check.py` reports a missing package; it
prints one line of what it did and never fails the session.

## Out of Scope

Installing non-Python tools (bst, bwrap, node).

## Acceptance Test

`tests/unit/test_a_session_starts_ready.py` runs the hook against a
shallow scratch clone and asserts it leaves it unshallow, and that a second
run does nothing. Mutation: drop the unshallow branch; it reddens.

## Outcome

**The gap measured:** a `git clone --depth 1` scratch repo reports
`--is-shallow-repository` true; no hook registered under `SessionStart`.

**The close measured:** `pytest tests/unit/test_a_session_starts_ready.py`:
6 passed (unshallow + second run "nothing to do", lock install via stub,
linked worktree nothing, raising installer returns a line, shell entry
exits 0, `missing_locked`). 12 touching files: 280 passed, 3 skipped.
`missing_locked` counts absent pins only, not version drift (a drift
would reinstall at every start).

| Mutation | Reddened | Printed |
|---|---|---|
| unshallow branch `if False and installer(...)` | `test_a_shallow_clone_is_unshallowed_and_a_second_run_does_nothing` | 1 failed, 5 passed |
| worktree early exit `if False:` | `test_a_linked_worktree_does_nothing` | 1 failed, 5 passed |

Files as Decided: settings.json, session-start.sh, session_start.py,
the test (`missing_locked` lives in `session_start.py`; `dev_env_check.py` is at its size ceiling).

Deviation: `missing_locked` lives in `session_start.py`, not
`dev_env_check.py` (at its size ceiling), and counts only absent pins.
`tests/quality_baseline.json` gained 2 ruff S603 entries via
`dev_baseline.py --write --force --reason UX-1114`; that write flipped
`ruff_version` to the stale 0.15.8, restored by hand to 0.16.8.
