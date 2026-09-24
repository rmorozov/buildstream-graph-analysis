# UX-1001: ninja 1.13's jobserver client is read by its version, not its help text

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-843, UX-846, UX-878 | **Found by:** `UX-905`'s fdsdk auto arm (run 35965495279, 2026-09-24): `Found ninja-1.13.2 at /tmp/.bst-native-trace/wrappers/ninja`, then `lto-wrapper: warning: using serial compilation of 16 LTRANS jobs` on every git-minimal link, and a stall there | **Serves:** R2, R5 (a meson element on a current ninja joins the pool instead of starving it) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`probe_ninja` and the wrapper's own check both call ninja a client only
when `--help` says "jobserver". ninja 1.13.2 is a client (fifo only) and
its help never says so:

```text
$ ninja --version; ninja --help 2>&1 | grep -ci jobserver    # built from the v1.13.2 tag
1.13.2
0
```

So a 1.13 ninja reads as `ninja_wrapper`. The wrapper takes up to
`nproc` tokens and runs `ninja -j <width>`, and an explicit `-j` turns
ninja's client off (`ninja.cc:1724`), while the auth still flows down in
`MAKEFLAGS` to the compilers. On fdsdk's git-minimal the LTO links'
lto-wrapper then meets a pool the wrapper already emptied. A client that
is recognised also needs a `fifo:` auth: 1.13 rejects the pipe style
(`jobserver.cc:193`, "Pipe-based protocol is not supported!").

## Required Fix

`ninja_is_client(version, help)`: help names the jobserver, or the
version is 1.13 or later. `ninja_client` joins `_COMPILER_SAFE_POLICIES`,
so the raw fd becomes `fifo:` (or is scrubbed under a sub-4.4 make).
The wrapper steps aside for ninja 1.13+ on a `fifo:` auth: it holds no
tokens but still strips the recipe's `-j`, since fdsdk's meson recipe is
`ninja -v -j ${JOBS} -C _builddir` with `JOBS` emptied.

## Decomposition

surfaces: `tools/native_trace/bwrap_shim.py`'s ninja probe and `_COMPILER_SAFE_POLICIES`, `tools/native_trace/wrappers/_common.sh`
guards: a version table past 1.13 with 1.13.2's real help text; the probe and the real gate on a fake bwrap; the `MAKEFLAGS` a meson element gets; the wrapper on a real FIFO in three cells (client on fifo, old ninja, client on fd)
gap: whether a recognised client should see a `fifo:` or be scrubbed under a sub-4.4 make; the compiler-safe path already decides that per element
track: session's own - found live on the fdsdk arm, fixed in the thread that read it
gate: its own, then `UX-905`'s auto arm re-run

## Out of Scope

Whether lto-wrapper's own inner `make` joins the pool well (`UX-884`).
The pair reading itself, which is `UX-905`'s.

## Acceptance Test

`tests/unit/test_a_ninja_client_is_read_by_version.py` passes, and a
real ninja 1.13.2 behind the wrapper prints `Jobserver mode detected`
with the pool whole afterwards.

## Outcome

Gap measured, real ninja 1.13.2 behind the wrapper on a 3-token FIFO,
before the fix:

```text
{"event":"acquire","tool":"ninja","pid":6550,"tokens":3,...}
```

After, recipe `ninja -v -j ${JOBS} -C .` with `JOBS=`:

```text
== fifo   ninja: Jobserver mode detected: -j4 --jobserver-auth=fifo:.../js
          tokens unread 3, no ledger line
== fd     {"event":"acquire","tool":"ninja","tokens":3}   (1.13 cannot read a pipe; wrapped as before)
          tokens unread 3
```

`make test`-selected shim, wrapper and ninja files: 765 passed, 22 skipped.

| mutation | reddened | count |
|---|---|---|
| `ninja_is_client` reads the help only | version table, probe, gate, fifo | 7 |
| `ninja_client` out of `_COMPILER_SAFE_POLICIES` | `test_a_client_ninja_is_handed_a_fifo_not_the_raw_fd` | 1 |
| the wrapper ignores the version | the wrapper's `1.13.2`/`fifo` case | 1 |
| the wrapper steps aside on an fd auth | the wrapper's `1.13.2`/`fd` case | 1 |
| the client path keeps the dangling `-j` | the wrapper's `1.13.2`/`fifo` case | 1 |

Deviation: the fixture passes `ninja_probe` from `probe_ninja` on the
fake rather than letting `build_shim_argv` probe; without it the policy
falls back to `cmake_meson` and the fifo case passed unfixed.
