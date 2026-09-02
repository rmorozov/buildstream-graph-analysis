# UX-522: the selector runs last, and carries the census

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-500 (the measurement this changes the odds of), UX-336 (`dev_touching`) | **Serves:** the implementing session, at the commit it is about to make | **Topic:** guards

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
