# UX-852: outstanding tokens are audited against live processes

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 (a killed link does not shrink the pool for the rest of the build) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

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
