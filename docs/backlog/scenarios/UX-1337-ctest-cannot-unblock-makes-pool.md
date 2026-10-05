# UX-1337: ctest cannot unblock make's pool

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the owner's json-schema-validator 2.3.0 build under `--jobserver auto` (2026-10-05) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_ctest_cannot_unblock_makes_pool.py`

## Motivation

> read jobs pipe: resource temporarily unavailable. stop. waiting for unfinished jobs.

A `kind: cmake` element on make 4.2.1 runs `ctest --test-dir` after its
build; the install's make then aborted, intermittently, at a late target.
Under `auto` bga hands make 4.2.1 a raw fd pair (`UX-913`). ctest 3.29+ is
a jobserver client: `cmUVJobServerClient::OpenFD` `dup`s each fd and
`uv_pipe_open` sets `O_NONBLOCK` on the dup, which is the same open file
description make reads. make 4.2.1 `pselect`s then `read`s, and a token
taken in between returns EAGAIN, which it treats as fatal.

## Decomposition

Input classes: fd-pair auth; `fifo:` auth (opened per process, unaffected);
no auth. Journey: `bga_run_wrapped` -> `bga_run_isolated` -> exec. The
wrapper directory is mounted whenever an auth is injected (`UX-846`).

## Required Fix

**Decision:** a `ctest` wrapper with a new `isolate` flag style. On an fd
pair it reopens the read end via `/dev/fd` on fd 9 (a new description over
the same pipe), rewrites the auth to `9,9` and execs ctest; anything else
passes through. Restoring the flag after ctest was rejected: ctest runs
while make may still be reading. Scrubbing ctest's auth was rejected: it
loses the pool for a `ctest -j`.

## Out of Scope

Other libuv-based clients reached by absolute path, which bypass `PATH`.

## Acceptance Test

A fake ctest does what libuv does to a dup of the auth's read fd; the guard
asserts the caller's pipe stays blocking, the auth reads `9,9`, a token the
fake writes reaches the caller's pipe, and `fifo:`/no auth pass through.

## Outcome

### The gap, measured

Vanilla make 4.2.1 (Ubuntu orig tarball, built here), ctest 3.31.10 (pip),
six sub-makes of 200 `sleep 0.005` targets on one fd-pair pool, 2 tokens,
3 rounds:

```text
no ctest:           fd blocking True,  0/18 makes died
ctest 3.31 bare:    fd blocking False, 15/18 died: read jobs pipe: Resource temporarily unavailable.  Stop.
ctest 3.28.3 bare:  fd blocking True (3.28 is not a client)
```

### The close, measured

```text
ctest via wrapper:  fd blocking True,  0/18 makes died
$ python3 -m pytest -q -p no:xdist tests/unit/test_ctest_cannot_unblock_makes_pool.py
3 passed
```

The nix gnumake-4.2.1 pin did not reproduce it: it sets `O_NONBLOCK`
itself and handles EAGAIN (a distro patch); the owner's make is vanilla.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | the `isolate` branch never taken | 1 of 3 (fd pair) |
| M2 | fd 9 never opened | 1 of 3 (fd pair) |
| M3 | the auth not rewritten | 1 of 3 (fd pair) |
| M4 | the wrapper calls `threads` | 1 of 3 (fd pair) |
