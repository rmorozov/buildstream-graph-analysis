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

## Outcome

**Gap measured.** `UX-679`'s Outcome named it outright: "the tracer's
FIFO lifecycle, unguarded today (the verifier's mutation passed its
suite)". `open_jobserver`/`close_jobserver` now exist as the named
pair; `run_traced_build`'s `finally` (already wrapping the build) calls
`close_jobserver`, and `open_jobserver` self-cleans and raises on a
seed mismatch rather than leaving a half-seeded FIFO for the caller to
find. The auth style is chosen by `jobserver_auth_style(requested,
make_version_output)`, resolved once in `main` from the host's own
`make --version` (this box: GNU Make 4.3, so `auto` → `fd`, matching
the Required Fix's stated reading) and threaded through
`BST_TRACE_JOBSERVER_AUTH` to the shim, which injects `fifo:<path>` +
a `--bind` of the FIFO onto itself, or the existing `<fd>,<fd>`.

**Close measured**, `PYTHONDONTWRITEBYTECODE=1 python3 -m pytest tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py -q`:

```text
tests/unit/test_the_jobserver_fifo_has_a_lifecycle.py ........  [100%]
============================== 8 passed in 0.69s ===============================
```

`tests/unit/test_bwrap_shim.py`'s existing two jobserver cases needed
no signature change (16/16 still pass). A live run,
`--jobserver 4` on `examples/06-macro-micro-optimization`'s `core.bst`
(host GNU Make 4.3, `bst` reached via a subprocess wrapper - direct
invocation refuses with `stdout … O_NONBLOCK` in this sandbox): exit 0,
report carries `"jobserver": 4, "jobserver_auth": "fd"`, per-element
native parallelism `peak 2 req 1 achieved 200%` on the pinned
(`notparallel`) `core.bst` - the spike's known pin gap (`UX-845`), out
of this row's scope.

**Mutation table**, `falsify` skill, reverted from the scratchpad copy each time:

| mutation | reddened | revert |
|---|---|---|
| `open_jobserver`: `tokens = n - 1` → `tokens = n` | `test_a_pool_of_4_holds_three_readable_tokens_and_removes_on_close`, `test_a_pool_of_1_writes_zero_tokens` (2 failed) | green, 8/8 |
| `close_jobserver`: `os.remove(path)` skipped | `test_a_pool_of_4_holds_three_readable_tokens_and_removes_on_close` (1 failed) | green, 8/8 |

The "build that raises" test did not redden under the second mutation:
`run_traced_build`'s own scratch (`capture_scratch`) removes the whole
tree in its own `finally` regardless, masking a `close_jobserver` that
skipped its `os.remove`. The direct `open_jobserver`/`close_jobserver`
test is what actually discriminates that mutation; the raises-test's
job is proving the *try/finally shape*, not this specific line.
