# UX-788: the size ledger trusts a broken pylint

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-712 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the run where pylint dies and the duplicate count reads zero | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`tools/dev_sizes.py` `duplicate_blocks` raises `PylintFailure` when
the exit code is outside `PYLINT_OK_CODES`, and parses JSON beside it:

```console
$ sed -i 's/if run.returncode not in PYLINT_OK_CODES:/if False:/' tools/dev_sizes.py
$ python -m pytest tests/unit/test_the_size_ledger_only_shrinks.py -q
8 passed
```

No fixture makes pylint fail, so a silently swallowed run — zero
duplicates, every cell "shrank" — passes the guard that exists to
notice it. `bandit`'s S603 entry for this file's `subprocess.run` is
the only thing in the tree that knows the call is there.

## Required Fix

A fake `pylint` on `PATH` in
`tests/unit/test_the_size_ledger_only_shrinks.py` that exits 32 with
no JSON: `duplicate_blocks` raises `PylintFailure`; a second that
prints non-JSON at exit 0: raises too.

## Out of Scope

- Making pylint a default dependency — `UX-712`'s Outcome declined it.

## Acceptance Test

`tests/unit/test_the_size_ledger_only_shrinks.py` reds under the mutation
`PYLINT_OK_CODES` widened to every code; green restored.

## Outcome

_Not started._
