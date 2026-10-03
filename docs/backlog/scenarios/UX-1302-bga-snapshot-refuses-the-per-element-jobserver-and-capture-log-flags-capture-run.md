# UX-1302: `bga snapshot` refuses the per-element jobserver and capture-log flags `capture run` takes, and no doc says so

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** docs gap audit on `c27ebd68`, UX-1300's thread (2026-10-03) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_snapshot_forwards_the_translated_flags.py`

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

**Decision:** forward the four translated flags. `bga snapshot` takes
`--jobserver-auth-override` (repeatable), `--lto-cap`, `--wrapper-dir`
and `--wrapper-dir-mode`; `take_snapshot` hands them to
`bga.cli.apply_capture_env_flags`, which runs the same three
`_translate_capture_*` functions `capture run` does, so a stale value
clears too. The other eleven `capture run` flags stay `capture run`
only, named in cli.md's `bga snapshot` section: `--wrapped-log`,
`--run-dir`, `--raw-log`, `--host-samples` (snapshot writes them),
`--jobserver-seed` (resolved from `--jobserver`), `--jobserver-pool`,
`--jobserver-capacity`, `--argv-log`, `--invocation-log`,
`--no-invocation-log`, `--json`. pilot.md's sentence stays true.

## Out of Scope

The `--help` text (`UX-1301`).

## Acceptance Test

`bga snapshot --jobserver auto --jobserver-auth-override off:x.bst --
true` is accepted, or cli.md names the flag as `capture run` only; a
guard holds the chosen set. Reading taken in this container.

## Outcome

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — `bga snapshot` refused all four per-element flags.

### The gap, measured

```text
$ for f in "--jobserver-auth-override off:x.bst" "--lto-cap 4" "--wrapper-dir /tmp/w" "--wrapper-dir-mode replace"; do
    bga snapshot --jobserver auto $f -- true 2>&1 | tail -1; done      # HEAD d54fa8e1
bga snapshot: error: unrecognized arguments: --jobserver-auth-override
bga snapshot: error: unrecognized arguments: --lto-cap
bga snapshot: error: unrecognized arguments: --wrapper-dir
bga snapshot: error: unrecognized arguments: --wrapper-dir-mode
```

### After

```text
$ (same loop, in a scratch project) | grep -c "unrecognized arguments"
0
0
0
0
$ comm -23 <(bga capture run --help | grep -oE '^  --[a-z-]+' | sort -u) <(bga snapshot --help | grep -oE '^  --[a-z-]+' | sort -u)
--argv-log --host-samples --invocation-log --jobserver-capacity --jobserver-pool --jobserver-seed --json --no-invocation-log --raw-log --run-dir --wrapped-log
$ bga snapshot --help | wc -l
63
```

The capture in this container then stops at `no real bwrap found on
PATH`; the guard pins the environment the capture reads with the tracer
faked, comparing it with what `capture run`'s own translators set for
the same flag. The eleven left are cli.md's `capture run`-only list.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| B1 | `take_snapshot` never applies the flags | 4 parametrized + repeatable + stale, 6 failed 1 passed |
| B2 | applied only when a flag was given | `test_a_stale_value_is_cleared_when_the_flag_is_absent`, 1 failed 6 passed |
| B3 | `capture_env_tokens` drops `--lto-cap` | `[--lto-cap]`, 1 failed 6 passed |
| B4 | only the last override kept | `test_the_override_is_repeatable`, 1 failed 6 passed |
| B5 | `apply_capture_env_flags` skips the wrapper translator | `[--wrapper-dir]`, `[--wrapper-dir-mode]`, stale, 3 failed 4 passed |
| B6 | a fifth translated flag `--new-flag` | `test_the_flag_set_is_the_translators`, 1 failed 6 passed |

Reverted from a copy: 7 passed.

### Deviation from the Required Fix

None. The guard runs `bga.cli.main`: `test_the_loop_stays_fast.py`'s
selector `max` ceiling 200 -> 201 (measured 201 over 820 files).

```text
$ PYTEST_XDIST= python3 -m pytest -q -p no:randomly <the guard, the docs, help, snapshot and jobserver-guide files>
307 passed, 3 skipped in 40.83s
$ make lint   # clean
```
