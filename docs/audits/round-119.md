# Round 119 — the jobserver's value: the server's shape, the snapshot switch, and the gaps round 118's verifiers named

Run on 2026-09-14, after round 118 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

BuildStream caps an element's `max-jobs` at 8 by default. On a 40-core
server an llvm-sized element alone on the critical path builds at
`-j8` with 32 cores idle; under the mode it takes every token the pool
has. Round 118's evaluation could not show it - four elements at `-j4`
on four cores are saturated at `off` - so this round models the server
on this box: one long element under a `max-jobs` below the core count.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-853` `UX-854` `UX-855` `UX-856` | disjoint: the broker's memory sum, the proxies' leak audit, the ninja probe's guard, the snapshot switch |
| 2 | `UX-857` | after the switch: `examples/11-serial-giant`, captured both ways in CI |

## What closed

(in progress)

## Agents

no agents launched at this commit: the tracks start after the pull
request opens, and their rows land in the ledger as they finish.
