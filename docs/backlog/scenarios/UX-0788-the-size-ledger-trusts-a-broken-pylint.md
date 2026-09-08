# UX-788: the size ledger trusts a broken pylint

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-712 | **Found by:** round 109, retro-verifying round 102 | **Serves:** the run where pylint dies and the duplicate count reads zero | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

**Gap measured** (Motivation's own repro, `PYLINT_OK_CODES` branch
swallowed with `sed`): `8 passed` — no fixture drove `pylint` off its
happy path, so a silently zeroed run read as a clean sweep.

**Close measured**, two fixtures added to
`tests/unit/test_the_size_ledger_only_shrinks.py`: a fake `pylint` on
`PATH` (`monkeypatch.setenv("PATH", ...)`) that exits 32 with no
JSON, and one that exits 0 printing non-JSON.

```console
$ python3 -m pytest tests/unit/test_the_size_ledger_only_shrinks.py -q
10 passed
```

**Mutation table**

| mutation | reddened | count |
|---|---|---|
| `PYLINT_OK_CODES` widened to `tuple(range(256))`, and the `json.JSONDecodeError` branch made to return `raw = []` instead of raising | the two new fixtures only, both other 8 green | `2 failed, 8 passed` |

Both fixtures raise `PylintFailure` (`main` exit 2) against the real,
unmutated `dev_sizes.py` too, since neither exit 32 nor non-JSON
output is ever produced by a working `pylint` — the new guards do not
depend on the host's `pylint` behaving.

**Deviation.** Same track and verifier as `UX-787`; `pylint` was already importable, so the brief's install step was not needed. A pylint that exits 0 with `[]` is accepted as zero duplicates — probed, correct.
