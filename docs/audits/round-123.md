# Round 123 — the auth style autodetect finally picks the safe one

Run on 2026-09-16, after round 122 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user ran `--jobserver auto` on the latest bga and hit the fifo
rejection again, now on a `kind: cmake` element whose sandbox-built
cmake runs `/usr/sysroot/bin/make` (below 4.4) by absolute path:
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2. Round 122's
`UX-874` probe covers only `make`/`autotools` and reads bare `make` on
`PATH`, so it never saw cmake's own make. `auto` cannot know, ahead of
the build, every make a recipe will invoke, and `fd`-style auth every
make from 4.2 up accepts. Two fixes: `auto` picks `fd` (`UX-876`), and
the sandbox-make downgrade covers every kind that injects `MAKEFLAGS`
for anyone who still forces `fifo` (`UX-877`).

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-876` `UX-877` | disjoint files: the host-side auto default in the tracer, the sandbox-side downgrade scope in the shim |

## What closed

(in progress)

## Agents

(in progress)

## The gate

(in progress)
