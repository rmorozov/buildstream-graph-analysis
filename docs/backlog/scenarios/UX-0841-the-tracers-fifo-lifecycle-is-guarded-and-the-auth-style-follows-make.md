# UX-841: the tracer's FIFO lifecycle is guarded, and the auth style follows `make`

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-679 (the spike) | **Found by:** round 117, Direction 20 | **Serves:** R4, before any jobserver capture is trusted | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-679`'s Outcome closes on its own gap: `tools/bst_native_build_tracer.py`
makes the FIFO, writes `N-1` tokens, exports `BST_TRACE_JOBSERVER` and
removes it after the build (`:1112-1121`, `:1192-1195`), and no guard
reads any of it - the verifier's mutation passed the suite. GNU Make
4.3 on this box accepts only the fd style of `--jobserver-auth`; 4.4
adds `fifo:PATH`, which survives an `env -i` and a tool that closes
inherited fds.

## Required Fix

`tools/bst_native_build_tracer.py`: the jobserver block becomes one
function (`open_jobserver(n, scratch)` returning the FIFO path, the fd
and the token count) with a matching `close_jobserver`; the token count
written equals `N-1` and is asserted after the write by reading the
FIFO's readable bytes; the auth style is chosen by the sandbox's
`make --version` (fd for < 4.4, `fifo:` from 4.4) and recorded in the
report as `jobserver_auth`. `tools/native_trace/bwrap_shim.py` binds
the FIFO path in when the style is `fifo:`.

## Decomposition

Input classes: `N` of 1 (an empty pool - only implicit tokens), 4, and
64; make 4.3 and 4.4 (the style); a build that exits before the
teardown (the FIFO removed by the finally). The journey it extends is
R4's `capture run --jobserver` on examples/06.

## Out of Scope

The dynamic pool (`UX-845`) and the leak audit (`UX-852`); this row
guards what the spike wrote.

## Acceptance Test

`tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py`: opens a pool
of 4 in a temp dir, reads three `+` bytes back, closes, asserts the
path is gone; the shim's argv carries `fifo:` for a 4.4 version string
and `<fd>,<fd>` for 4.3; mutation: write `N` tokens instead of `N-1` -
red; skip the `os.remove` - red.
