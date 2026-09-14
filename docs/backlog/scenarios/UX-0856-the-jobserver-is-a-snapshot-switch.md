# UX-856: the jobserver is a snapshot switch

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-851, UX-849 | **Found by:** round 119, the user | **Serves:** R4 (the local loop captures under the mode with one flag) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`bga capture run --jobserver auto` (`UX-851`) and `--plan` (`UX-849`)
exist, but the local loop is `bga snapshot -- bst build target.bst`,
which composes the capture itself and offers neither. A user of the loop
cannot capture under the mode without typing the three commands
`snapshot` exists to replace, and a snapshot pair (off, then auto) is
the comparison the mode's value is read from.

## Required Fix

`tools/bga_snapshot.py`: `--jobserver auto|N|off` (default `off`) and
`--plan @prev|@last|<analyze.json>` pass through to the capture argv
exactly as `bga capture run` resolves them (`bga/cli.py`'s
`resolve_jobserver_ceiling`, reused, not copied); `@prev` and `@last`
resolve to that snapshot's `analyze.json`. The capture context file
records both, and the compare header names each side's mode (the
`run_instance.jobserver` fact `UX-851` writes). `docs/guides/cli.md`'s
snapshot section shows the pair.

## Decomposition

Input classes: `off`, an int, `auto` with and without `--builders`,
`--plan` as a path and as `@prev`, `--plan` without the mode; the
journey it extends is R4's local loop - a snapshot pair off then auto.

## Out of Scope

A sticky setting in `.bga/config` - the flag is per capture, like
`--diagnose` (`UX-146`).

## Acceptance Test

`tests/unit/test_the_snapshot_takes_the_jobserver_switch.py`: the
composed capture argv carries `--jobserver N` and `--plan <path>` for
`auto`, an int, `off` and `@prev`, and the context file names them;
mutation: drop the pass-through - red. A live pair on examples/11
(`UX-857`) pasted from this box.
