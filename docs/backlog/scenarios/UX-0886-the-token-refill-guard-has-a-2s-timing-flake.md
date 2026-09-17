# UX-886: the token-refill guard has a 2s SIGKILL-timing flake

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-852 | **Found by:** round 125 (PR #235 test 3.11 went red on `test_a_leaked_token_is_refilled::test_sigkilled_holder_is_refilled_and_named` with `assert 0 == 1`, while 3.9/3.10/3.12 passed the same commit and the local gate was green — a confirmed timing flake, re-run passed) | **Serves:** the pipeline (a green suite means green, not "green four times out of five") | **Topic:** guards | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

`test_sigkilled_holder_is_refilled_and_named` (UX-852,
`test_a_leaked_token_is_refilled.py`) SIGKILLs a token holder and asserts
`PoolController.audit_leaks` refills and names the leaked token. It hinges
on a **2-second** window for the kill + reap + audit to settle; on a
loaded CI runner (round 125 saw it on the 3.11 shard only, the other
three Python shards green on the same sha) the audit ran before the reap
landed → `assert 0 == 1`. A re-run passed. This is a real timing flake in
the guard, not a defect in `audit_leaks`.

## Required Fix

Make the guard deterministic: poll for the reap with a bounded retry
instead of a fixed 2s sleep (wait up to N seconds for the killed pid to be
reaped, then audit), or drive the audit off an explicit reap signal rather
than wall-clock. The assertion about *refill + naming* is the real claim;
the timing is incidental and must not gate. Record the incident in the
flake ledger (`docs/audits/` — the round-125 3.11 red, the same-sha
green shards, the passing re-run) so a future flake on this guard is a
second data point, not a first.

Surfaces: `tests/unit/test_a_leaked_token_is_refilled.py` (the wait), the
flake ledger doc under `docs/audits/`.

## Decomposition

surfaces: `tests/unit/test_a_leaked_token_is_refilled.py` · `docs/audits/<flake-ledger>.md`
guards: the fixed test is its own guard — run it under artificial scheduling delay (a slow reap) and confirm it still passes deterministically
gap: the flake ledger may not exist yet as a doc — if not, this filing starts it (a round-125 row) per the process
track: bounded `implementer`
gate: a later round (filed this round, not built)

## Out of Scope

`audit_leaks` itself (it is correct — the flake is the guard's timing).
Other tiers' timing budgets.

## Acceptance Test

The rewritten guard passes deterministically when the killed holder's reap
is artificially delayed within the bound, and still reddens if
`audit_leaks` genuinely fails to refill. Mutation: break the refill in
`audit_leaks` — the guard reddens (proving it still guards the real
claim, not just the timing).

## Outcome

_(filed round 126, not built — deferred)_
