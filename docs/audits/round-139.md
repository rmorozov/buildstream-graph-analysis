# Round 139 — the workflow review, and its first four rows

Run on 2026-09-23 from `49a29a29`, off main at `65a0a3fc` (`#284`,
which closed `UX-991` and filed `UX-992` in a parallel thread). The
review measured the process and Ruslan took all four of its calls at
14:44; this round lands them.

```text
closed   UX-993 UX-994 UX-996            (UX-991 closed by #284)
open     UX-995 (the PR's own 3.12 reference is owed), UX-997 (T2 owed)
filed    UX-998 UX-999 (Ruslan's 15:03 and 15:11 ideas)
index    dev_close_task.py --counts: 960 scenarios, 24 open, 936 closed
```

## What the review measured

```text
process share of filings    6% (UX-1..100)  85% (701..800)  87% (901..951)
adopt commits on main       89 of the last 300 first-parent commits
catch-ups                   35 of 60 merged PRs; 40 of 47 conflict paths registers
4-Python matrix             68.5% of a run's job-seconds
```

Hence the order: the derived registers (`UX-996`) and the CI records
(`UX-997`) are what the catch-ups collide on, and the matrix
(`UX-995`) is what a queued PR waits behind.

## Every track was held once

All three verifiers returned HOLD, and each hold was a real defect:

```text
UX-996  MD032 in the task file; the new guard undeclared in the census
UX-995  a substring exemption let a timing step drop off pull requests
UX-997  a swallowed fetch then a live publish dropped rows from the tip
```

`UX-997`'s was reproduced against local bare remotes and is now a test
that reddens with the base comparison removed. The architect's
decisions held on route; each track still found a file the Decision
did not name (`dev_tier_drift.py`'s use of `_backlog_counts()`,
fixture ids at `UX-999`, a hook's `holds:` slug).

## The push gate caught an id collision

Filing `UX-999` reddened `test_one_id_names_one_task_file.py`: two
guards wrote their fixture row at `UX-0999` as a free id. Both now
write `UX-9999` (`4de7764a`).

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | agent-runs ledger statistics | 66k | 23 | 3.5 m | none reported |
| researcher | sonnet | CI and merge-cycle timing | 44k | 25 | 3.9 m | run-log archive 403; job tails only |
| researcher | sonnet | backlog process vs product share | 52k | 37 | 3.9 m | none reported |
| general-purpose | opus | architect: `UX-996` | 88k | 35 | 5.5 m | missed `dev_tier_drift.py` reading `_backlog_counts()` |
| general-purpose | opus | architect: `UX-995` | 95k | 16 | 2.8 m | none reported |
| general-purpose | opus | architect: `UX-997` | 64k | 26 | 3.7 m | artifacts and caches 403 through the proxy, so a branch |
| implementer | sonnet | `UX-996` | 340k | 283 | 44 m | MD032 and three census bounds a new guard moves together |
| verifier | sonnet | `UX-996` verifier | 104k | 50 | 11.7 m | none reported |
| implementer | sonnet | `UX-995` | 505k | 243 | 72.4 m | a substring exemption; `fromJSON` broke two guards' cell loops |
| verifier | sonnet | `UX-995` verifier | 108k | 47 | 13.9 m | none reported |
| implementer | sonnet | `UX-997` T1 | 601k | 231 | 103.8 m | fetch-then-stage for publish; git's stderr tells absent from unreachable |
| verifier | sonnet | `UX-997` verifier | 86k | 52 | 12.8 m | the dropped-row case needed a hand-built bare-remote repro |

Twelve rows, 2,153k fresh tokens, each derived by
`dev_track_cost.py --ledger`. The architect ran as `general-purpose`
on `opus` because `.claude/agents/architect.md` landed in this round.
The closing session's own row is not here.
