# UX-852: outstanding tokens are audited against live processes

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-845, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 (a killed link does not shrink the pool for the rest of the build) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

A client killed between acquire and release never returns its token:
`SIGKILL` on a linker, an OOM kill, a `bst` interrupt. The pool shrinks
by one for the rest of the build and nothing says so. The hook already
records every process exit with its pid.

## Required Fix

`tools/bst_native_build_tracer.py`: the ledger (`UX-845`) records who
holds what - the wrappers write their pid with each acquire; every
second the server compares outstanding tokens against the pids the
hook has seen exit and refills each token whose holder is gone,
recorded as `leaked` with the pid and the tool; the report's
`jobserver` block counts leaks.

## Decomposition

Input classes: a wrapper killed by `SIGKILL`, a sub-make killed, a
clean build (zero leaks); the journey it extends is R4's interrupted
capture.

## Out of Scope

Tokens held by processes the hook does not see (a static binary
without the hook) - counted as unknown, not refilled.

## Acceptance Test

`tests/unit/test_a_leaked_token_is_refilled.py` kills a fake holder
and asserts the pool is back to its count within two seconds; mutation:
refill unconditionally - red on the live-holder case.

## Outcome

**Gap measured.** `PoolController` (UX-845) tracked its own moves but
never read a wrapper's own `acquire`/`release` rows (UX-846) - a
`SIGKILL`ed wrapper (its trap never runs) held its tokens for the rest
of the build with nothing to say so. `git grep -n "def audit_leaks"
tools/bst_native_build_tracer.py` before this change: no match.

**Close measured**, `PYTHONDONTWRITEBYTECODE=1 timeout 120 python3 -m
pytest -q tests/unit/test_a_leaked_token_is_refilled.py
tests/unit/test_the_pool_follows_the_machine.py
tests/unit/test_a_held_tool_returns_its_tokens.py`:

```text
tests/unit/test_a_leaked_token_is_refilled.py ......                     [ 22%]
tests/unit/test_the_pool_follows_the_machine.py ..........               [ 59%]
tests/unit/test_a_held_tool_returns_its_tokens.py ...........            [100%]

============================== 27 passed in 7.64s ==============================
```

**Mutation verified red and reverted (1):** `_holder_is_gone` returns
`True` unconditionally (refill regardless of liveness).

| mutation | reddened | revert |
|---|---|---|
| `_holder_is_gone` always `True` | `TestALiveHolderKeepsItsTokens::test_a_sleeping_holder_is_left_alone` (live holder's 2 tokens refilled anyway: `4 == 2` failed) and `TestOutstandingPidsAreCheckedIndependently::test_the_live_pid_is_kept_the_dead_one_is_refilled` (this test's own alive pid refilled too) | green, 6/6, from the pre-mutation copy |

`python3 tools/dev_baseline.py --check`: exit 0, no `new:` line.
`make lint`: exit 0, ruff and pymarkdown both clean.

Deviation (merge): `stop()` now joins the audit thread twice and folds
its liveness into `controller_stopped` (the verifier read a single 3 s
join that never fed the flag); a pid reused by an unrelated live
process is left alone for good - the accepted limit of `os.kill(pid, 0)`
as the liveness test - and the `EAGAIN` retry on a full FIFO stays
unguarded.
