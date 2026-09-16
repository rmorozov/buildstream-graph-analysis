# Round 122 — the auth style the sandbox make refused

Run on 2026-09-16, after round 121 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user built a `kind: make` element from a `tar` source on a host
with GNU Make 4.4 and hit
`make: *** internal error: invalid --jobserver-auth string
'fifo:/tmp/.bst-native-trace/jobserver'. Stop`, exit 2. `UX-869` had
already put the FIFO where the sandbox reaches it (the path is right,
no `mkdir parents` error); the *style* was wrong. `jobserver_auth_style`
picks `fifo` from the **host** make, but the element's own `tar` stages
an older make, and that make - the one that actually consumes the
string - rejects `fifo:`. `fd` style every make from 4.0 up accepts, so
the fix is a sandbox-make check that narrows fifo to fd. Two filings.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-874` `UX-875` | disjoint surfaces: the shim's per-element auth downgrade, the snapshot entry point's passthrough |

## What closed

(in progress)

## Agents

(in progress)

## The gate

(in progress)
