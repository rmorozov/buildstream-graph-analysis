# UX-1006: a wrapped ninja hands gcc a fifo path, not a blocking fd pair

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-846, UX-878, UX-1001 | **Found by:** the fdsdk hang's local reproduction (2026-09-24): gcc 16.2 and 13.3 `lto1` deadlock on a raw `--jobserver-auth=R,W` pair whose descriptors are blocking, and never on a `fifo:` path | **Serves:** R2 (an LTO element under an old ninja finishes) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`ninja_wrapper` passes the pool's raw fd pair through, and ninja never
touches the descriptors, so gcc's `lto1` inherits them blocking. Staged
gcc 16.2.0 (nixos-unstable) and host gcc 13.3, 40 objects, 16 LTRANS
partitions, `timeout 120`:

```text
fifo:PATH, 0 tokens, 5 links in parallel       exit 0, 30-31s (serial on the implicit slot)
make 4.4.1 / 4.3 -j4 own pool, 4 links         exit 0, 24-25s
ninja 1.13.2 client, fifo:, 0 tokens           exit 0, 93s
--jobserver-auth=3,9 blocking, 0 tokens        HANG, exit 124
--jobserver-auth=3,9 blocking, 3 tokens        HANG, exit 124, 3 zombies
gcc 13, 3,9 blocking, 0 or 3 tokens            HANG both
```

`lto1` (WPA, `-fwpa=jobserver`) takes a token, forks a streaming child
and reads again; on the blocking pair the read never returns and the
children are never reaped, so their tokens never come back. That is the
fdsdk witness exactly: `anon_pipe_read`, fds 3 and 9 on the pool,
zombies. `UX-1001` fixed fdsdk by giving ninja 1.13 a `fifo:` path; an
older ninja behind the wrapper still hands gcc the pair.

## Decomposition

surfaces: `_COMPILER_SAFE_POLICIES` in `tools/native_trace/bwrap_shim.py`
guards: an old ninja behind the wrapper gets `fifo:`; under a sub-4.4 make both the auth and the emptied `JOBS` drop
gap: none - the wrapper already reads a `fifo:` auth (`_common.sh`), guarded in `UX-1001`'s wrapper cells
track: session's own
gate: its own

## Required Fix

`ninja_wrapper` joins `_COMPILER_SAFE_POLICIES`: the raw fd becomes
`fifo:`, or is scrubbed with `JOBS` under a sub-4.4 make.

## Out of Scope

A make-kind element's LTO links (`UX-884`).

## Acceptance Test

`tests/unit/test_a_wrapped_ninja_hands_gcc_a_fifo.py` passes.

## Outcome

Gap measured: the table above, from reproduction scripts kept outside
the repository (one opens a FIFO blocking on fds 3 and 9 and links under
`MAKEFLAGS=-j4 --jobserver-auth=3,9`).

Close: `build_shim_argv` for a meson element on ninja 1.11.1 with a
wrapper dir now reads `MAKEFLAGS=--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver`;
shim, wrapper and ninja tests: 767 passed, 22 skipped.

| mutation | reddened | count |
|---|---|---|
| `ninja_wrapper` out of `_COMPILER_SAFE_POLICIES` | both cases | 2 |

Deviation: `UX-1001`'s Motivation blamed the wrapper's held tokens; the
pair deadlocks with 3 tokens in the pool too, so the `fifo:` path, not
the released tokens, is what fixed fdsdk.
