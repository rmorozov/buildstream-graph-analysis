# UX-854: a proxy token held by a killed job is audited too

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-849, UX-852 | **Found by:** round 118, UX-849's verifier | **Serves:** R4 (a killed link does not shrink the pool for the rest of the build) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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

## Out of Scope

A token held by a client the hook never saw (a static binary without
the hook) - counted unknown, not refilled, as `UX-852` says.

## Acceptance Test

`tests/unit/test_the_broker_grants_by_slack.py` gains a case: a proxy
granted 3, a fake holder reads 2 and is killed; after `note_done` the
global FIFO reads its full count and one `leaked` row names the element
with 2 tokens; mutation: drain only the readable bytes - red.
