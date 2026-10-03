# UX-1302: `bga snapshot` refuses the per-element jobserver and capture-log flags `capture run` takes, and no doc says so

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`bga snapshot` forwards only `--jobserver`, `--jobserver-auth` and
`--plan` (`tools/bga_snapshot.py:326-399`); the translators fire only on
`capture run` (`bga/cli.py:3302-3306`). A snapshot user cannot pass a
per-element override, an LTO cap, a wrapper directory or the pool's
tuning, and the docs never say which command takes which.

```text
$ bga snapshot --jobserver auto --jobserver-auth-override off:x.bst -- true
bga snapshot: error: unrecognized arguments: --jobserver-auth-override
```

`comm -23` of the two `--help` outputs: `--argv-log --host-samples
--invocation-log --jobserver-capacity --jobserver-pool --jobserver-seed
--raw-log --run-dir --wrapped-log`, plus the four translated flags.

## Decomposition

Input classes: a translated flag on `snapshot`; a tracer-only flag (`--jobserver-pool`, `--jobserver-seed`, `--jobserver-capacity`); a capture-log flag (`--argv-log`, `--raw-log`, `--invocation-log`); a flag both commands share. Journey: `bga snapshot --jobserver auto <flag> -- bst build all.bst`.

## Required Fix

Decide per flag: forward it from `snapshot`, or say in cli.md that it
is `capture run` only. The four per-element jobserver flags are the
first candidates to forward, since `jobserver.md` now sends a user to
them.

## Out of Scope

The `--help` text (`UX-1301`).

## Acceptance Test

`bga snapshot --jobserver auto --jobserver-auth-override off:x.bst --
true` is accepted, or cli.md names the flag as `capture run` only; a
guard holds the chosen set. Reading taken in this container.

## Outcome
