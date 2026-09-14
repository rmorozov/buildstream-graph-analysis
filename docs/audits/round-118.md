# Round 118 — the fifteen open rows: review 23's three and the jobserver's stage 1

Run on 2026-09-14, after round 117 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit (the user's proposal),
and closed with the round.

## Plan

Fifteen rows open: `UX-838` to `UX-840` from review 23 and `UX-841` to
`UX-852` from Direction 20. The dependency order the filings declare:

| wave | rows | why together |
|---|---|---|
| 1 | `UX-838` `UX-839` `UX-840` `UX-841` | disjoint surfaces: the contracts guard, the README, the styleguide guard, the tracer's FIFO |
| 2 | `UX-842` `UX-845` `UX-851` | after `UX-841`: the shim's pin rule, the tracer's pool, the capture option |
| 3 | `UX-843` `UX-846` `UX-852` `UX-844` | after the pin rule: the environment table, the wrappers, the leak audit, the key guard |
| 4 | `UX-847` `UX-848` `UX-849` `UX-850` | after the pool and the wrappers: the ledger, the example, priority, memory |

## What closed

(in progress)

## Agents

no agents launched at this commit: the tracks start after the pull
request opens, and their rows land in the ledger as they finish.
