# UX-1336: a patched ninja joins the jobserver

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-1315 | **Found by:** the owner's LLVM 22.1 build under `--jobserver auto` (2026-10-04) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_patched_ninja_joins_the_jobserver.py`

## Motivation

> ninja warning -jN forced on command line ignoring gnu make jobserver

The owner's sandbox ninja is 1.10.2 with the community jobserver patch
(ninja PR #1140). `--version` and `--help` never name it, so the wrapper
held tokens for it and passed `-j <width>`, which turns the patch's client
off: the element got a width fixed at start instead of per-edge tokens.

## Decomposition

Input classes: patched ninja on a `fifo:` auth; patched ninja on an fd pair;
unpatched pre-1.13 ninja (must still hold). Journey: `bga_run_wrapped`
client detection -> `-j` strip -> exec. The shim's probe (`probe_ninja`)
keeps classing it `ninja_wrapper`, which is what puts the wrapper there.

## Required Fix

**Decision:** the wrapper greps the real binary for the patch's own warning
`ignoring GNU make jobserver`. A match is a client: no tokens held, the
recipe's `-j` stripped, exec. The patch parses `%d,%d` only and looks for
`--jobserver-fds=` before `--jobserver-auth=` (`src/tokenpool-gnu-make.cc`),
so on a `fifo:` auth the wrapper opens the fifo on fd 9 and prepends
`--jobserver-fds=9,9`; the `fifo:` auth stays last for gcc's `lto1`, which
deadlocks on a blocking fd pair (`UX-1006`). The patch reads a blocking fd
safely (poll, then a 100 ms alarm). Classing it in `probe_ninja` instead
was rejected: `ninja_client` gives no wrapper, and the patch cannot read
a `fifo:` auth, so it would fall back to its default width.

## Out of Scope

A make 4.2 child of the patched ninja sees two auths; make 4.2 rejects
that and also rejects `fifo:`, so it was already broken under this auth.

## Acceptance Test

The guard stages a fake real ninja carrying the warning string and one
without it, and asserts argv, `MAKEFLAGS`, the token on fd 9 and the pool
left untouched by the wrapper. It reddens under each mutation below.

## Outcome

### The gap, measured

PR #1140's head (`05d39cb`) built here with `configure.py --bootstrap`,
version string set to 1.10.2; six `sleep 0.3` edges, `fifo:` pool.

```text
$ MAKEFLAGS=--jobserver-auth=fifo:$PWD/js ninja -j8      # through the wrapper
ninja: warning: -jN forced on command line; ignoring GNU make jobserver.
$ ninja --help 2>&1 | grep -ci jobserver
0
```

### The close, measured

```text
3 tokens:  ninja: using GNU make jobserver.   0.64 s (4 at once), 3 tokens back in the pool
0 tokens:                                      1.86 s (serial)
$ python3 -m pytest -q -p no:xdist tests/unit/test_a_patched_ninja_joins_the_jobserver.py tests/unit/test_a_nested_build_can_run_the_ninja_wrapper.py
9 passed
```

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | the binary grep never matches | 2 of 3 (fifo, fd pair) |
| M2 | no `--jobserver-fds=9,9` prefix | 1 of 3 (fifo) |
| M3 | fd 9 never opened | 1 of 3 (fifo) |
| M4 | the fds flag appended after the auth | 1 of 3 (fifo) |
