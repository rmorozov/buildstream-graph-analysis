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

## Outcome

**Gap measured:** every ninja case in `tests/unit/test_bwrap_shim.py`
fed `kind_job_env`/`build_shim_argv` a hand-built probe dict; no case
called `probe_ninja` itself. `grep -c "probe_ninja(" tests/unit/test_bwrap_shim.py`
before this change: 0.

**Close measured:** 5 cases added, each driving `probe_ninja` with a
fake `real_bwrap` shell script in `tmp_path` (per the decision already
taken, passed straight through as the `real_bwrap` argument, never
placed on PATH) - available+jobserver-client, exit 127, a hang past a
0.2s timeout, a failing bwrap (exit 1, stderr), and a cache hit. `python3 -m
pytest tests/unit/test_bwrap_shim.py -v`: 42 passed in 0.40s (was 37).
No probe change: all three failure paths converge on the same
`{"available": False, "version": None, "jobserver_client": None}` -
none raised, none hung past its timeout, no field was missing.

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| `probe_ninja`'s cache-write body replaced with `pass` | `test_a_second_probe_ninja_call_is_served_from_the_cache_without_rerunning` | 1 failed (`['run', 'run'] == ['run']`); reverted: full file 42 passed |
