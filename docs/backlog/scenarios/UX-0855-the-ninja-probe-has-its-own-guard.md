# UX-855: the ninja probe has its own guard

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-843 | **Found by:** round 118, UX-843's verifier | **Serves:** R4 (a cmake element joins the jobserver the way its generator can) | **Topic:** guards | **Area:** tools | **Shape:** bounded

## Motivation

`UX-843`'s `probe_ninja` runs the sandbox's own `ninja --version` and
`--help` through bwrap and caches the result per capture; every guard
feeds the decision function a hand-built probe dict, so the probe itself
(exit 127 when the sandbox has no ninja, bwrap failing, the timeout,
the cache hit) is exercised by no test.

## Required Fix

`tests/unit/test_bwrap_shim.py`: `probe_ninja` driven with a fake
`bwrap` on `PATH` (a shell script that echoes a version and a help text,
or exits 127, or sleeps past the timeout) and a scratch cache path: the
four outcomes recorded as the dict the decision function reads, and a
second call served from the cache without running the fake. No change
to the probe unless a case finds one.

## Out of Scope

A real bwrap in a unit test.

## Acceptance Test

The four cases and the cache case green; mutation: skip the cache
write, so the second call runs the fake again - red.
