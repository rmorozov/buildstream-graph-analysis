# UX-854: a proxy token held by a killed job is audited too

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-849, UX-852 | **Found by:** round 118, UX-849's verifier | **Serves:** R4 (a killed link does not shrink the pool for the rest of the build) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-852` audits the wrappers' acquire rows against live pids and
refills a gone holder's tokens. `UX-849`'s proxies have no audit: a job
that read tokens from its element's proxy and was killed before
returning them leaves them in no pipe - `note_done` drains only what is
still readable, so the global pool shrinks for the rest of the build.
The wrappers already write the pid beside every acquire.

## Required Fix

`tools/bst_native_build_tracer.py`: the broker's grant count for an
element against the proxy's readable bytes plus the wrappers'
outstanding acquire rows for that element is the invariant; at
`note_done`, and on every audit tick for a running element whose
acquire holders are all gone, the difference is written back to the
global FIFO and recorded as a `leaked` row naming the element - the
row `UX-852` writes, with `element` beside `pid`. `jobserver_pool.broker`
counts `leaks`.

## Decomposition

Input classes: a holder killed before `note_done`, a holder killed
while its element runs on, a live holder, a pid no element maps to;
the journey it extends is R4's interrupted capture under a plan.

## Out of Scope

A token held by a client the hook never saw (a static binary without
the hook) - counted unknown, not refilled, as `UX-852` says.

## Acceptance Test

`tests/unit/test_the_broker_grants_by_slack.py` gains a case: a proxy
granted 3, a fake holder reads 2 and is killed; after `note_done` the
global FIFO reads its full count and one `leaked` row names the element
with 2 tokens; mutation: drain only the readable bytes - red.

## Outcome

**The gap measured** (`TestLeaks::test_a_dead_note_done_holder_is_
refilled_to_the_global_fifo` against `note_done` with the leak-refill
block stubbed out - `assert _readable(global_fd) == before + 3`):

```text
E   AssertionError: 1 drained + 2 leaked = the full grant
E   assert 5 == (4 + 3)
```

**The close measured** (same test against the real fix, plus the
tick-case, live-holder, unmapped-pid, exclusive-audit and poll-refresh
cases; the three other cited guard files unaffected):

```text
tests/unit/test_the_broker_grants_by_slack.py .............  [100%]
13 passed in 0.59s
tests/unit/test_a_leaked_token_is_refilled.py ......
tests/unit/test_the_pool_follows_the_machine.py ...........
tests/unit/test_the_pool_withholds_for_memory.py .........
39 passed in 5.00s
```

**Mutation table** (verifier HOLD, points 1-2 added after the first pass)

| mutation | reddened | count |
|---|---|---|
| `note_done`: drop the leftover-refill block (drain only readable bytes) | `TestLeaks::test_a_dead_note_done_holder_is_refilled_to_the_global_fifo` | 1 failed, 12 passed |
| `_audit_wrapper_leaks`: log the tick `leaked` row under `"leak"` not `"leaked"` (never closes the pid - a second `tick()` refills it again) | `TestLeaks::test_a_dead_tick_holder_mapped_to_a_running_element_is_refilled_to_its_proxy` | 1 failed, 12 passed |
| `audit_leaks`: ignore `broker_owns_audit` (both auditors run) | `TestExclusiveAudit::test_the_broker_is_the_sole_auditor_when_one_exists` | 1 failed, 12 passed |
| `_maybe_refresh_pid_to_element`: made a no-op | `TestPollRefreshesPidToElement::test_poll_maps_a_dead_holders_pid_and_refills_its_proxy` | 1 failed, 12 passed |

All four reverted from pre-mutation copies saved to the scratchpad;
`git diff --stat`/`grep MUTATION` after each revert showed nothing
remaining, and the full guard file returned to 13 passed each time.

Deviation (merge): the verifier held once - the pool's audit and the
broker's could both refill one dead holder, and the once-a-second
refresh was unguarded; one auditor per capture now (the broker when a
plan runs), both guarded on the track; pids the hook never saw stay
with UX-852's rule.
